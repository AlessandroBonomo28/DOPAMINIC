"""Crop verticale 9:16 dei clip.

Due modalita':
  - crop centrale (veloce): ritaglia il centro dell'inquadratura.
  - face-tracking (OpenCV, lento): segue il volto piu' centrato spostando
    il ritaglio segmento per segmento.
"""
from functools import lru_cache

import numpy as np
from moviepy.editor import VideoClip, concatenate_videoclips
from moviepy.video.fx.all import crop

from . import DATA_DIR

TARGET_W, TARGET_H = 1080, 1920
TARGET_RATIO = 9 / 16


@lru_cache(maxsize=1)
def _cv2():
    """Importa OpenCV solo quando serve (face-tracking). E' una dipendenza opzionale."""
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "Il face-tracking richiede OpenCV, che non e' installato.\n"
            "Installa con:  pip install opencv-python"
        ) from exc
    return cv2


@lru_cache(maxsize=1)
def _face_cascade():
    """Carica (una sola volta) il classificatore Haar per i volti."""
    cv2 = _cv2()
    cascade_path = DATA_DIR / "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        raise RuntimeError(f"Impossibile caricare il classificatore Haar: {cascade_path}")
    return cascade


def _detect_faces(frame):
    """Rileva i volti in un frame RGB di MoviePy. Restituisce una lista di (x, y, w, h)."""
    cv2 = _cv2()
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return _face_cascade().detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)


def crop_center(clip: VideoClip) -> VideoClip:
    """Crop centrale 9:16 (veloce, nessuna analisi)."""
    target_width = int(clip.h * TARGET_RATIO)
    cropped = crop(clip, width=target_width, height=clip.h, x_center=clip.w / 2)
    return cropped.resize((TARGET_W, TARGET_H))


# Intervallo (in secondi) tra i frame campionati per il rilevamento volti.
# Campionare invece di scansionare ogni frame rende il face-tracking molto più
# veloce (ed evita il "blocco" su clip senza volti).
FACE_SAMPLE_STEP = 0.4


def _most_centered_face(clip: VideoClip, start_sec: float, end_sec: float):
    """Cerca un volto campionando i frame in [start_sec, end_sec) e ritorna il piu' centrato.

    Campiona pochi frame (FACE_SAMPLE_STEP) e si ferma al primo con volti: limita
    il lavoro al segmento corrente, niente scansione dell'intero clip.
    """
    most_centered = None
    t = max(0.0, start_sec)
    end = min(end_sec, clip.duration)
    while t < end:
        try:
            faces = _detect_faces(clip.get_frame(t))
        except Exception:
            faces = []
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                face_center_x = x + w / 2
                if most_centered is None or abs(face_center_x - clip.w / 2) < abs(most_centered[0] - clip.w / 2):
                    most_centered = (face_center_x, y + h / 2, w, h)
            break
        t += FACE_SAMPLE_STEP
    return most_centered


def crop_face_tracking(clip: VideoClip, segment_duration: float = 3.0) -> VideoClip:
    """Crop 9:16 che segue il volto piu' centrato (OpenCV). Piu' lento del crop centrale."""
    target_width = int(clip.h * TARGET_RATIO)
    min_dist = target_width // 2

    segments = []
    most_centered = None
    t = 0.0
    while t < clip.duration:
        end_time = min(t + segment_duration, clip.duration)
        subclip = clip.subclip(t, end_time)
        new_face = _most_centered_face(clip, start_sec=t, end_sec=end_time)

        if most_centered is None:
            most_centered = new_face
        elif new_face is not None and abs(new_face[0] - most_centered[0]) >= min_dist:
            # Cambia inquadratura solo se il volto si e' spostato in modo significativo
            most_centered = new_face

        if most_centered is None:
            x_center = clip.w / 2
        else:
            x_center = most_centered[0] - most_centered[2] / 2
            x_center = min(x_center, clip.w - target_width / 2)
            x_center = max(x_center, target_width / 2)

        cropped = crop(subclip, width=target_width, height=clip.h, x_center=x_center)
        segments.append(cropped.resize((TARGET_W, TARGET_H)))
        t += segment_duration

    return concatenate_videoclips(segments)


