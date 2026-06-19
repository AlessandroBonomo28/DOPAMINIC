"""Musica di sottofondo in loop (pygame, dipendenza opzionale on-demand).

Genera anche un brano di default (sintetizzato, royalty-free) se non ne viene
scelto uno. pygame riproduce wav/ogg/mp3 con volume e loop.
"""
import struct
import wave

from . import PROJECT_ROOT

# Brano di default scelto dall'utente (lo mette nella cartella del programma).
DEFAULT_MUSIC_FILE = PROJECT_ROOT / "musica.mp3"
# Fallback sintetizzato se musica.mp3 non c'e'.
FALLBACK_MUSIC = PROJECT_ROOT / "default_music.wav"
# Credit del brano di default.
MUSIC_CREDIT = "Rolling Down The Street, In My Katamari"


def _generate_default(path) -> None:
    """Sintetizza un loop chiptune calmo e nostalgico (melodia pentatonica + basso)."""
    import numpy as np

    sr = 44100
    beat = 0.34  # tempo lento, rilassato

    def synth(freq, dur, vol=0.3, harm=(1.0,), decay=2.2):
        n = int(sr * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        if freq <= 0:
            return np.zeros(n)
        env = np.minimum(1.0, t / 0.02) * np.exp(-decay * t)
        sig = sum(np.sin(2 * np.pi * freq * h * t) / h for h in harm)
        return vol * env * sig

    NOTE = {"A3": 220.0, "C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.0,
            "A4": 440.0, "C5": 523.25, "D5": 587.33, "E5": 659.25, "r": 0.0}
    # Melodia dolce in La minore pentatonico
    melody = [("E4", 2), ("G4", 1), ("A4", 3), ("G4", 1), ("E4", 1), ("D4", 2),
              ("C4", 2), ("D4", 1), ("E4", 3), ("D4", 1), ("C4", 1), ("A3", 2),
              ("E4", 2), ("G4", 1), ("A4", 1), ("C5", 1), ("D5", 3), ("C5", 1),
              ("A4", 2), ("G4", 1), ("E4", 1), ("D4", 2), ("E4", 4)]
    lead = np.concatenate([synth(NOTE[n], beat * b, vol=0.30, harm=(1.0, 0.5, 0.25))
                           for n, b in melody])

    # Basso lento sotto (Am - F - C - G)
    BASS = {"A2": 110.0, "F2": 87.31, "C3": 130.81, "G2": 98.0}
    bass = np.concatenate([synth(BASS[n], beat * 8, vol=0.16, harm=(1.0,), decay=0.7)
                           for n in ("A2", "F2", "C3", "G2")])

    length = len(lead)
    if len(bass) < length:
        bass = np.tile(bass, int(np.ceil(length / len(bass))))
    mix = lead + bass[:length]
    samples = (mix / max(1e-6, np.max(np.abs(mix))) * 0.55 * 32767).astype(np.int16)
    _write_wav(path, samples, sr)


def ensure_default_music() -> str:
    """Ritorna il brano di default: musica.mp3 se presente, altrimenti il fallback generato."""
    if DEFAULT_MUSIC_FILE.exists():
        return str(DEFAULT_MUSIC_FILE)
    if not FALLBACK_MUSIC.exists():
        try:
            _generate_default(FALLBACK_MUSIC)
        except Exception:
            return ""
    return str(FALLBACK_MUSIC)


def _write_wav(path, samples_int16, sr=44100):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"".join(struct.pack("<h", int(s)) for s in samples_int16))


def _tone(freqs, durs, sr=44100):
    """Sequenza di toni sine con leggero decay -> int16."""
    import numpy as np
    out = []
    for f, d in zip(freqs, durs):
        n = int(sr * d)
        t = np.linspace(0, d, n, endpoint=False)
        env = np.minimum(1.0, t / 0.005) * np.exp(-6.0 * t)
        out.append(0.5 * env * np.sin(2 * np.pi * f * t))
    sig = np.concatenate(out)
    return (sig / max(1e-6, np.max(np.abs(sig))) * 0.7 * 32767).astype("int16")


# Un suono per evento (stile MSN). Ognuno e' un breve tono sintetizzato.
_SOUND_SPECS = {
    "send":  ([900], [0.06]),               # tic invio
    "reply": ([660, 880], [0.10, 0.14]),    # do-din risposta
    "click": ([1300], [0.025]),             # click pulsante
    "tab":   ([520, 780], [0.04, 0.05]),    # cambio sezione
    "sleep": ([520, 330], [0.13, 0.20]),    # discendente (sbadiglio)
    "wake":  ([392, 523, 659], [0.06, 0.06, 0.10]),  # ascendente (sveglia)
}


