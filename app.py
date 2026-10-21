import os
import json
import re
import time
import werkzeug.security as security
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, session

from config import Config
from database.db import (
    init_db, create_user, get_user_by_email, get_user_by_id, update_user_password, update_user_avatar,
    save_prediction, get_history, delete_history_record, clear_all_history, save_dataset_record, get_latest_metrics
)
from ml.model import clickbait_model_pipeline
from ml.preprocessor import extract_linguistic_features

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Database on app startup
with app.app_context():
    init_db()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    is_authenticated = 'user_id' in session
    return render_template('index.html', is_authenticated=is_authenticated)

# ---------------------------------------------------------
# AUTHENTICATION ENDPOINTS (UC-1, UC-2, UC-3, UC-4)
# ---------------------------------------------------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not name or not email or not password:
        return jsonify({"success": False, "message": "Please fill in all required fields."}), 400

    # Requirement 3: Name must contain letters & spaces ONLY (no numbers or symbols)
    if not re.match(r'^[A-Za-z\s]+$', name):
        return jsonify({"success": False, "message": "Name can only contain alphabetic letters and spaces (no numbers or special characters)."}), 400

    # Requirement 4: Email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({"success": False, "message": "Please enter a valid email address (e.g. user@example.com)."}), 400

    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    # Requirement 4: Password complexity validation
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long."}), 400

    if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9!@#$%^&*]', password):
        return jsonify({"success": False, "message": "Password must contain both letters and numbers/symbols."}), 400

    password_hash = security.generate_password_hash(password)
    user_id = create_user(name, email, password_hash)

    if not user_id:
        return jsonify({"success": False, "message": "Email already registered."}), 400

    session['user_id'] = user_id
    session['user_name'] = name
    session['user_email'] = email
    session['user_avatar'] = None

    return jsonify({
        "success": True,
        "message": "Registration successful!",
        "user": {"id": user_id, "name": name, "email": email, "avatar_url": None}
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"success": False, "message": "Please fill all fields."}), 400

    user = get_user_by_email(email)
    if not user or not security.check_password_hash(user['password_hash'], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_avatar'] = user['avatar_url'] if 'avatar_url' in user.keys() else None

    return jsonify({
        "success": True,
        "message": "Login successful!",
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "avatar_url": user['avatar_url'] if 'avatar_url' in user.keys() else None
        }
    })

