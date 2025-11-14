import os
from datetime import datetime
import shutil
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from markupsafe import escape

from ..extensions import db
from ..models import Lesson, AudioFile, Note, LiveTranscript
from .forms import CreateLessonForm, UploadAudioForm, RenameLessonForm, DeleteLessonForm
from ..services.openai_client import transcribe_audio_file, generate_notes_from_text


main_bp = Blueprint("main", __name__)


def allowed_file(filename: str) -> bool:
    from ..config import Config
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@main_bp.route("/")
@login_required
def dashboard():
    lessons = Lesson.query.filter_by(user_id=current_user.id).order_by(Lesson.created_at.desc()).all()
    form = CreateLessonForm()
    rename_form = RenameLessonForm()
    delete_form = DeleteLessonForm()
    return render_template("main/dashboard.html", lessons=lessons, form=form, rename_form=rename_form, delete_form=delete_form)


@main_bp.route("/lesson/create", methods=["POST"]) 
@login_required
def create_lesson():
    form = CreateLessonForm()
    if form.validate_on_submit():
        title = form.title.data.strip()
        user_dir = os.path.join(current_app.config["DATA_DIR"], str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        # katalog lekcji: data/<user>/<timestamp_title>
        folder_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secure_filename(title)}"
        lesson_dir = os.path.join(user_dir, folder_name)
        os.makedirs(lesson_dir, exist_ok=True)

        lesson = Lesson(user_id=current_user.id, title=title, folder_path=lesson_dir)
        db.session.add(lesson)
        db.session.commit()
        flash("Lekcja utworzona.", "success")
        return redirect(url_for("main.view_lesson", lesson_id=lesson.id))
    flash("Nie udało się utworzyć lekcji.", "danger")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/lesson/<int:lesson_id>/rename", methods=["POST"]) 
