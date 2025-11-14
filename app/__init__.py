import os
from datetime import datetime
from flask import Flask
from .config import Config
from .extensions import db, login_manager
from .models import User

from dotenv import load_dotenv, find_dotenv
from sqlalchemy.exc import IntegrityError


def create_app():
    # Wczytaj zmienne środowiskowe z .env niezależnie od katalogu roboczego
    # find_dotenv() przeszukuje nadrzędne katalogi i znajdzie plik w root repo
    load_dotenv(find_dotenv(), override=False)

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
        # Bezpieczne seedowanie użytkowników z .env (email:haslo;...) tylko raz
        seeded = app.config.get("AUTH_SEEDED_USERS", "")
        if seeded:
            seed_marker = os.path.join(app.config["DATA_DIR"], ".seed_done")
            if not os.path.exists(seed_marker):
                pairs = [p.strip() for p in seeded.replace(",", ";").split(";") if p.strip()]
                for pair in pairs:
                    if ":" in pair:
                        email, pwd = pair.split(":", 1)
                        email = email.strip().lower()
                        pwd = pwd.strip()
                        if not email or not pwd:
                            continue
                        try:
                            # Spróbuj wstawić; jeśli już istnieje (wyścig między workerami) – zignoruj
                            if not User.query.filter_by(email=email).first():
                                u = User(email=email)
                                u.set_password(pwd)
                                db.session.add(u)
                                db.session.commit()
                        except IntegrityError:
                            db.session.rollback()
                            # inny worker zdążył – ignorujemy
                # Zapisz marker, aby nie seedować ponownie przy kolejnych restartach
                try:
                    with open(seed_marker, "w", encoding="utf-8") as fh:
                        fh.write(f"seeded_at={datetime.utcnow().isoformat()}\n")
                except Exception:
                    pass

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
