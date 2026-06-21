"""Trascrizione completa del video con cache su disco + rilevamento monologhi.

Usata da due punti:
- highlight "by talk": trova i monologhi (i tratti di parlato continuo piu'
  lunghi), scartando rumore/musica/allucinazioni.
- sottotitoli: quando la trascrizione completa e' disponibile (modalita' talk,
  oppure cache gia' presente), i sottotitoli di ogni short si ottengono
  *affettando* questa trascrizione, senza ri-trascrivere clip per clip.

La trascrizione completa e' costosa su video lunghi, quindi viene salvata su
disco e riusata finche' video (data/dimensione), modello e lingua non cambiano.
"""
import hashlib
import json
import os
import time
from typing import Callable, List, Optional, Tuple

from . import TEMP_DIR, WRITABLE_BASE, ensure_dirs
from .subtitles import _group_words

BarCb = Callable[[str], None]
LogCb = Callable[[str], None]
# Formato moviepy SubtitlesClip: ((start, end), testo)
Subtitle = Tuple[Tuple[float, float], str]

TRANSCRIPTS_DIR = WRITABLE_BASE / "transcripts"
CACHE_VERSION = 1

# Soglie per scartare i segmenti che non sono parlato (rumore/musica/allucinazioni).
# Sono gli indicatori standard di faster-whisper.
_MAX_NO_SPEECH = 0.6       # probabilita' di "niente voce": sopra = scarto
_MIN_AVG_LOGPROB = -1.0    # confidenza media: sotto = probabile allucinazione
_MAX_COMPRESSION = 2.4     # ripetitivita': sopra = testo allucinato/loop
_MIN_WORDS = 2             # meno parole di cosi' = frammento, non parlato utile

# Gap massimo (s) entro cui due segmenti di parlato si fondono nello stesso
# monologo: un respiro o una pausa breve non deve spezzare il discorso.
_MERGE_GAP = 2.0

# Audio estratto a 16 kHz mono: sufficiente per Whisper, file piccolo.
_ASR_FPS = 16000


# --------------------------------------------------------------------------- #
# Cache su disco
# --------------------------------------------------------------------------- #
def _cache_key(video_path: str, model: str, language: str) -> str:
    try:
        mtime = int(os.path.getmtime(video_path))
        size = os.path.getsize(video_path)
    except OSError:
        mtime = size = 0
    raw = f"{CACHE_VERSION}|{os.path.abspath(video_path)}|{size}|{mtime}|{model}|{language}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _cache_path(video_path: str, model: str, language: str):
    return TRANSCRIPTS_DIR / f"{_cache_key(video_path, model, language)}.json"


def load_cached(video_path: str, model: str, language: str) -> Optional[dict]:
    """Ritorna la trascrizione in cache se valida, altrimenti None."""
    p = _cache_path(video_path, model, language)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(video_path: str, model: str, language: str, transcript: dict) -> None:
    try:
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_cache_path(video_path, model, language), "w", encoding="utf-8") as f:
            json.dump(transcript, f)
    except Exception:
        pass  # la cache e' un'ottimizzazione: se fallisce, pazienza


