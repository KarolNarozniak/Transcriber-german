import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATA_DIR = os.getenv("DATA_DIR", "data")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB limit dla plików audio
    # Dozwolone rozszerzenia plików audio
    ALLOWED_EXTENSIONS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"}
    # Kontrola rejestracji i allowlisty loginu
    REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "false").lower() in ("1", "true", "yes")
    AUTH_ALLOWLIST_EMAILS = os.getenv("AUTH_ALLOWLIST_EMAILS", "")  # np. "test@gmail.com,kasia@test.com"
    AUTH_SEEDED_USERS = os.getenv("AUTH_SEEDED_USERS", "")  # np. "test@gmail.com:haslo123;kasia@test.com:test123"
