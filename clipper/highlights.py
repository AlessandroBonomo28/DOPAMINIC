"""Rilevamento highlight: trova i momenti piu' rumorosi del video.

Approccio 100% locale: si analizza l'audio (RMS per finestre temporali) e si
restituiscono i segmenti con volume piu' alto, che in genere corrispondono ai
momenti piu' intensi (risate, urla, azione).
"""
import wave
from typing import List, Tuple

import numpy as np
from moviepy.editor import VideoFileClip

from . import TEMP_DIR, ensure_dirs

# Frequenza di campionamento usata per l'analisi (bassa = piu' veloce, sufficiente per l'RMS)
ANALYSIS_FPS = 22050


def extract_loudest_segments(
    video_path: str,
    segment_duration: float = 3.0,
    top_n: int = 5,
) -> List[Tuple[float, float]]:
    """Restituisce i `top_n` segmenti piu' rumorosi.

    Args:
        video_path: percorso del video da analizzare.
        segment_duration: durata in secondi di ogni finestra di analisi.
        top_n: quanti segmenti restituire.

    Returns:
        Lista di tuple (start_seconds, rms) ordinata per volume decrescente.
    """
    ensure_dirs()
    temp_wav = str(TEMP_DIR / "highlight_audio.wav")

    # Estrai l'audio in un WAV temporaneo (evita to_soundarray, rotto con numpy 2.x)
    clip = VideoFileClip(video_path)
    try:
        if clip.audio is None:
            raise ValueError("Il video non ha traccia audio: impossibile rilevare gli highlight.")
        clip.audio.write_audiofile(temp_wav, fps=ANALYSIS_FPS, nbytes=2, logger=None)
    finally:
        clip.close()

    with wave.open(temp_wav, "rb") as wf:
        n_channels = wf.getnchannels()
        framerate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    segment_samples = int(segment_duration * framerate)
    if segment_samples <= 0:
        raise ValueError("segment_duration troppo piccola.")

    num_segments = len(samples) // segment_samples
    loudness: List[Tuple[float, float]] = []
    for i in range(num_segments):
        segment = samples[i * segment_samples:(i + 1) * segment_samples]
        rms = float(np.sqrt(np.mean(segment ** 2)))
        loudness.append((i * segment_duration, rms))

    loudness.sort(key=lambda x: x[1], reverse=True)
    return loudness[:top_n]


def select_non_overlapping(
    segments: List[Tuple[float, float]],
    n: int,
    min_gap: float,
) -> List[float]:
    """Sceglie fino a `n` start-time distanti almeno `min_gap` secondi.

    Evita di generare clip sovrapposte/duplicate quando i picchi sono vicini.
    `segments` deve essere gia' ordinato per volume decrescente.
    """
    chosen: List[float] = []
    for start, _rms in segments:
        if all(abs(start - c) >= min_gap for c in chosen):
            chosen.append(start)
        if len(chosen) >= n:
            break
    return chosen