# --------------------------------------------------------------------------- #
# Trascrizione completa (con barra di avanzamento)
# --------------------------------------------------------------------------- #
def _fmt(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _bar(frac: float, width: int = 20) -> str:
    filled = int(round(max(0.0, min(1.0, frac)) * width))
    return "#" * filled + "." * (width - filled)


def _extract_full_audio(video_path: str) -> str:
    from moviepy.editor import VideoFileClip

    ensure_dirs()
    wav = str(TEMP_DIR / "full_audio.wav")
    clip = VideoFileClip(video_path)
    try:
        if clip.audio is None:
            raise ValueError("Il video non ha traccia audio: impossibile trascrivere.")
        clip.audio.write_audiofile(wav, fps=_ASR_FPS, nbytes=2, logger=None)
    finally:
        clip.close()
    return wav


def get_full_transcript(
    video_path: str,
    model: str,
    language: str,
    device: str,
    bar_cb: Optional[BarCb] = None,
    log_cb: Optional[LogCb] = None,
) -> dict:
    """Trascrizione completa del video: {"duration": float, "segments": [...]}.

    Usa la cache su disco se valida; altrimenti trascrive (aggiornando `bar_cb`
    con una barra di avanzamento) e salva il risultato.
    """
    cached = load_cached(video_path, model, language)
    if cached is not None:
        if log_cb:
            log_cb("[talk] Trascrizione completa trovata in cache: nessuna ri-trascrizione.")
        return cached

    from .subtitles import WhisperTranscriber

    if log_cb:
        log_cb("[talk] Trascrizione completa del video (una volta sola, poi resta in cache)...")
    transcriber = WhisperTranscriber(model_size=model, language=language, device=device)
    wav = _extract_full_audio(video_path)

    start_wall = time.time()

    def progress(frac: float, pos: float, total: float) -> None:
        if bar_cb is None:
            return
        elapsed = time.time() - start_wall
        eta = (elapsed / frac - elapsed) if frac > 0.02 else 0.0
        eta_txt = f"  (~{_fmt(eta)} rimasti)" if eta > 1 else ""
        bar_cb(f"[trascrizione] [{_bar(frac)}] {int(frac * 100):3d}%  "
               f"{_fmt(pos)}/{_fmt(total)}{eta_txt}")

    segments, total = transcriber.transcribe_full(wav, progress=progress)
    transcript = {"duration": total, "segments": segments}
    _save_cache(video_path, model, language, transcript)
    if bar_cb is not None:
        bar_cb(f"[trascrizione] [{_bar(1.0)}] 100%  completata in {_fmt(time.time() - start_wall)}")
    return transcript


# --------------------------------------------------------------------------- #
# Rilevamento monologhi (highlight "by talk")
# --------------------------------------------------------------------------- #
def _seg_words(seg: dict) -> int:
    return len(seg.get("words") or []) or len((seg.get("text") or "").split())


def _is_speech(seg: dict) -> bool:
    """True se il segmento e' parlato vero (non rumore/musica/allucinazione)."""
    return (
        seg.get("no_speech_prob", 0.0) <= _MAX_NO_SPEECH
        and seg.get("avg_logprob", 0.0) >= _MIN_AVG_LOGPROB
        and seg.get("compression_ratio", 0.0) <= _MAX_COMPRESSION
        and _seg_words(seg) >= _MIN_WORDS
    )


def find_monologue_clips(
    transcript: dict,
    clip_duration: float,
    n: int,
    video_duration: float,
) -> List[Tuple[float, float]]:
    """Ritorna fino a `n` intervalli (start, end) sui monologhi piu' lunghi.

    Unisce i segmenti di parlato vicini in monologhi, li ordina per durata e
    prende i piu' lunghi non sovrapposti, ancorando la finestra all'inizio del
    monologo (gia' allineato a un confine di frase).
    """
    segs = sorted((s for s in transcript.get("segments", []) if _is_speech(s)),
                  key=lambda s: s["start"])
    if not segs:
        return []

    monologues: List[List[float]] = []  # [start, end]
    for s in segs:
        if monologues and s["start"] - monologues[-1][1] <= _MERGE_GAP:
            monologues[-1][1] = max(monologues[-1][1], s["end"])
        else:
            monologues.append([s["start"], s["end"]])

    # I monologhi piu' lunghi per primi.
    monologues.sort(key=lambda m: m[1] - m[0], reverse=True)

    chosen: List[Tuple[float, float]] = []
    for ms, _me in monologues:
        start = ms
        end = start + clip_duration
        if end > video_duration:
            end = video_duration
            start = max(0.0, end - clip_duration)
        # Scarta se si sovrappone a una finestra gia' scelta.
        if all(end <= cs or start >= ce for cs, ce in chosen):
            chosen.append((start, end))
        if len(chosen) >= n:
            break

    chosen.sort()
    return chosen


# --------------------------------------------------------------------------- #
# Sottotitoli per slicing della trascrizione completa
# --------------------------------------------------------------------------- #
def slice_subtitles(
    transcript: dict,
    start: float,
    end: float,
    max_chars: int = 16,
) -> List[Subtitle]:
    """Estrae i sottotitoli per la finestra [start, end] dalla trascrizione completa.

    I timestamp vengono riportati a tempo-clip (0 = inizio dello short). Riusa
    lo stesso raggruppamento in righe brevi dei sottotitoli per-clip.
    """
    words = []
    for seg in transcript.get("segments", []):
        for (ws, we, wt) in seg.get("words") or []:
            if start <= ws < end:
                words.append((ws - start, min(we, end) - start, wt))
    if not words:
        return []
    lines = _group_words(words, max_chars)
    lines = [(s, e, t) for s, e, t in lines if e > s and t.strip(" -–—.,")]
    return [((s, e), t) for s, e, t in lines]
