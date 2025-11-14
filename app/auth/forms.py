from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Hasło", validators=[DataRequired()])
    submit = SubmitField("Zaloguj")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Hasło",
        validators=[DataRequired(), Length(min=6, message="Min. 6 znaków")],
    )
    confirm = PasswordField(
        "Powtórz hasło",
        validators=[DataRequired(), EqualTo("password", message="Hasła muszą być takie same")],
    )
    submit = SubmitField("Zarejestruj")
