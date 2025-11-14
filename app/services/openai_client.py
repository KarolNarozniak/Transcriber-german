import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


TRANSCRIBE_MODEL = "gpt-4o-transcribe"
SUMMARIZE_MODEL = "gpt-4o-mini"


def transcribe_audio_file(path: str, prompt: str | None = None) -> str:
    """
    Transkrybuje dźwięk za pomocą GPT-4o Transcribe.
    Zwraca czysty tekst (response_format="text").
    """
    # Uwaga: plik musi mieć < 25 MB zgodnie z dokumentacją
    with open(path, "rb") as f:
        result = client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=f,
            response_format="text",
            # prompt może pomóc z jakością transkrypcji
            prompt=(
                prompt
                or (
                    "To nagranie z zajęć na studiach. Większość będzie po polsku ale mogą się też pojawić lekcje niemieckiego."
                    "zostaw niemieckie słowa w oryginale, poprawnie rozpoznawaj nazwy własne i słownictwo lekcyjne."
                )
            ),
        )
        # SDK v1.53.0: wynik to obiekt z .text gdy response_format default json; dla text zwraca tekst.
        # Gdy response_format="text", SDK zwraca po prostu treść w polu .text lub bezpośrednio string?
        # Zgodnie z docs przyjmujemy .text dla spójności.
        return getattr(result, "text", str(result))


def generate_notes_from_text(transcript_text: str) -> tuple[str, str]:
    """
    Generuje polskie podsumowanie i wypunktowane notatki z transkryptu.
    Zwraca (summary, bullets_markdown).
    """
    system_msg = (
        "Jesteś asystentem nauczyciela. Otrzymasz transkrypt lekcji języka niemieckiego. "
        "Twoje zadanie: 1) przygotuj zwięzłe podsumowanie po polsku (3-6 zdań), "
        "2) przygotuj wypunktowane notatki po polsku z sekcjami: Słownictwo (DE->PL), "
        "Gramatyka (krótkie reguły + przykłady), Zadania domowe (konkretne polecenia). "
        "Zachowaj przejrzystą strukturę. Nie wymyślaj faktów poza transkryptem."
    )

    user_prompt = (
        "Transkrypt lekcji:\n\n" + transcript_text.strip() +
        "\n\nZwróć wynik w JSON: {\"summary\": \"...\", \"notes\": \"...\"}, "
        "gdzie notes to Markdown z listami punktowanymi."
    )

    resp = client.chat.completions.create(
        model=SUMMARIZE_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = resp.choices[0].message.content

    # Prosta próba odczytu JSON-u z odpowiedzi; jeśli nie wyjdzie, zwracamy całość jako notes
    import json
    summary = ""
    notes = ""
    if content:
        try:
            data = json.loads(content)
            summary = data.get("summary", "")
            notes = data.get("notes", "")
        except Exception:
            # Spróbuj znaleźć blok JSON w treści
            import re
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                try:
                    data = json.loads(match.group(0))
                    summary = data.get("summary", "")
                    notes = data.get("notes", "")
                except Exception:
                    notes = content
            else:
                notes = content
    return summary.strip(), notes.strip()
