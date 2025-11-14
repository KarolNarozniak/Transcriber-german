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
        # Opcjonalne seedowanie użytkowników z .env (email:haslo;...)
        seeded = app.config.get("AUTH_SEEDED_USERS", "")
        if seeded:
            pairs = [p.strip() for p in seeded.replace(",", ";").split(";") if p.strip()]
            for pair in pairs:
                if ":" in pair:
                    email, pwd = pair.split(":", 1)
                    email = email.strip().lower()
                    pwd = pwd.strip()
                    if email and pwd and not User.query.filter_by(email=email).first():
                        u = User(email=email)
                        u.set_password(pwd)
                        db.session.add(u)
            db.session.commit()

    # Rejestracja blueprintów
    from .auth.routes import auth_bp
    from .main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Sidebar: udostępnij listę lekcji w każdym szablonie
    @app.context_processor
    def inject_sidebar_lessons():
        try:
            from flask_login import current_user
            from .models import Lesson
            if getattr(current_user, 'is_authenticated', False):
                lessons = Lesson.query.filter_by(user_id=current_user.id).order_by(Lesson.created_at.desc()).limit(20).all()
            else:
                lessons = []
            return dict(nav_lessons=lessons)
        except Exception:
            return dict(nav_lessons=[])

    return app
