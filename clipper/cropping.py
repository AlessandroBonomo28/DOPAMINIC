"""Crop verticale 9:16 dei clip.

Due modalita':
  - crop centrale (veloce): ritaglia il centro dell'inquadratura.
  - face-tracking (OpenCV, lento): segue il volto piu' centrato spostando
    il ritaglio segmento per segmento.
"""
from functools import lru_cache

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


def crop_to_vertical(clip: VideoClip, use_face_tracking: bool) -> VideoClip:
    """Dispatch: face-tracking se richiesto, altrimenti crop centrale veloce."""
    if use_face_tracking:
        return crop_face_tracking(clip)
    return crop_center(clip)
