# Transcriber German – Notatki z lekcji (Flask)

Aplikacja w języku polskim do nagrywania, transkrypcji i generowania notatek z lekcji niemieckiego. Backend: Flask, OpenAI GPT-4o Transcribe.

## Funkcje
- Rejestracja/logowanie (Flask-Login)
- Tworzenie lekcji (katalogów) i przesyłanie plików audio
- Nagrywanie mikrofonu w przeglądarce (MediaRecorder) i wysyłka do backendu
- Transkrypcja przez OpenAI `gpt-4o-transcribe`
- Generowanie podsumowania i notatek (chat completions, model `gpt-4o-mini`)

## Wymagania
- Python 3.10+
- Klucz OpenAI w `.env`

## Szybki start (Windows PowerShell)
1. Skopiuj `.env.example` do `.env` i ustaw:
   - `OPENAI_API_KEY`
   - `FLASK_SECRET_KEY` (losowy)
   - `SQLALCHEMY_DATABASE_URI` (np. `sqlite:///app.db`)
2. Utwórz i aktywuj wirtualne środowisko:
   - `python -m venv venv`
   - `./venv/Scripts/Activate.ps1`
3. Zainstaluj zależności:
   - `pip install -r requirements.txt`
4. Uruchom aplikację:
   - `python run.py`
5. Otwórz przeglądarkę: http://127.0.0.1:5000

Uwagi:
- Pliki audio i notatki trafiają do folderu `data/<user_id>/<lekcja>/`.
- Maksymalny rozmiar uploadu to 25 MB (zgodnie z dokumentacją OpenAI Audio API).
- Nie commituj `.env` do repozytorium (jest w `.gitignore`).