@app.route('/api/auth/avatar', methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    if 'avatar' not in request.files:
        return jsonify({"success": False, "message": "No avatar file provided."}), 400

    file = request.files['avatar']
    if not file or not file.filename:
        return jsonify({"success": False, "message": "No selected file."}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('png', 'jpg', 'jpeg', 'webp', 'gif'):
        return jsonify({"success": False, "message": "Invalid image format. Supported: PNG, JPG, WEBP"}), 400

    upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'avatars')
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"user_{session['user_id']}_{int(time.time())}.{ext}"
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    avatar_url = f"/static/uploads/avatars/{filename}"
    update_user_avatar(session['user_id'], avatar_url)
    session['user_avatar'] = avatar_url

    return jsonify({"success": True, "avatar_url": avatar_url, "message": "Profile picture updated successfully!"})

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not email or not new_password:
        return jsonify({"success": False, "message": "Please fill in all required fields."}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"success": False, "message": "Email not found."}), 404

    new_hash = security.generate_password_hash(new_password)
    updated = update_user_password(email, new_hash)

    if updated:
        return jsonify({"success": True, "message": "Password reset successful!"})
    return jsonify({"success": False, "message": "Failed to update password."}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            return jsonify({
                "authenticated": True,
                "user": {
                    "id": user['id'],
                    "name": user['name'],
                    "email": user['email'],
                    "avatar_url": user['avatar_url'] if 'avatar_url' in user.keys() else None
                }
            })
    return jsonify({"authenticated": False})

# ---------------------------------------------------------
# CLICKBAIT DETECTION & EXPLAINABLE AI (UC-5, UC-8, UC-9, UC-10, UC-12)
# ---------------------------------------------------------
@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_json() or {}
    headline = data.get('headline', '').strip()

    if not headline:
        return jsonify({"success": False, "message": "Text field cannot be empty. Please enter headline text."}), 400

    if len(headline) < 3 or headline.replace('@', '').replace('#', '').strip() == '':
        return jsonify({"success": False, "message": "Please enter valid headline or news text."}), 400

    try:
        from ml.preprocessor import clean_webpage_text_artifacts
        cleaned_input = clean_webpage_text_artifacts(headline)

        # Check if user pasted a long article / webpage text rather than a single headline
        if len(cleaned_input) > 180 or '\n' in headline:
            lines = [l.strip() for l in cleaned_input.split('\n') if len(l.strip()) > 10]
            if not lines:
                lines = [cleaned_input]
            
            headline_title = lines[0]
            if len(headline_title) > 150:
                sentences = re.split(r'(?<=[.!?])\s+', headline_title)
                headline_title = sentences[0] if sentences else headline_title[:120]
            
            headline_res = clickbait_model_pipeline.predict(headline_title)
            headline_ling = extract_linguistic_features(headline_title)

            body_sample = cleaned_input[:2000]
            body_res = clickbait_model_pipeline.predict(body_sample)
            body_ling = extract_linguistic_features(body_sample)

            h_prob_cb = headline_res['prob_clickbait']
            b_prob_cb = body_res['prob_clickbait']
            overall_prob_cb = round(float(0.85 * h_prob_cb + 0.15 * b_prob_cb), 4)
            overall_prob_non_cb = round(float(1.0 - overall_prob_cb), 4)

            if headline_res['confidence'] >= 70.0:
                is_cb = headline_res['prediction'] == 'Clickbait'
            else:
                is_cb = overall_prob_cb >= 0.5

            prediction = "Clickbait" if is_cb else "Non-Clickbait"
            confidence = round((overall_prob_cb if is_cb else overall_prob_non_cb) * 100, 2)

            sensational = list(set(headline_ling['sensational_words'] + body_ling['sensational_words']))
            hyperbolic = list(set(headline_ling['hyperbolic_expressions'] + body_ling['hyperbolic_expressions']))
            ai_markers = list(set(headline_ling.get('ai_markers_found', []) + body_ling.get('ai_markers_found', [])))

            reasons = []
            if is_cb:
                if headline_res['prediction'] == 'Clickbait':
                    reasons.append(f"Headline contains strong sensational phrasing ({round(headline_res['confidence'], 1)}% clickbait likelihood).")
                if sensational:
                    reasons.append(f"Sensational trigger terms detected: {', '.join(sensational[:4])}.")
                if hyperbolic:
                    reasons.append(f"Hyperbolic curiosity gaps identified: {', '.join(hyperbolic[:3])}.")
            else:
                if headline_res['prediction'] == 'Non-Clickbait':
                    reasons.append(f"Headline uses informative, objective news syntax ({round(headline_res['confidence'], 1)}% factual rating).")
                if not sensational and not hyperbolic:
                    reasons.append("Zero hyperbolic triggers or sensational curiosity traps found in content.")

            res = {
                "headline": headline_title,
                "prediction": prediction,
                "confidence": confidence,
                "prob_clickbait": round(overall_prob_cb * 100, 2),
                "prob_non_clickbait": round(overall_prob_non_cb * 100, 2),
                "top_words": headline_res['top_words'],
                "linguistic_features": {
                    "sensational_words": sensational,
                    "hyperbolic_expressions": hyperbolic,
                    "ai_markers_found": ai_markers,
                    "has_ai_signal": len(ai_markers) > 0,
                    "has_exclamation": headline_ling['has_exclamation'],
                    "has_question": headline_ling['has_question']
                },
                "reasons": reasons
            }
        else:
            res = clickbait_model_pipeline.predict(headline)
            res['prob_clickbait'] = round(res['prob_clickbait'] * 100, 2)
            res['prob_non_clickbait'] = round(res['prob_non_clickbait'] * 100, 2)
            
            linguistic_info = extract_linguistic_features(headline)
            res['linguistic_features'] = linguistic_info

            reasons = []
            is_cb = res['prediction'] == 'Clickbait'
            sensational = linguistic_info.get('sensational_words', [])
            hyperbolic = linguistic_info.get('hyperbolic_expressions', [])
            has_excl = linguistic_info.get('has_exclamation', False)
            has_q = linguistic_info.get('has_question', False)

            if is_cb:
                if res['confidence'] > 75.0:
                    reasons.append(f"Headline contains strong sensational phrasing ({round(res['confidence'], 1)}% clickbait confidence).")
                if sensational:
                    reasons.append(f"Sensational trigger terms detected: {', '.join(sensational[:4])}.")
                if hyperbolic:
                    reasons.append(f"Hyperbolic curiosity gaps identified: {', '.join(hyperbolic[:3])}.")
                if has_excl:
                    reasons.append("Exclamatory punctuation used to provoke emotional curiosity.")
            else:
                if res['confidence'] > 75.0:
                    reasons.append(f"Headline uses objective, factual news syntax ({round(res['confidence'], 1)}% factual rating).")
                if not sensational and not hyperbolic:
                    reasons.append("Zero sensational trigger words or hyperbolic curiosity traps found.")
                if has_q:
                    reasons.append("Interrogative structure formatted as standard informational inquiry.")

            res['reasons'] = reasons

        # Real-time Authenticity & Fake News Verification
        try:
            from ml.authenticity_verifier import authenticity_verifier
            target_headline = headline_title if (len(cleaned_input) > 180 or '\n' in headline) else headline
            auth_res = authenticity_verifier.verify_headline(target_headline)
        except Exception:
            auth_res = {
                "status": "UNVERIFIED",
                "score": 50.0,
                "badge_type": "unverified",
                "consensus_label": "Engine Offline",
                "tier1_count": 0,
                "fact_check_flag": False,
                "explanation": "Authenticity verification temporarily unavailable.",
                "evidence_sources": [],
                "claim_type": "General"
            }
        res['authenticity'] = auth_res

        # Auto-save detection history
        user_id = session.get('user_id')
        rec_id = save_prediction(
            user_id=user_id,
            headline=res['headline'],
            prediction=res['prediction'],
            confidence=res['confidence'],
            top_words=res['top_words'],
            source_type='text',
            source_url=None,
            authenticity_status=auth_res.get('status', 'Unverified'),
            authenticity_score=auth_res.get('score', 50.0),
            authenticity_details=auth_res
        )
        res['record_id'] = rec_id

        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "message": f"Prediction model error: {str(e)}"}), 500

