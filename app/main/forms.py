from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired, Length


class CreateLessonForm(FlaskForm):
    title = StringField("Nazwa lekcji", validators=[DataRequired(), Length(min=2, max=200)])
    submit = SubmitField("Utwórz lekcję")


class UploadAudioForm(FlaskForm):
    file = FileField("Plik audio", validators=[DataRequired()])
    submit = SubmitField("Wyślij")


class RenameLessonForm(FlaskForm):
    title = StringField("Nowa nazwa lekcji", validators=[DataRequired(), Length(min=2, max=200)])
    submit = SubmitField("Zapisz")


class DeleteLessonForm(FlaskForm):
    submit = SubmitField("Usuń lekcję")
