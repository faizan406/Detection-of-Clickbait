import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "clickbait.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    # Check and perform safe schema migration for prediction_history and users table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(prediction_history)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    
    try:
        if 'source_type' not in existing_cols:
            cursor.execute("ALTER TABLE prediction_history ADD COLUMN source_type TEXT DEFAULT 'text'")
    except Exception:
        pass

    try:
        if 'source_url' not in existing_cols:
            cursor.execute("ALTER TABLE prediction_history ADD COLUMN source_url TEXT DEFAULT NULL")
    except Exception:
        pass

    try:
        if 'authenticity_status' not in existing_cols:
            cursor.execute("ALTER TABLE prediction_history ADD COLUMN authenticity_status TEXT DEFAULT 'Unverified'")
    except Exception:
        pass

    try:
        if 'authenticity_score' not in existing_cols:
            cursor.execute("ALTER TABLE prediction_history ADD COLUMN authenticity_score REAL DEFAULT 50.0")
    except Exception:
        pass

    try:
        if 'authenticity_details' not in existing_cols:
            cursor.execute("ALTER TABLE prediction_history ADD COLUMN authenticity_details TEXT DEFAULT NULL")
    except Exception:
        pass

    try:
        cursor.execute("PRAGMA table_info(users)")
        existing_user_cols = [col[1] for col in cursor.fetchall()]
        if 'avatar_url' not in existing_user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT DEFAULT NULL")
    except Exception:
        pass
        
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# User Management
def create_user(name, email, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", 
                       (name, email, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def update_user_password(email, new_password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_password_hash, email))
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows > 0

def update_user_avatar(user_id, avatar_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user_id))
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows > 0

from datetime import datetime

# History Logging
def save_prediction(user_id, headline, prediction, confidence, top_words, source_type='text', source_url=None,
                    authenticity_status='Unverified', authenticity_score=50.0, authenticity_details=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    top_words_json = json.dumps(top_words) if top_words else "[]"
    auth_details_json = json.dumps(authenticity_details) if authenticity_details else "{}"
    local_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO prediction_history (user_id, headline, prediction, confidence, top_words, source_type, source_url, created_at,
                                        authenticity_status, authenticity_score, authenticity_details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, headline, prediction, confidence, top_words_json, source_type, source_url, local_now,
          authenticity_status, authenticity_score, auth_details_json))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def get_history(user_id=None, search=None, filter_type=None, source_type_filter=None, auth_filter=None):
    conn = get_db_connection()
    query = "SELECT * FROM prediction_history WHERE 1=1"
    params = []
    
    if user_id:
        # Only show records belonging to this user
        query += " AND user_id = ?"
        params.append(user_id)
    else:
        # Not logged in — return nothing
        return []

    if search:
        query += " AND (headline LIKE ? OR source_url LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    if filter_type and filter_type.lower() != 'all':
        query += " AND prediction = ?"
        params.append(filter_type)
    if source_type_filter and source_type_filter.lower() != 'all':
        query += " AND source_type = ?"
        params.append(source_type_filter.lower())
    if auth_filter and auth_filter.lower() != 'all':
        query += " AND authenticity_status LIKE ?"
        params.append(f"%{auth_filter}%")
        
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    results = []
    for r in rows:
        item = dict(r)
        item['top_words'] = json.loads(item['top_words']) if item['top_words'] else []
        if 'source_type' not in item or not item['source_type']:
            item['source_type'] = 'text'
        if 'source_url' not in item:
            item['source_url'] = None
        if 'authenticity_status' not in item or not item['authenticity_status']:
            item['authenticity_status'] = 'Unverified'
        if 'authenticity_score' not in item:
            item['authenticity_score'] = 50.0
        if 'authenticity_details' in item and item['authenticity_details']:
            try:
                item['authenticity_details'] = json.loads(item['authenticity_details'])
            except Exception:
                item['authenticity_details'] = {}
        else:
            item['authenticity_details'] = {}
        results.append(item)
    return results

def delete_history_record(record_id, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM prediction_history WHERE id = ? AND (user_id = ? OR user_id IS NULL)", (record_id, user_id))
    else:
        cursor.execute("DELETE FROM prediction_history WHERE id = ?", (record_id,))
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows > 0

def clear_all_history(user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM prediction_history WHERE user_id = ? OR user_id IS NULL", (user_id,))
    else:
        cursor.execute("DELETE FROM prediction_history")
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows > 0

# Model Metrics
def save_model_metrics(model_name, accuracy, precision, recall, f1_score, sample_count):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO model_metrics (model_name, accuracy, precision, recall, f1_score, sample_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (model_name, accuracy, precision, recall, f1_score, sample_count))
    conn.commit()
    conn.close()

def get_latest_metrics():
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM model_metrics ORDER BY trained_at DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

# Dataset Management
def save_dataset_record(filename, row_count, uploaded_by=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO datasets (filename, row_count, uploaded_by)
        VALUES (?, ?, ?)
    """, (filename, row_count, uploaded_by))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id
