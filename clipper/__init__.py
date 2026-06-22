"""DOPAMINIC - long video to vertical shorts, 100% local.

Tutto gira in locale: rilevamento highlight (segmenti piu' rumorosi),
taglio clip, crop verticale (con o senza face-tracking OpenCV), watermark
e sottotitoli opzionali via Whisper locale. Nessuna API esterna, nessun
ImageMagick (il testo e' renderizzato con Pillow).
"""
from pathlib import Path

# Versione dell'app (confrontata con l'ultima release su GitHub per gli update).
# Tenere allineata a MyAppVersion in installer/app.iss.
APP_VERSION = "1.3"

# Radice del programma (cartella che contiene questo pacchetto). Contiene gli
# asset di sola lettura: data/ (cascade) e fonts/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FONTS_DIR = PROJECT_ROOT / "fonts"


def _is_writable(path: Path) -> bool:
    """Verifica reale di scrittura (os.access non e' affidabile su Windows)."""
    try:
        test = path / ".write_test"
        test.touch()
        test.unlink()
        return True
    except Exception:
        return False


def _writable_base() -> Path:
    """Cartella per file scrivibili (output, temp, settings).

    In sviluppo coincide con la radice del progetto. Da installato (es. in
    Program Files, sola lettura) ricade nella home dell'utente.
    """
    if _is_writable(PROJECT_ROOT):
        return PROJECT_ROOT
    base = Path.home() / "DOPAMINIC"
    base.mkdir(parents=True, exist_ok=True)
    return base


WRITABLE_BASE = _writable_base()
OUTPUT_DIR = WRITABLE_BASE / "output"
TEMP_DIR = WRITABLE_BASE / "temp"


def ensure_dirs() -> None:
    """Crea le cartelle di lavoro se non esistono."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