# ---------------------------------------------------------
# URL FULL WEBPAGE ARTICLE ANALYSIS API
# ---------------------------------------------------------
@app.route('/api/analyze-url', methods=['POST'])
def analyze_url():
    data = request.get_json() or {}
    url_str = data.get('url', '').strip()

    if not url_str:
        return jsonify({"success": False, "message": "Please enter a valid URL."}), 400

    from ml.url_extractor import fetch_and_extract_webpage_content
    success, ext_result = fetch_and_extract_webpage_content(url_str)

    if not success:
        return jsonify({"success": False, "message": ext_result}), 400

    extracted_headline = ext_result['headline']
    body_text = ext_result['body_text']
    body_preview = ext_result['body_preview']
    word_count = ext_result['word_count']

    try:
        # 1. Headline Prediction
        headline_res = clickbait_model_pipeline.predict(extracted_headline)
        headline_ling = extract_linguistic_features(extracted_headline)

        # 2. Article Body Text Prediction (if available)
        if body_text and len(body_text) > 30:
            body_sample = body_text[:2000]
            body_res = clickbait_model_pipeline.predict(body_sample)
            body_ling = extract_linguistic_features(body_sample)
        else:
            body_res = headline_res
            body_ling = headline_ling

        # 3. Headline-Dominant Combination (85% Headline + 15% Sanitized Body for consistent predictions)
        h_prob_cb = headline_res['prob_clickbait']
        b_prob_cb = body_res['prob_clickbait']

        overall_prob_cb = round(float(0.85 * h_prob_cb + 0.15 * b_prob_cb), 4)
        overall_prob_non_cb = round(float(1.0 - overall_prob_cb), 4)

        # Align prediction with headline if headline confidence is strong
        if headline_res['confidence'] >= 70.0:
            is_cb = headline_res['prediction'] == 'Clickbait'
        else:
            is_cb = overall_prob_cb >= 0.5

        prediction = "Clickbait" if is_cb else "Non-Clickbait"
        confidence = round((overall_prob_cb if is_cb else overall_prob_non_cb) * 100, 2)

        # 4. Combine top influential XAI words from both headline & body
        combined_words = []
        seen_words = set()
        for w in headline_res['top_words'] + body_res['top_words']:
            w_str = w['word'].lower()
            if w_str not in seen_words:
                seen_words.add(w_str)
                combined_words.append(w)
        combined_words = combined_words[:50]

        # 5. Combine linguistic signals
        sensational = list(set(headline_ling['sensational_words'] + body_ling['sensational_words']))
        hyperbolic = list(set(headline_ling['hyperbolic_expressions'] + body_ling['hyperbolic_expressions']))
        ai_markers = list(set(headline_ling.get('ai_markers_found', []) + body_ling.get('ai_markers_found', [])))
        has_excl = headline_ling['has_exclamation'] or body_ling['has_exclamation']
        has_q = headline_ling['has_question'] or body_ling['has_question']

        # 6. Generate detailed specific Reasons Why (no generic fallbacks)
        reasons = []
        if is_cb:
            if headline_res['prediction'] == 'Clickbait':
                reasons.append(f"Headline contains strong sensational phrasing ({round(headline_res['confidence'], 1)}% clickbait likelihood).")
            if sensational:
                reasons.append(f"Sensational trigger terms detected: {', '.join(sensational[:4])}.")
            if hyperbolic:
                reasons.append(f"Hyperbolic curiosity gaps identified: {', '.join(hyperbolic[:3])}.")
            if ai_markers:
                reasons.append(f"AI-Generated news content signals detected (LLM markers: {', '.join(ai_markers[:3])}).")
            if has_excl:
                reasons.append("Exclamatory language used to provoke emotional response.")
            if body_res['prediction'] == 'Clickbait':
                reasons.append(f"Article body text displays exaggerated tone ({round(body_res['confidence'], 1)}% clickbait score).")
        else:
            if headline_res['prediction'] == 'Non-Clickbait':
                reasons.append(f"Headline uses informative, objective news syntax ({round(headline_res['confidence'], 1)}% factual rating).")
            if body_res['prediction'] == 'Non-Clickbait':
                reasons.append(f"Article body text contains descriptive, factual vocabulary ({round(body_res['confidence'], 1)}% non-clickbait score).")
            if ai_markers:
                reasons.append(f"AI-Generated news writing style detected (LLM markers: {', '.join(ai_markers[:3])}).")
            if not sensational and not hyperbolic:
                reasons.append("Zero hyperbolic triggers or sensational curiosity traps found in content.")

        final_result = {
            "headline": extracted_headline,
            "prediction": prediction,
            "confidence": confidence,
            "prob_clickbait": round(overall_prob_cb * 100, 2),
            "prob_non_clickbait": round(overall_prob_non_cb * 100, 2),
            "headline_score": {
                "prediction": headline_res['prediction'],
                "confidence": headline_res['confidence']
            },
            "body_score": {
                "prediction": body_res['prediction'],
                "confidence": body_res['confidence']
            },
            "top_words": combined_words,
            "linguistic_features": {
                "sensational_words": sensational,
                "hyperbolic_expressions": hyperbolic,
                "ai_markers_found": ai_markers,
                "has_ai_signal": len(ai_markers) > 0,
                "has_exclamation": has_excl,
                "has_question": has_q
            },
            "reasons": reasons
        }

        # Real-time Authenticity & Fake News Verification
        try:
            from ml.authenticity_verifier import authenticity_verifier
            auth_res = authenticity_verifier.verify_headline(extracted_headline, source_url=url_str)
        except Exception:
            auth_res = {
                "status": "UNVERIFIED",
                "score": 50.0,
                "badge_type": "unverified",
                "consensus_label": "Engine Offline",
                "tier1_count": 0,
                "fact_check_flag": False,
                "explanation": "Authenticity verification temporarily unavailable.",
                "evidence_sources": [],
                "claim_type": "General"
            }
        final_result['authenticity'] = auth_res

        # Auto-save detection history
        user_id = session.get('user_id')
        rec_id = save_prediction(
            user_id=user_id,
            headline=extracted_headline,
            prediction=prediction,
            confidence=confidence,
            top_words=combined_words,
            source_type='url',
            source_url=url_str,
            authenticity_status=auth_res.get('status', 'Unverified'),
            authenticity_score=auth_res.get('score', 50.0),
            authenticity_details=auth_res
        )
        final_result['record_id'] = rec_id

        return jsonify({
            "success": True,
            "source_type": "url",
            "source_url": url_str,
            "extracted_headline": extracted_headline,
            "body_preview": body_preview,
            "full_body_text": body_text,
            "word_count": word_count,
            "result": final_result
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Prediction error for webpage content: {str(e)}"}), 500

# ---------------------------------------------------------
# HISTORY API & DELETE ENDPOINTS (UC-13)
# ---------------------------------------------------------
@app.route('/api/history', methods=['GET'])
def fetch_history():
    user_id = session.get('user_id')
    search = request.args.get('search', '').strip()
    filter_type = request.args.get('filter', '').strip()
    source_type_filter = request.args.get('source_type', '').strip()
    auth_filter = request.args.get('auth_filter', '').strip()

    history = get_history(user_id=user_id, search=search, filter_type=filter_type, source_type_filter=source_type_filter, auth_filter=auth_filter)
    return jsonify({"success": True, "history": history})

@app.route('/api/history/delete/<int:record_id>', methods=['POST', 'DELETE'])
def delete_history_item(record_id):
    user_id = session.get('user_id')
    deleted = delete_history_record(record_id, user_id=user_id)
    if deleted:
        return jsonify({"success": True, "message": "History record deleted successfully."})
    return jsonify({"success": False, "message": "Record not found or already deleted."}), 404

@app.route('/api/history/clear', methods=['POST', 'DELETE'])
def clear_history():
    user_id = session.get('user_id')
    cleared = clear_all_history(user_id=user_id)
    return jsonify({"success": True, "message": "All history records cleared successfully."})

# ---------------------------------------------------------
# WORD CLOUD INSIGHTS API
# ---------------------------------------------------------
@app.route('/api/wordcloud', methods=['GET'])
def get_wordcloud():
    top_n = request.args.get('limit', default=40, type=int)
    from ml.wordcloud_generator import generate_wordcloud_data
    csv_path = os.path.join(os.path.dirname(__file__), "data", "dataset.csv")
    try:
        data = generate_wordcloud_data(csv_path, top_n=top_n)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Word cloud generation error: {str(e)}"}), 500

# ---------------------------------------------------------
# DATASET UPLOAD & MODEL TRAINING (UC-6, UC-7, UC-11)
# ---------------------------------------------------------
@app.route('/api/dataset/upload', methods=['POST'])
def upload_dataset():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file."}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"success": False, "message": "Invalid record format. Please upload a CSV file."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    # Validate CSV content
    try:
        import pandas as pd
        df = pd.read_csv(save_path)
        if df.empty:
            os.remove(save_path)
            return jsonify({"success": False, "message": "Uploaded file carries no information."}), 400

        user_id = session.get('user_id')
        save_dataset_record(filename, len(df), uploaded_by=user_id)

        return jsonify({
            "success": True,
            "message": "Dataset uploaded successfully!",
            "filename": filename,
            "filepath": save_path,
            "row_count": len(df),
            "columns": list(df.columns)
        })
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        return jsonify({"success": False, "message": f"Dataset layout is invalid: {str(e)}"}), 400

@app.route('/api/model/train', methods=['POST'])
def train_model():
    data = request.get_json() or {}
    filename = data.get('filename')

    if filename:
        dataset_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    else:
        dataset_path = os.path.join(os.path.dirname(__file__), "data", "dataset.csv")

    if not os.path.exists(dataset_path):
        return jsonify({"success": False, "message": "No dataset available for training."}), 400

    try:
        metrics = clickbait_model_pipeline.train(dataset_path)
        return jsonify({
            "success": True,
            "message": "Model training finished successfully!",
            "metrics": metrics
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Model training failure: {str(e)}"}), 500

@app.route('/api/model/metrics', methods=['GET'])
def get_metrics():
    clickbait_model_pipeline.load_model()
    metrics = clickbait_model_pipeline.metrics
    if not metrics:
        db_metrics = get_latest_metrics()
        if db_metrics:
            metrics = db_metrics
        else:
            return jsonify({"success": False, "message": "Model performance records are not available."}), 404

    return jsonify({"success": True, "metrics": metrics})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
