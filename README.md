# Transcriber German – Notatki z lekcji (Flask)

Aplikacja webowa w języku polskim do nagrywania, transkrypcji (w czasie rzeczywistym i z pliku) oraz generowania notatek z lekcji niemieckiego. Backend: Flask + OpenAI GPT‑4o Transcribe.

Spis treści
- Funkcje
- Architektura i dane
- Wymagania (Linux)
- Instalacja krok po kroku (Linux)
- Uruchomienie (dev) – `python run.py`
- Uruchomienie (prod) – Gunicorn na niestandardowym porcie
- Konfiguracja (.env)
- Dostosowanie streamingu (długość segmentu i overlap)
- Rozwiązywanie problemów
- Dalszy rozwój

## Funkcje
- Rejestracja/logowanie (Flask‑Login).
- Tworzenie lekcji (katalogów) i przesyłanie plików audio.
- Nagrywanie mikrofonu w przeglądarce (MediaRecorder), streaming w 3–10 s segmentach z overlapem.
- Transkrypcja przez OpenAI `gpt-4o-transcribe` (Audio API).
- Generowanie podsumowania i notatek (Chat Completions, `gpt-4o-mini`).
- Pobieranie nagrań i bezpieczne serwowanie plików.
- Prosta nawigacja z lewym paskiem lekcji.

## Architektura i dane
- Backend: Flask 3, SQLAlchemy + SQLite (domyślnie plikowo).
- Dane użytkownika (audio, fragmenty, notatki) są w katalogu `DATA_DIR/<user_id>/<timestamp>_<tytuł_lekcji>/`.
- Streaming live zapisuje fragmenty do `live_<id>/chunk_*.webm` w katalogu lekcji.
- Notatki (`Note`) i transkrypcje pełnych plików (`AudioFile.transcription_text`) przechowywane w SQLite.

## Wymagania (Linux)
- Python 3.10+ (sprawdzone także na 3.12/3.13).
- `git`.
- Dostępny klucz OpenAI (zmienna środowiskowa `.env`).

## Instalacja krok po kroku (Linux)
1) Sklonuj repozytorium
   - git clone https://github.com/KarolNarozniak/Transcriber-german.git
   - cd Transcriber-german

2) Utwórz i aktywuj wirtualne środowisko
   - python3 -m venv .venv
   - source .venv/bin/activate

3) Zainstaluj zależności
   - pip install --upgrade pip
   - pip install -r requirements.txt
   Uwaga: plik `requirements.txt` zawiera także `gunicorn` do uruchomienia produkcyjnego.

4) Skonfiguruj `.env`
   - cp .env.example .env
   - edytuj `.env` (patrz sekcja Konfiguracja).

5) Inicjalizacja bazy (SQLite)
   - Nie wymaga migracji – tabele tworzą się automatycznie przy pierwszym uruchomieniu (`db.create_all()`).

## Uruchomienie (dev)
- source .venv/bin/activate
- python run.py
- Przeglądarka: http://127.0.0.1:5000

## Uruchomienie (prod) – Gunicorn na niestandardowym porcie
Najprościej uruchomić Gunicorn na porcie 8000 (lub dowolnym innym) i związać na wszystkich interfejsach:
- source .venv/bin/activate
- gunicorn -w 2 -b 0.0.0.0:8000 run:app

Wyjaśnienia:
- `run:app` – wskazuje na obiekt `app` z pliku `run.py`.
- `-w 2` – liczba workerów; dostosuj do CPU i obciążenia.
- `-b 0.0.0.0:8000` – nasłuch na wszystkich interfejsach na porcie 8000.

Przykład z innym portem (np. 8081):
- gunicorn -w 4 -b 0.0.0.0:8081 run:app

Uruchomienie jako systemd (opcjonalnie):
1) Utwórz plik serwisu, np. `/etc/systemd/system/transcriber.service`:
```
[Unit]
Description=Transcriber German (Flask) Gunicorn service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/Transcriber-german
Environment="PYTHONPATH=/opt/Transcriber-german"
Environment="FLASK_ENV=production"
EnvironmentFile=/opt/Transcriber-german/.env
ExecStart=/opt/Transcriber-german/.venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 run:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
2) systemctl daemon-reload
3) systemctl enable --now transcriber

Za reverse proxy (nginx) wystaw statyczny host na 80/443 i przekieruj do `127.0.0.1:8000`.

## Konfiguracja (.env)
Dostępne zmienne (patrz `.env.example`):
- FLASK_SECRET_KEY – dowolny losowy ciąg (sesje, CSRF).
- OPENAI_API_KEY – klucz OpenAI do Audio API i Chat Completions.
- SQLALCHEMY_DATABASE_URI – domyślnie `sqlite:///app.db` (plik w katalogu projektu).
- DATA_DIR – katalog danych (audio, fragmenty, transkrypcje, notatki), np. `data` lub ścieżka absolutna `/var/lib/transcriber-data`.

Limity i formaty audio:
- Maksymalny rozmiar uploadu: 25 MB (zgodnie z ograniczeniem API OpenAI dla `/v1/audio/transcriptions`).
- Obsługiwane formaty: mp3, mp4, mpeg, mpga, m4a, wav, webm.

## Dostosowanie streamingu
Parametry front‑endu (przeglądarka): `app/static/js/record_overlap.js`
- `SEGMENT_MS` – długość pojedynczego segmentu (ms).
- `OVERLAP_MS` – nakładka między segmentami (ms).
- `STEP_MS = SEGMENT_MS - OVERLAP_MS` – co ile startuje nowy segment.

Transkrypcja live działa tak:
- Przeglądarka nagrywa segmenty jako kompletne pliki WebM/Opus (by uniknąć błędu „Audio file might be corrupted…”).
- Backend transkrybuje każdy segment przez `gpt-4o-transcribe` z „rolling promptem” (ostatnie ~400 znaków).
- Na STOP: zapisuje się notatka z finalnym tekstem oraz wysyłany jest pełny plik nagrania do lekcji, aby lista „Transkrypcje” nie była pusta.

## Rozwiązywanie problemów
- Brak importów (Flask/…): upewnij się, że aktywowałeś `.venv` i instalacja `pip install -r requirements.txt` przebiegła poprawnie.
- Błąd HTTP 400 „Audio file might be corrupted or unsupported”: zwykle fragment nie był kompletnym plikiem. Używamy nagrywania segmentów jako pełnych plików WebM/Opus – odśwież stronę, spróbuj ponownie w Chrome/Edge.
- Klucz OpenAI w `.env.example`: to tylko placeholder. Użyj własnego klucza i nie commituj `.env` (wykluczone przez `.gitignore`). W razie wycieku – od razu zrotuj klucz.
- Port zajęty: zmień `-b 0.0.0.0:PORT` w komendzie Gunicorna.

## Dalszy rozwój
- Przełączenie na Realtime API (WebSocket) z VAD.
- Diarization (`gpt-4o-transcribe-diarize`) i segmenty ze speaker labels.
- Eksport notatek do PDF/Markdown.
- Renderowanie Markdown notatek po stronie klienta.
- Migracje DB (Alembic) i Postgres w produkcji.

---
Pytania lub sugestie? Otwórz issue/PR w repozytorium.
