import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATA_DIR = os.getenv("DATA_DIR", "data")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB limit dla plików audio
    # Dozwolone rozszerzenia plików audio
    ALLOWED_EXTENSIONS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"}
