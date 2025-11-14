import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models import User
from .forms import LoginForm, RegisterForm


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"]) 
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        # Jeśli ustawiona allowlista, tylko te maile mogą się logować
        allowlist_raw = current_app.config.get("AUTH_ALLOWLIST_EMAILS", "")
        if allowlist_raw:
            allowed = {e.strip().lower() for e in allowlist_raw.replace(";", ",").split(",") if e.strip()}
            if email not in allowed:
                flash("To konto nie jest dozwolone do logowania.", "danger")
                return render_template("auth/login.html", form=form)

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Zalogowano pomyślnie.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))
        flash("Nieprawidłowy email lub hasło.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"]) 
def register():
    # Rejestracja tymczasowo wyłączona
    if not current_app.config.get("REGISTRATION_ENABLED", False):
        abort(404)
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Taki email już istnieje.", "warning")
        else:
            user = User(email=form.email.data.lower())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            # Utwórz katalog użytkownika w data
            user_dir = os.path.join(current_app.config["DATA_DIR"], str(user.id))
            os.makedirs(user_dir, exist_ok=True)
            flash("Konto utworzone. Możesz się zalogować.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Wylogowano.", "info")
    return redirect(url_for("auth.login"))
