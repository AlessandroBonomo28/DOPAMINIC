"""Uploader YouTube: OAuth del proprio canale + upload programmato (publishAt).

Stile "Buffer": definisci slot settimanali, assegni automaticamente i video
della cartella output agli slot futuri e li carichi come privati con orario di
pubblicazione (status.publishAt). YouTube li pubblica da solo all'orario.

Le librerie Google sono opzionali e importate in modo lazy (installate on-demand).
"""
import json
from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, Tuple

from . import WRITABLE_BASE

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
TOKEN_FILE = WRITABLE_BASE / "youtube_token.json"
SCHEDULE_FILE = WRITABLE_BASE / "youtube_schedule.json"

# Quota giornaliera YouTube: 10.000 unità, ~1.600 per upload -> ~6 upload/giorno.
MAX_UPLOADS_PER_DAY = 6

# Uno slot settimanale: (giorno 0=lunedì..6=domenica, "HH:MM")
Slot = Tuple[int, str]
WEEKDAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]


# --------------------------------------------------------------- disponibilità

def available() -> bool:
    """True se le librerie Google sono installate."""
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
        return True
    except ImportError:
        return False


# --------------------------------------------------------------------- OAuth

def _load_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not TOKEN_FILE.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def is_authorized() -> bool:
    try:
        creds = _load_creds()
        return bool(creds and creds.valid)
    except Exception:
        return False


def authorize(client_secret_path: str) -> str:
    """Esegue il flusso OAuth (apre il browser) e salva il token. Ritorna il nome del canale."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return channel_title() or "(canale)"


def channel_title() -> Optional[str]:
    try:
        from googleapiclient.discovery import build
        creds = _load_creds()
        if not creds:
            return None
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        resp = yt.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        return items[0]["snippet"]["title"] if items else None
    except Exception:
        return None


# -------------------------------------------------------------------- upload

def upload(
    video_path: str,
    title: str,
    description: str = "",
    publish_at: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """Carica un video. Se `publish_at` è dato, lo carica come privato con quell'orario
    di pubblicazione programmata. Ritorna l'id del video."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = _load_creds()
    if not creds:
        raise RuntimeError("Non autenticato: configura prima l'accesso al canale YouTube.")
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    status = {"privacyStatus": "private" if publish_at else "public", "selfDeclaredMadeForKids": False}
    if publish_at:
        status["publishAt"] = publish_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    body = {
        "snippet": {"title": title[:100], "description": description, "tags": tags or [], "categoryId": "22"},
        "status": status,
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    return response["id"]


# ------------------------------------------------------------ slot / calendario

def upcoming_slot_datetimes(slots: List[Slot], start: datetime, count: int) -> List[datetime]:
    """Genera i prossimi `count` orari (datetime) a partire da `start` dati gli slot settimanali."""
    if not slots:
        return []
    result: List[datetime] = []
    day = start.date()
    # Ordina gli slot per (giorno, ora) per coerenza
    sorted_slots = sorted(slots, key=lambda s: (s[0], s[1]))
    guard = 0
    while len(result) < count and guard < 366:
        for weekday, hhmm in sorted_slots:
            if day.weekday() != weekday:
                continue
            h, m = (int(x) for x in hhmm.split(":"))
            dt = datetime.combine(day, time(h, m))
            if dt > start:
                result.append(dt)
                if len(result) >= count:
                    break
        day += timedelta(days=1)
        guard += 1
    return result


def assign_to_slots(
    video_paths: List[str], slots: List[Slot], start: Optional[datetime] = None
) -> List[Tuple[str, datetime]]:
    """Assegna ogni video al prossimo slot libero. Ritorna [(path, publish_dt), ...]."""
    start = start or datetime.now()
    dts = upcoming_slot_datetimes(slots, start, len(video_paths))
    return list(zip(video_paths, dts))


# ------------------------------------------------------------ persistenza config

def load_schedule() -> dict:
    if SCHEDULE_FILE.exists():
        try:
            return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Default: 3 slot/settimana alle 18:00 (Lun/Mer/Ven)
    return {"slots": [[0, "18:00"], [2, "18:00"], [4, "18:00"]]}


def save_schedule(data: dict) -> None:
    SCHEDULE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
