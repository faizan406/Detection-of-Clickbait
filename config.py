import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clickbait-detection-secret-key-2026'
    DATABASE = os.path.join(BASE_DIR, 'database', 'clickbait.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
