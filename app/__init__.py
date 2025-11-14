import os
from flask import Flask
from .config import Config
from .extensions import db, login_manager
from .models import User

from dotenv import load_dotenv


def create_app():
    # Wczytaj zmienne środowiskowe z .env (jeśli istnieje)
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True, static_folder="static")
    app.config.from_object(Config())

    # Upewnij się, że katalog danych istnieje
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)

    # Inicjalizacja rozszerzeń
    db.init_app(app)
    login_manager.init_app(app)

    # Tworzenie bazy danych przy pierwszym uruchomieniu
    with app.app_context():
        db.create_all()

    # Rejestracja blueprintów
    from .auth.routes import auth_bp
    from .main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
