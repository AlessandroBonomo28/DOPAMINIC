"""Sottotitoli generati in locale con Whisper (faster-whisper).

Opzionale: importato solo quando i sottotitoli sono abilitati, cosi' l'app
funziona anche senza faster-whisper installato.

I sottotitoli usano i timestamp **per parola** di Whisper (word_timestamps),
poi le parole vengono raggruppate in righe brevi (stile shorts) mantenendo i
tempi reali di inizio/fine -> sincronizzazione precisa con il parlato.
"""
from pathlib import Path
from typing import List, Tuple

from . import TEMP_DIR

# (start_seconds, end_seconds, testo)
Word = Tuple[float, float, str]
# Formato richiesto da moviepy SubtitlesClip: ((start, end), testo)
Subtitle = Tuple[Tuple[float, float], str]


def _format_timestamp(seconds: float) -> str:
    """Converte i secondi nel formato SRT HH:MM:SS,mmm."""
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _group_words(words: List[Word], max_chars: int) -> List[Word]:
    """Raggruppa le parole in righe brevi (<= max_chars), conservando i tempi reali."""
    lines: List[Word] = []
    buf: List[Word] = []
    buf_chars = 0

    for start, end, text in words:
        extra = len(text) + (1 if buf else 0)
        if buf and buf_chars + extra > max_chars:
            lines.append((buf[0][0], buf[-1][1], " ".join(w[2] for w in buf)))
            buf, buf_chars = [], 0
            extra = len(text)
        buf.append((start, end, text))
        buf_chars += extra

    if buf:
        lines.append((buf[0][0], buf[-1][1], " ".join(w[2] for w in buf)))
    return lines


def _build_srt(lines: List[Word]) -> str:
    entries = []
    for i, (start, end, text) in enumerate(lines, start=1):
        entries.append(f"{i}\n{_format_timestamp(start)} --> {_format_timestamp(end)}\n{text}\n")
    return "\n".join(entries)


def _add_cuda_dll_dirs() -> None:
    """Su Windows aggiunge al search path le DLL CUDA installate via pip (nvidia-*-cu12)."""
    import os
    try:
        import nvidia
    except ImportError:
        return
    for base in nvidia.__path__:
        for sub in ("cublas", "cudnn"):
            bin_dir = os.path.join(base, sub, "bin")
            if os.path.isdir(bin_dir) and hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(bin_dir)
                except OSError:
                    pass


def _build_model(model_size: str, device: str):
    """Crea un WhisperModel sul device richiesto."""
    from faster_whisper import WhisperModel

    if device == "cuda":
        _add_cuda_dll_dirs()
        return WhisperModel(model_size, device="cuda", compute_type="float16")
    return WhisperModel(model_size, device="cpu", compute_type="int8")


class WhisperTranscriber:
    """Trascrittore riutilizzabile: carica il modello UNA volta e lo riusa per
    tutte le clip. Ricaricare il modello a ogni clip (soprattutto su GPU, con la
    VRAM ancora occupata dall'istanza precedente) causava blocchi/lentezza enorme.
    """

    def __init__(self, model_size: str = "base", language: str = "it",
                 device: str = "cpu", max_chars: int = 16):
        try:
            from faster_whisper import WhisperModel  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Sottotitoli abilitati ma 'faster-whisper' non e' installato.\n"
                "Installa con:  pip install faster-whisper"
            ) from exc
        self.model_size = model_size
        self.language = language
        self.device = device
        self.max_chars = max_chars
        self._model = None

    def _model_obj(self):
        if self._model is None:
            self._model = _build_model(self.model_size, self.device)
        return self._model

    def _words(self, audio_path: str) -> List[Word]:
        model = self._model_obj()
        segments, _info = model.transcribe(
            audio_path,
            language=None if self.language == "auto" else self.language,
            word_timestamps=True,
            vad_filter=True,                 # isola il parlato (musica/silenzi/rumore)
            condition_on_previous_text=False,  # evita derive di lingua/ripetizioni
        )
        words: List[Word] = []
        for seg in segments:  # qui scatta l'encode (eventuale errore CUDA emerge ora)
            if seg.words:
                for w in seg.words:
                    text = w.word.strip()
                    if text:
                        words.append((w.start, w.end, text))
            elif seg.text.strip():
                words.append((seg.start, seg.end, seg.text.strip()))
        return words

    def _full(self, audio_path: str, progress=None):
        """Trascrive l'intero file. Ritorna (lista_segmenti, durata_totale).

        Ogni segmento e' un dict con metadati (no_speech_prob, avg_logprob,
        compression_ratio) utili a scartare il non-parlato, piu' le parole con
        i timestamp assoluti. `progress(frazione, posizione_s, totale_s)` viene
        chiamato a ogni segmento per la barra di avanzamento.
        """
        model = self._model_obj()
        segments, info = model.transcribe(
            audio_path,
            language=None if self.language == "auto" else self.language,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        total = float(getattr(info, "duration", 0.0) or 0.0)
        out = []
        for seg in segments:  # qui scatta l'encode (eventuale errore CUDA emerge ora)
            words = []
            if seg.words:
                for w in seg.words:
                    text = w.word.strip()
                    if text:
                        words.append((float(w.start), float(w.end), text))
            out.append({
                "start": float(seg.start),
                "end": float(seg.end),
                "text": seg.text.strip(),
                "no_speech_prob": float(getattr(seg, "no_speech_prob", 0.0)),
                "avg_logprob": float(getattr(seg, "avg_logprob", 0.0)),
                "compression_ratio": float(getattr(seg, "compression_ratio", 0.0)),
                "words": words,
            })
            if progress is not None and total > 0:
                progress(min(1.0, seg.end / total), float(seg.end), total)
        return out, total

    def transcribe_full(self, audio_path: str, progress=None):
        """Come `_full`, con fallback a CPU (una volta) se la GPU non è usabile."""
        try:
            return self._full(audio_path, progress)
        except Exception as exc:  # noqa: BLE001
            if self.device == "cuda":
                print(f"[!] GPU non utilizzabile ({exc}). Passo alla CPU.")
                self.device = "cpu"
                self._model = None
                return self._full(audio_path, progress)
            raise

    def transcribe(self, audio_path: str) -> List[Subtitle]:
        """Trascrive una clip. Fallback a CPU (una volta) se la GPU non è usabile."""
        try:
            words = self._words(audio_path)
        except Exception as exc:  # noqa: BLE001
            if self.device == "cuda":
                print(f"[!] GPU non utilizzabile ({exc}). Passo alla CPU.")
                self.device = "cpu"
                self._model = None  # ricarica su CPU e riusa per le prossime clip
                words = self._words(audio_path)
            else:
                raise

        lines = _group_words(words, self.max_chars)
        lines = [(s, e, t) for s, e, t in lines if e > s and t.strip(" -–—.,")]

        # .srt di riferimento (UTF-8); per il rendering passiamo la lista (vedi pipeline)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        srt_path = TEMP_DIR / f"{Path(audio_path).stem}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(_build_srt(lines))
        return [((s, e), t) for s, e, t in lines]


def generate_subtitles(
    audio_path: str,
    model_size: str = "base",
    language: str = "it",
    device: str = "cpu",
    max_chars: int = 16,
) -> List[Subtitle]:
    """Trascrive un singolo file audio (crea un transcriber usa-e-getta)."""
    return WhisperTranscriber(model_size, language, device, max_chars).transcribe(audio_path)
