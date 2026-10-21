-- Database Schema for Clickbait Detection System

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    avatar_url TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    headline TEXT NOT NULL,
    prediction TEXT NOT NULL,
    confidence REAL NOT NULL,
    top_words TEXT, -- JSON string of influential words & weights
    source_type TEXT DEFAULT 'text', -- 'text' or 'url'
    source_url TEXT DEFAULT NULL,   -- original URL if source_type is 'url'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS model_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    accuracy REAL NOT NULL,
    precision REAL NOT NULL,
    recall REAL NOT NULL,
    f1_score REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    uploaded_by INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