# Durata (s) di ogni blocco nelle modalita' VTUBER: si alterna centro/lato.
VTUBER_PERIOD = 5.0


def crop_vtuber(clip: VideoClip, side: str = "right", period: float = VTUBER_PERIOD) -> VideoClip:
    """Crop 9:16 che alterna ogni `period` secondi tra il CENTRO e un LATO.

    Pensato per i vtuber: l'avatar sta in un angolo (dx o sx), quindi si mostra
    un blocco di gameplay centrale e un blocco sull'avatar, a turno. Non usa
    OpenCV: e' solo un ritaglio che cambia posizione, quindi veloce.
    """
    target_width = int(clip.h * TARGET_RATIO)
    half = target_width / 2
    x_center = clip.w / 2
    x_side = half if side == "left" else clip.w - half
    x_side = max(half, min(clip.w - half, x_side))   # resta dentro l'inquadratura

    segments = []
    t, i = 0.0, 0
    while t < clip.duration:
        end_time = min(t + period, clip.duration)
        subclip = clip.subclip(t, end_time)
        xc = x_center if (i % 2 == 0) else x_side     # i pari = centro, dispari = lato
        cropped = crop(subclip, width=target_width, height=clip.h, x_center=xc)
        segments.append(cropped.resize((TARGET_W, TARGET_H)))
        t += period
        i += 1

    return concatenate_videoclips(segments)


# --------------------------------------------------------------------------- #
# Modalita' LONGPLAY: pan singolo che segue chi parla (volto + audio) nelle
# cutscene e l'azione (movimento) nel gameplay. Detector YuNet (fallback Haar).
# --------------------------------------------------------------------------- #
YUNET_MODEL = DATA_DIR / "face_detection_yunet_2023mar.onnx"
LONGPLAY_STEP = 0.4       # secondi tra un campionamento e l'altro
DETECT_WIDTH = 360        # i frame vengono ridotti a questa larghezza per la detezione
AUDIO_ACTIVE = 0.35       # soglia (0..1) sopra cui consideriamo "si sta parlando"


@lru_cache(maxsize=1)
def _yunet():
    """FaceDetectorYN (YuNet) se il modello c'e', altrimenti None (fallback Haar)."""
    if not YUNET_MODEL.exists():
        return None
    try:
        cv2 = _cv2()
        return cv2.FaceDetectorYN.create(str(YUNET_MODEL), "", (320, 320), 0.6, 0.3, 5000)
    except Exception:
        return None


def _detect_small(small_rgb):
    """Volti su un frame RGB ridotto. Ritorna [(cx, cy, w, h, score)] in coord. del frame ridotto."""
    cv2 = _cv2()
    bgr = cv2.cvtColor(small_rgb, cv2.COLOR_RGB2BGR)
    out = []
    det = _yunet()
    if det is not None:
        h, w = bgr.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(bgr)
        if faces is not None:
            for f in faces:
                out.append((float(f[0] + f[2] / 2), float(f[1] + f[3] / 2),
                            float(f[2]), float(f[3]), float(f[-1])))
        return out
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    for (x, y, w, h) in _face_cascade().detectMultiScale(gray, 1.2, 5):
        out.append((x + w / 2, y + h / 2, float(w), float(h), 1.0))
    return out


