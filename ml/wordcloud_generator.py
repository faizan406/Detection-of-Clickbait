import os
import pandas as pd
from collections import Counter
from ml.preprocessor import preprocess_text, STOP_WORDS

def generate_wordcloud_data(csv_filepath, top_n=40):
    """
    Analyzes the dataset at csv_filepath and extracts the most frequent,
    distinguishing words for both Clickbait and Non-Clickbait headlines.
    """
    if not os.path.exists(csv_filepath):
        # Fallback to default benchmark dataset
        csv_filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dataset.csv")

    df = pd.read_csv(csv_filepath)

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
        headline_col = df.columns[0]
        label_col = df.columns[1]

    labels = df[label_col].astype(str).str.lower().str.strip()
    clickbait_df = df[labels.isin(['1', '1.0', 'clickbait', 'true'])]
    non_clickbait_df = df[labels.isin(['0', '0.0', 'non-clickbait', 'false'])]

    def get_word_counts(series):
        counter = Counter()
        for text in series.dropna():
            cleaned = preprocess_text(str(text), keep_stop_words=False)
            words = [w for w in cleaned.split() if len(w) > 2 and w not in STOP_WORDS]
            counter.update(words)
        return counter

    cb_counts = get_word_counts(clickbait_df[headline_col])
    non_cb_counts = get_word_counts(non_clickbait_df[headline_col])

    # Top words
    cb_top = cb_counts.most_common(top_n)
    non_cb_top = non_cb_counts.most_common(top_n)

    # Normalize weights (0.2 to 1.0 scale for CSS font sizing)
    def normalize_list(items):
        if not items:
            return []
        max_count = max([c for _, c in items]) or 1
        min_count = min([c for _, c in items]) or 0
        denom = (max_count - min_count) or 1
        
        results = []
        for word, count in items:
            norm_weight = round(0.3 + 0.7 * ((count - min_count) / denom), 3)
            results.append({
                "word": word,
                "count": count,
                "weight": norm_weight
            })
        return results

    return {
        "clickbait_words": normalize_list(cb_top),
        "non_clickbait_words": normalize_list(non_cb_top),
        "total_clickbait_samples": len(clickbait_df),
        "total_non_clickbait_samples": len(non_clickbait_df)
    }