def default_sound(name: str) -> str:
    """Percorso del suono di default per l'evento `name` (lo genera se manca)."""
    spec = _SOUND_SPECS.get(name, _SOUND_SPECS["click"])
    p = PROJECT_ROOT / f"default_{name}.wav"
    if not p.exists():
        try:
            _write_wav(p, _tone(*spec))
        except Exception:
            return ""
    return str(p)


class SoundPlayer:
    """Riproduce brevi effetti sonori (pygame.mixer.Sound). No-op se pygame manca."""

    def __init__(self):
        self._cache = {}

    def play(self, path: str, volume: float = 0.7) -> None:
        if not path:
            return
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            snd = self._cache.get(path)
            if snd is None:
                snd = pygame.mixer.Sound(path)
                self._cache[path] = snd
            snd.set_volume(max(0.0, min(1.0, volume)))
            snd.play()
        except Exception:
            pass


class MusicPlayer:
    """Wrapper su pygame.mixer.music: play in loop, volume, stop."""

    def __init__(self):
        self._inited = False
        self._playing = False

    @staticmethod
    def available() -> bool:
        try:
            import pygame  # noqa: F401
            return True
        except ImportError:
            return False

    def _ensure_init(self) -> bool:
        if self._inited:
            return True
        try:
            import pygame
            pygame.mixer.init()
            self._inited = True
        except Exception:
            self._inited = False
        return self._inited

    def play(self, path: str, volume: int = 50) -> bool:
        if not path or not self._ensure_init():
            return False
        try:
            import pygame
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume / 100.0)))
            pygame.mixer.music.play(loops=-1)
            self._playing = True
            return True
        except Exception:
            return False

    def stop(self) -> None:
        try:
            import pygame
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._playing = False

    def set_volume(self, volume: int) -> None:
        try:
            import pygame
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume / 100.0)))
        except Exception:
            pass

    def position_ms(self) -> int:
        """Millisecondi dall'inizio della riproduzione (-1 se non sta suonando)."""
        try:
            import pygame
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                return pygame.mixer.music.get_pos()
        except Exception:
            pass
        return -1


def _decode_mono(path, sr=22050):
    """Decodifica l'audio in campioni mono float (-1..1). Usa ffmpeg via moviepy."""
    import wave
    import numpy as np
    from moviepy.editor import AudioFileClip
    from . import TEMP_DIR

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(TEMP_DIR / "_viz_audio.wav")
    clip = AudioFileClip(path)
    try:
        clip.write_audiofile(tmp, fps=sr, nbytes=2, logger=None)
    finally:
        clip.close()
    with wave.open(tmp, "rb") as wf:
        ch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def analyze(path, n_bands=28, fps=15):
    """Pre-analizza lo spettro del brano. Ritorna (matrice [frame][bande] 0..1, fps) o None.

    Permette al visualizzatore di reagire alla musica usando la posizione di
    riproduzione (get_pos) per scegliere il frame.
    """
    try:
        import numpy as np
        samples, sr = _decode_mono(path)
        win = max(256, sr // fps)
        nframes = len(samples) // win
        if nframes < 1:
            return None
        window = np.hanning(win)
        nbins = win // 2 + 1  # lunghezza di rfft
        # Edge in float (NON int+unique: collasserebbe gli edge bassi lasciando
        # vuote le ultime bande). Forziamo hi>lo cosi' TUTTE le bande hanno un valore.
        edges = np.logspace(0, np.log10(nbins - 1), n_bands + 1)
        bands = np.zeros((nframes, n_bands), dtype=np.float32)
        for f in range(nframes):
            seg = samples[f * win:(f + 1) * win]
            spec = np.abs(np.fft.rfft(seg * window))
            for b in range(n_bands):
                lo = int(edges[b])
                hi = max(lo + 1, int(edges[b + 1]))
                bands[f, b] = spec[lo:hi].mean()
        bands = np.log1p(bands)
        gpeak = bands.max() or 1.0
        # Normalizzazione MISTA per-banda/globale: gli alti (deboli) restano visibili
        # ma le dinamiche d'insieme si conservano (momenti calmi = barre basse).
        col_peak = bands.max(axis=0)
        divisor = np.maximum(0.5 * col_peak + 0.5 * gpeak, gpeak * 0.2)
        bands = np.clip(bands / divisor, 0.0, 1.0)
        return bands, fps
    except Exception:
        return None