@login_required
def rename_lesson(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    form = RenameLessonForm()
    if form.validate_on_submit():
        new_title = form.title.data.strip()
        try:
            base_dir = os.path.dirname(lesson.folder_path)
            old_name = os.path.basename(lesson.folder_path)
            if "_" in old_name:
                ts_prefix = old_name.split("_", 1)[0]
            else:
                ts_prefix = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            new_folder = f"{ts_prefix}_{secure_filename(new_title)}"
            new_path = os.path.join(base_dir, new_folder)
            if os.path.abspath(new_path) != os.path.abspath(lesson.folder_path):
                if not os.path.exists(new_path):
                    os.rename(lesson.folder_path, new_path)
                lesson.folder_path = new_path
            lesson.title = new_title
            db.session.commit()
            flash("Zmieniono nazwę lekcji.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Nie udało się zmienić nazwy: {e}", "danger")
    else:
        flash("Niepoprawna nazwa.", "warning")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/lesson/<int:lesson_id>/delete", methods=["POST"]) 
@login_required
def delete_lesson(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    form = DeleteLessonForm()
    if form.validate_on_submit():
        try:
            user_dir = os.path.join(current_app.config["DATA_DIR"], str(current_user.id))
            abs_user_dir = os.path.abspath(user_dir)
            abs_lesson_dir = os.path.abspath(lesson.folder_path)
            if abs_lesson_dir.startswith(abs_user_dir) and os.path.isdir(abs_lesson_dir):
                shutil.rmtree(abs_lesson_dir, ignore_errors=True)

            AudioFile.query.filter_by(lesson_id=lesson.id).delete()
            Note.query.filter_by(lesson_id=lesson.id).delete()
            LiveTranscript.query.filter_by(lesson_id=lesson.id).delete()
            db.session.delete(lesson)
            db.session.commit()
            flash("Lekcja została usunięta.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Nie udało się usunąć lekcji: {e}", "danger")
    else:
        flash("Nie udało się potwierdzić usunięcia.", "warning")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/lesson/<int:lesson_id>")
@login_required
def view_lesson(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    upload_form = UploadAudioForm()
    audio_files = AudioFile.query.filter_by(lesson_id=lesson.id).order_by(AudioFile.created_at.desc()).all()
    notes = Note.query.filter_by(lesson_id=lesson.id).order_by(Note.created_at.desc()).all()
    return render_template("main/lesson.html", lesson=lesson, upload_form=upload_form, audio_files=audio_files, notes=notes)


@main_bp.route("/lesson/<int:lesson_id>/upload", methods=["POST"]) 
@login_required
def upload_audio(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    form = UploadAudioForm()
    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(lesson.folder_path, filename)
            file.save(save_path)
            audio = AudioFile(lesson_id=lesson.id, filename=filename, filepath=save_path)
            db.session.add(audio)
            db.session.commit()
            flash("Plik przesłany.", "success")
        else:
            flash("Nieprawidłowy format pliku.", "warning")
    else:
        flash("Nie wybrano pliku.", "warning")
    return redirect(url_for("main.view_lesson", lesson_id=lesson_id))


@main_bp.route("/lesson/<int:lesson_id>/record")
@login_required
def record_page(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    return render_template("main/record.html", lesson=lesson)


@main_bp.route("/api/lesson/<int:lesson_id>/stream/start", methods=["POST"])
@login_required
def stream_start(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    lt = LiveTranscript(lesson_id=lesson.id, text="")
    db.session.add(lt)
    db.session.commit()
    # katalog na fragmenty: <lesson.folder_path>/live_<id>
    live_dir = os.path.join(lesson.folder_path, f"live_{lt.id}")
    os.makedirs(live_dir, exist_ok=True)
    return jsonify({"live_id": lt.id})


def _dedupe_overlap(existing_tail: str, new_text: str) -> str:
    """Usuń potencjalne dublowanie na granicy fragmentów."""
    existing_tail = existing_tail.strip()
    new_text = new_text.lstrip()
    # szukaj najdłuższego sufiksu istniejącego tekstu będącego prefiksem nowego
    max_k = min(len(existing_tail), 120)
    for k in range(max_k, 0, -1):
        if new_text.startswith(existing_tail[-k:]):
            return new_text[k:]
    return new_text


@main_bp.route("/api/lesson/<int:lesson_id>/stream/chunk", methods=["POST"])
@login_required
def stream_chunk(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    live_id = request.form.get("live_id", type=int)
    idx = request.form.get("idx", type=int)
    overlap_ms = request.form.get("overlap_ms", type=int, default=500)
    if live_id is None or idx is None:
        return jsonify({"error": "Brak live_id lub idx"}), 400
    if "audio" not in request.files:
        return jsonify({"error": "Brak pliku audio"}), 400

    lt = LiveTranscript.query.get_or_404(live_id)
    if lt.lesson_id != lesson.id:
        return jsonify({"error": "Nieprawidłowy kontekst"}), 403

    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "Pusty plik"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Niedozwolone rozszerzenie"}), 400

    # zapisz fragment na dysk
    live_dir = os.path.join(lesson.folder_path, f"live_{lt.id}")
    os.makedirs(live_dir, exist_ok=True)
    ext = os.path.splitext(secure_filename(file.filename))[1]
    chunk_name = f"chunk_{idx:06d}{ext}"
    save_path = os.path.join(live_dir, chunk_name)
    file.save(save_path)

    # przygotuj rolling prompt z ostatnich ~400 znaków
    tail = (lt.text or "")[-400:]
    prompt = (
        "Kolejny fragment transkrypcji z lekcji niemieckiego. Kontynuuj naturalnie. "
        f"Poprzedni kontekst: {tail}"
    )

    # transkrybuj fragment
    text = transcribe_audio_file(save_path, prompt=prompt)
    # deduplikacja na granicy
    appended = _dedupe_overlap(tail, text)
    if appended:
        lt.text = ((lt.text or "") + (" " if lt.text else "") + appended).strip()
        db.session.commit()

    return jsonify({"delta": appended, "full": lt.text})


@main_bp.route("/api/live/<int:live_id>/text")
@login_required
def live_text(live_id):
    lt = LiveTranscript.query.get_or_404(live_id)
    # sprawdź własność poprzez lekcję
    lesson = Lesson.query.get_or_404(lt.lesson_id)
    if lesson.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({"text": lt.text or ""})


@main_bp.route("/api/lesson/<int:lesson_id>/stream/stop", methods=["POST"])
@login_required
def stream_stop(lesson_id):
    # Zapisz końcowy tekst z LiveTranscript jako notatkę (summary) i zwróć note_id
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    live_id_raw = request.json.get("live_id") if request.is_json else request.form.get("live_id")
    try:
        live_id = int(live_id_raw) if live_id_raw is not None else None
    except Exception:
        live_id = None
    note_id = None
    if live_id is not None:
        lt = LiveTranscript.query.get(live_id)
        if lt and lt.lesson_id == lesson.id:
            # utwórz notatkę z końcowej transkrypcji: wygeneruj podsumowanie i notatki
            full_text = (lt.text or "").strip()
            if full_text:
                try:
                    summary, bullets = generate_notes_from_text(full_text)
                except Exception:
                    summary, bullets = "", ""
                # dodaj rozwijany transkrypt poniżej notatek
                transcript_block = (
                    "<details><summary>Transkrypt (pokaż/ukryj)</summary>"
                    f"<pre style='white-space: pre-wrap;'>{escape(full_text)}</pre>"
                    "</details>"
                )
                combined_notes = (bullets or "") + ("\n\n" if bullets else "") + transcript_block
                note = Note(lesson_id=lesson.id, summary=summary or "Podsumowanie lekcji", notes=combined_notes)
                db.session.add(note)
                db.session.commit()
                note_id = note.id
    return jsonify({"ok": True, "live_id": live_id, "note_id": note_id})


@main_bp.route("/api/lesson/<int:lesson_id>/record/upload", methods=["POST"]) 
@login_required
def record_upload(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    if "audio" not in request.files:
        return jsonify({"error": "Brak pliku audio"}), 400
    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "Pusty plik"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Niedozwolone rozszerzenie"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(lesson.folder_path, filename)
    file.save(save_path)
    audio = AudioFile(lesson_id=lesson.id, filename=filename, filepath=save_path)
    db.session.add(audio)
    db.session.commit()
    return jsonify({"message": "Zapisano", "audio_id": audio.id})


@main_bp.route("/api/audio/<int:audio_id>/transcribe", methods=["POST"]) 
@login_required
def api_transcribe(audio_id):
    audio = AudioFile.query.join(Lesson).filter(AudioFile.id==audio_id, Lesson.user_id==current_user.id).first_or_404()
    try:
        text = transcribe_audio_file(audio.filepath)
        audio.transcription_text = text
        db.session.commit()
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/audio/<int:audio_id>/download")
@login_required
def download_audio(audio_id):
    audio = AudioFile.query.join(Lesson).filter(AudioFile.id==audio_id, Lesson.user_id==current_user.id).first_or_404()
    directory, fname = os.path.split(audio.filepath)
    # zabezpieczenie: plik musi być w katalogu danych użytkownika
    user_dir = os.path.join(current_app.config["DATA_DIR"], str(current_user.id))
    abs_user_dir = os.path.abspath(user_dir)
    abs_file_dir = os.path.abspath(directory)
    if not abs_file_dir.startswith(abs_user_dir):
        return "Forbidden", 403
    return send_from_directory(directory, fname, as_attachment=True)

@main_bp.route("/api/lesson/<int:lesson_id>/notes", methods=["POST"]) 
@login_required
def api_generate_notes(lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, user_id=current_user.id).first_or_404()
    # Zbierz transkrypcje z lekcji
    transcripts = [a.transcription_text for a in lesson.audio_files if a.transcription_text]
    if not transcripts:
        return jsonify({"error": "Brak transkrypcji do podsumowania."}), 400
    combined = "\n\n".join(transcripts)
    try:
        summary, bullets = generate_notes_from_text(combined)
        note = Note(lesson_id=lesson.id, summary=summary, notes=bullets)
        db.session.add(note)
        db.session.commit()
        return jsonify({"summary": summary, "notes": bullets, "note_id": note.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/data/<path:filename>")
@login_required
def data_files(filename):
    # Serwuj pliki tylko z katalogu użytkownika
    user_dir = os.path.join(current_app.config["DATA_DIR"], str(current_user.id))
    directory = os.path.abspath(user_dir)
    requested = os.path.abspath(os.path.join(directory, filename))
    if not requested.startswith(directory):
        return "Forbidden", 403
    return send_from_directory(directory, filename)