def _audio_envelope(clip, step):
    """Inviluppo RMS (0..1) dell'audio per finestre di `step` secondi. None se assente."""
    import wave
    from . import TEMP_DIR, ensure_dirs
    if clip.audio is None:
        return None
    ensure_dirs()
    wav = str(TEMP_DIR / "longplay_audio.wav")
    try:
        clip.audio.write_audiofile(wav, fps=22050, nbytes=2, logger=None)
        with wave.open(wav, "rb") as wf:
            ch, fr = wf.getnchannels(), wf.getframerate()
            a = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32)
        if ch > 1:
            a = a.reshape(-1, ch).mean(axis=1)
        win = max(1, int(step * fr))
        n = max(1, len(a) // win)
        rms = np.array([np.sqrt(np.mean(a[i * win:(i + 1) * win] ** 2)) for i in range(n)])
        peak = rms.max()
        return rms / peak if peak > 0 else rms
    except Exception:
        return None


def _motion_center_x(prev_gray, gray, inv):
    """Colonna (in coord. piene) col baricentro del movimento tra due frame, o None."""
    if prev_gray is None:
        return None
    mask = np.abs(gray.astype(np.int16) - prev_gray.astype(np.int16)) > 18
    colsum = mask.sum(axis=0).astype(np.float32)
    total = colsum.sum()
    if total < mask.size * 0.004:        # quasi fermo: niente target dal movimento
        return None
    cx_small = float((np.arange(len(colsum)) * colsum).sum() / total)
    return cx_small * inv


def _ema(arr, alpha=0.25):
    """Media mobile esponenziale: rende il pan dolce."""
    out = np.array(arr, dtype=np.float32)
    for i in range(1, len(out)):
        out[i] = alpha * out[i] + (1 - alpha) * out[i - 1]
    return out


def crop_longplay(clip: VideoClip, step: float = LONGPLAY_STEP) -> VideoClip:
    """Pan 9:16 per longplay: inquadra chi parla (volto + audio) o l'azione (movimento)."""
    cv2 = _cv2()
    w, h = clip.w, clip.h
    target_width = int(h * TARGET_RATIO)
    half = target_width / 2.0
    dur = clip.duration

    env = _audio_envelope(clip, step)

    def talking(t):
        if env is None:
            return True                  # senza audio: aggancia comunque i volti prominenti
        return env[min(len(env) - 1, int(t / step))] > AUDIO_ACTIVE

    times = np.arange(0.0, max(step, dur), step)
    targets, cur, prev_gray = [], w / 2.0, None
    for t in times:
        try:
            frame = clip.get_frame(min(float(t), dur - 1e-3))
        except Exception:
            targets.append(cur)
            continue
        small = cv2.resize(frame, (DETECT_WIDTH, max(1, int(h * DETECT_WIDTH / w)))) \
            if w > DETECT_WIDTH else frame
        inv = w / small.shape[1]
        gray = cv2.cvtColor(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2GRAY)

        target = None
        faces = [f for f in _detect_small(small) if f[2] >= 0.06 * small.shape[1]]
        if faces and talking(float(t)):
            dom = max(faces, key=lambda f: f[2] * f[3] * max(0.1, f[4]))  # area x confidenza
            target = dom[0] * inv
        if target is None:
            target = _motion_center_x(prev_gray, gray, inv)
        if target is None:
            target = cur
        cur = target
        targets.append(target)
        prev_gray = gray

    smooth = np.clip(_ema(targets), half, max(half, w - half))

    def make_frame(t):
        f = clip.get_frame(t)
        xc = float(np.interp(t, times, smooth))
        x0 = int(round(min(max(xc - half, 0), max(0, w - target_width))))
        return np.ascontiguousarray(f[:, x0:x0 + target_width])

    panned = VideoClip(make_frame, duration=dur)
    panned.fps = clip.fps or 24
    if clip.audio is not None:
        panned = panned.set_audio(clip.audio)
    return panned.resize((TARGET_W, TARGET_H))


def crop_to_vertical(clip: VideoClip, tracking_enabled: bool, mode: str = "opencv") -> VideoClip:
    """Dispatch del crop verticale.

    - tracking disattivato -> crop centrale veloce.
    - "opencv"      -> face-tracking (segue il volto).
    - "vtuber_right"-> alterna centro/destra ogni 5s.
    - "vtuber_left" -> alterna centro/sinistra ogni 5s.
    """
    if not tracking_enabled:
        return crop_center(clip)
    if mode == "vtuber_right":
        return crop_vtuber(clip, "right")
    if mode == "vtuber_left":
        return crop_vtuber(clip, "left")
    if mode == "longplay":
        return crop_longplay(clip)
    return crop_face_tracking(clip)
