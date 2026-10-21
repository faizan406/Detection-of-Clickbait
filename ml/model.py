import os
import pickle
import pandas as pd
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

from ml.preprocessor import preprocess_text
from ml.xai_engine import explain_prediction
from database.db import save_model_metrics, get_latest_metrics

MODEL_FILE = os.path.join(os.path.dirname(__file__), "trained_model.pkl")

class ClickbaitModelPipeline:
    def __init__(self):
        self.vectorizer = None
        self.model = None
        self.metrics = {}
        self.load_model()

    def train(self, csv_filepath):
        """
        Trains the TF-IDF Vectorizer and Logistic Regression classifier
        on the dataset specified by csv_filepath.
        """
        if not os.path.exists(csv_filepath):
            raise FileNotFoundError(f"Dataset file not found: {csv_filepath}")

        df = pd.read_csv(csv_filepath)
        
        # Check required columns
        req_cols = [col for col in df.columns if col.lower() in ['headline', 'text', 'title', 'label', 'target', 'class']]
        
        # Prioritize headline / title over full text
        headline_col = None
        label_col = None
        for target in ['headline', 'title', 'news', 'text']:
            for col in df.columns:
                if col.lower() == target:
                    headline_col = col
                    break
            if headline_col:
                break

        for target in ['label', 'clickbait', 'target', 'class']:
            for col in df.columns:
                if col.lower() == target:
                    label_col = col
                    break
            if label_col:
                break

        if not headline_col or not label_col:
            # Fallback to column index 0 and 1
            headline_col = df.columns[0]
            label_col = df.columns[1]

        # Drop any null headlines or labels
        df = df.dropna(subset=[headline_col, label_col])

        # Clean text
        df['clean_headline'] = df[headline_col].astype(str).apply(lambda x: preprocess_text(x, keep_stop_words=True))
        X = df['clean_headline']
        y = df[label_col].astype(int)

        # Train/Test split (or full dataset if small)
        if len(df) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        else:
            X_train, X_test, y_train, y_test = X, X, y, y

        # Vectorization (Scaled dynamically based on corpus size)
        max_feat = 15000 if len(df) > 30000 else 5000
        reg_c = 2.0 if len(df) > 30000 else 1.0

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=max_feat)
        X_train_tfidf = vectorizer.fit_transform(X_train)
        X_test_tfidf = vectorizer.transform(X_test)

        # Model Training (Logistic Regression)
        clf = LogisticRegression(C=reg_c, max_iter=1000, random_state=42)
        clf.fit(X_train_tfidf, y_train)

        # Predictions & Metrics
        y_pred = clf.predict(X_test_tfidf)
        
        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))

        self.vectorizer = vectorizer
        self.model = clf
        self.metrics = {
            "model_name": "Logistic Regression + TF-IDF",
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "sample_count": len(df)
        }

        # Save model
        with open(MODEL_FILE, 'wb') as f:
            pickle.dump({'vectorizer': self.vectorizer, 'model': self.model, 'metrics': self.metrics}, f)

        # Save to database
        try:
            save_model_metrics("Logistic Regression", acc, prec, rec, f1, len(df))
        except Exception as e:
            print("Database metric log note:", e)

        return self.metrics

    def load_model(self):
        """Loads model from disk if available."""
        if os.path.exists(MODEL_FILE):
            try:
                with open(MODEL_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.vectorizer = data.get('vectorizer')
                    self.model = data.get('model')
                    self.metrics = data.get('metrics', {})
                return True
            except Exception as e:
                print("Error loading model:", e)
        return False

    def predict(self, raw_headline, top_n=50):
        """
        Classifies input headline and provides prediction, confidence score, and XAI feature explanation.
        """
        if not self.model or not self.vectorizer:
            # Auto train on baseline dataset if model file doesn't exist
            base_csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dataset.csv")
            if os.path.exists(base_csv):
                self.train(base_csv)
            else:
                raise RuntimeError("Model is not trained and baseline dataset is missing.")

        clean_text = preprocess_text(raw_headline, keep_stop_words=True)
        X_vec = self.vectorizer.transform([clean_text])
        
        # Predict probability
        probs = self.model.predict_proba(X_vec)[0]
        prob_clickbait = float(probs[1])
        prob_non_clickbait = float(probs[0])
        
        is_clickbait = prob_clickbait >= 0.5
        prediction = "Clickbait" if is_clickbait else "Non-Clickbait"
        confidence = round(prob_clickbait * 100 if is_clickbait else prob_non_clickbait * 100, 2)

        # Explain prediction via XAI engine
        xai_words = explain_prediction(clean_text, self.vectorizer, self.model, top_n=top_n)

        return {
            "headline": raw_headline,
            "prediction": prediction,
            "confidence": confidence,
            "prob_clickbait": round(prob_clickbait, 4),
            "prob_non_clickbait": round(prob_non_clickbait, 4),
            "top_words": xai_words
        }

# Global singleton instance
clickbait_model_pipeline = ClickbaitModelPipeline()
