"""Lettura/scrittura delle impostazioni persistenti (settings.json)."""
import json

from . import WRITABLE_BASE

SETTINGS_FILE = WRITABLE_BASE / "settings.json"

DEFAULTS = {
    # Output
    "n_clips": 5,
    "clip_duration": 23,
    # Crop verticale
    "opencv_face_tracking": False,   # False = crop centrale veloce, True = segue i volti (lento)
    # Watermark
    "watermark": True,
    "watermark_text": "@notset",
    # Sottotitoli (Whisper locale, opzionale)
    "subtitles_enabled": False,
    "subtitles_color": "#FFFFFF",
    "subtitle_font": "ptsans.ttf",   # file in fonts/
    "subtitle_fontsize": 80,
    "subtitle_stroke": 6,            # spessore contorno nero
    "whisper_model": "base",         # tiny | base | small | medium | large-v3
    "whisper_language": "it",        # "auto" oppure codice ISO ("it", "en", ...)
    "whisper_device": "cpu",         # cpu | cuda (GPU NVIDIA)
    # Assistente (avatar + sleep)
    "sleep_timeout": 30,             # secondi di inattivita' prima del sonno (0 = mai)
    "idle_gif": "assistant.gif",     # gif animata da sveglio
    "gotosleep_gif": "gotosleep.gif",  # gif transizione verso il sonno (una volta)
    "sleep_png": "sleep.png",        # immagine statica mentre dorme
    # Musica di sottofondo (in loop di default)
    "music_enabled": True,
    "music_volume": 50,              # 0-100
    "music_file": "",                # vuoto = brano di default (musica.mp3)
    # Livello di chill (persistente: secondi totali passati nella finestra)
    "chill_seconds": 0,
    # Tema interfaccia
    "theme": "light",                # light | dark
    "language": "it",                # it | en
    # Nome dell'assistente (criceto)
    "assistant_name": "CRI il criceto",
    # YouTube: metadati predefiniti per gli short programmati
    "yt_title": "",                  # titolo (max 100 caratteri)
    "yt_description": "",             # descrizione (max 5000 caratteri)
    # Animazioni visualizzatore (stile Windows Media Player) dietro al log
    "viz_enabled": True,
    # Effetti sonori (stile MSN)
    "sounds_enabled": True,
    "sound_send": "",                # vuoto = suono di default (invio)
    "sound_reply": "",               # vuoto = suono di default (risposta)
}


def load_settings() -> dict:
    """Carica le impostazioni, creando il file con i default se assente."""
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULTS)
        return dict(DEFAULTS)

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Completa eventuali chiavi mancanti con i default (retro-compatibilita')
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
