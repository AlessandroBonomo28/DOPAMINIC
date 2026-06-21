"""Pipeline long video -> shorts.

Un'unica funzione che, dato un video lungo, rileva gli highlight, taglia le
clip, le porta in verticale 9:16 (crop centrale o face-tracking), aggiunge
watermark e sottotitoli opzionali, ed esporta gli short pronti.
"""
import uuid
from pathlib import Path
from typing import Callable, List, Optional

from moviepy.editor import CompositeVideoClip, ImageClip, VideoFileClip

from . import FONTS_DIR, OUTPUT_DIR, ensure_dirs
from .cropping import crop_to_vertical
from .highlights import extract_loudest_segments, select_non_overlapping
from .textrender import render_text

ProgressCb = Callable[[str], None]

# PT Sans Bold: grassetto e con copertura completa degli accenti (it/es/fr...).
# (The Bold Font era incompleto: mancavano è, à, ò... -> accenti vuoti.)
SUBTITLE_FONT = str(FONTS_DIR / "ptsans.ttf")
WATERMARK_FONT = str(FONTS_DIR / "ptsans.ttf")

# Offset negativo: la clip parte qualche secondo prima del picco di volume
NEGATIVE_OFFSET = 2.0
SEGMENT_DURATION = 3.0  # finestra di analisi per gli highlight


def _log(cb: Optional[ProgressCb], message: str) -> None:
    print(message)
    if cb is not None:
        cb(message)


def _build_watermark(text: str, height: int, duration: float) -> ImageClip:
    arr = render_text(text or "@default", WATERMARK_FONT, 40, fill="#FFFFFF", fill_alpha=0x60)
    return (
        ImageClip(arr, transparent=True)
        .set_duration(duration)
        .set_position(("center", height * 0.75))
    )


# Stile sottotitoli: testo con contorno nero (Pillow disegna un outline pulito).
SUBTITLE_FONTSIZE = 80
SUBTITLE_STROKE = 6  # spessore del contorno nero


def _subtitle_generator(color: str, font_path: str = SUBTITLE_FONT,
                        fontsize: int = SUBTITLE_FONTSIZE, stroke: int = SUBTITLE_STROKE):
    def generator(txt: str) -> ImageClip:
        arr = render_text(
            txt, font_path, fontsize,
            fill=color, stroke_color="#000000", stroke_width=stroke,
        )
        return ImageClip(arr, transparent=True)

    return generator


def detect_clips(
    video_path: str,
    n_clips: int,
    clip_duration: int,
    settings: dict,
    progress_cb: Optional[ProgressCb] = None,
    bar_cb: Optional[ProgressCb] = None,
) -> dict:
    """Rileva gli intervalli da tagliare, SENZA generare gli short.

    Permette di mostrare un'anteprima/editor prima di produrre i file.

    Returns:
        dict con:
          - "clips": lista di (start, end) in secondi (ordine cronologico);
          - "transcript": trascrizione completa (talk, o cache riusabile) o None;
          - "duration": durata del video in secondi.
    """
    ensure_dirs()

    subtitles_enabled = settings.get("subtitles_enabled", False)

    # Durata del video (apri e chiudi subito).
    probe = VideoFileClip(video_path)
    length_seconds = probe.duration
    probe.close()

    # Auto-adatta i parametri se il video e' troppo corto
    if length_seconds * 0.75 < n_clips * clip_duration:
        clip_duration = min(clip_duration, 6)
        n_clips = int((length_seconds * 0.75) // clip_duration)
        if n_clips < 1:
            _log(progress_cb, "[!] Video troppo corto per estrarre clip.")
            return {"clips": [], "transcript": None, "duration": length_seconds}
        _log(progress_cb, f"[!] Video corto: adatto a {n_clips} clip da {clip_duration}s.")

    highlight_mode = settings.get("highlight_mode", "loudness")
    model = settings.get("whisper_model", "base")
    language = settings.get("whisper_language", "it")
    device = settings.get("whisper_device", "cpu")

    transcript = None

    if highlight_mode == "talk":
        from .transcript import get_full_transcript, find_monologue_clips

        _log(progress_cb, "[+] Modalita' 'by talk': cerco i monologhi piu' lunghi.")
        transcript = get_full_transcript(
            video_path, model, language, device,
            bar_cb=bar_cb, log_cb=lambda m: _log(progress_cb, m),
        )
        clips = find_monologue_clips(transcript, clip_duration, n_clips, length_seconds)
        if not clips:
            _log(progress_cb, "[!] Nessun parlato rilevato nel video.")
        elif len(clips) < n_clips:
            _log(progress_cb, f"[!] Trovati solo {len(clips)} monologhi distinti (richiesti "
                              f"{n_clips}): uso quelli disponibili.")
    else:
        _log(progress_cb, "[+] Analisi audio: ricerca dei momenti piu' rumorosi...")
        loudest = extract_loudest_segments(
            video_path, segment_duration=SEGMENT_DURATION, top_n=n_clips * 4
        )
        starts = select_non_overlapping(loudest, n=n_clips, min_gap=clip_duration)
        if not starts:
            _log(progress_cb, "[!] Nessun highlight rilevato.")
            return {"clips": [], "transcript": None, "duration": length_seconds}
        if len(starts) < n_clips:
            _log(progress_cb, f"[!] Trovati solo {len(starts)} momenti distinti (richiesti "
                              f"{n_clips}): uso quelli disponibili.")
        # Intervalli in ordine CRONOLOGICO (gli highlight arrivano per rumorosita').
        clips = []
        for peak in starts:
            start_time = max(0.0, peak - NEGATIVE_OFFSET)
            end_time = min(start_time + clip_duration, length_seconds)
            clips.append((start_time, end_time))
        clips.sort()
        # Riusa la trascrizione completa per i sottotitoli SOLO se gia' in cache.
        if subtitles_enabled:
            from .transcript import load_cached
            transcript = load_cached(video_path, model, language)
            if transcript is not None:
                _log(progress_cb, "[+] Trascrizione completa in cache: la riuso per i sottotitoli.")

    return {"clips": clips, "transcript": transcript, "duration": length_seconds}


def render_clips(
    video_path: str,
    clips: List,
    settings: dict,
    transcript: Optional[dict] = None,
    progress_cb: Optional[ProgressCb] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> List[str]:
    """Genera gli short dagli intervalli `clips` (eventualmente ritoccati nell'editor)."""
    ensure_dirs()
    if not clips:
        return []

    use_face_tracking = settings.get("opencv_face_tracking", False)
    subtitles_enabled = settings.get("subtitles_enabled", False)
    subtitles_color = settings.get("subtitles_color", "#FFFFFF")
    watermark_enabled = settings.get("watermark", True)
    watermark_text = settings.get("watermark_text", "@default")

    clips = sorted(clips)
    _log(progress_cb, f"[+] {len(clips)} clip da generare. Genero gli short...")

    # Transcriber per-clip: serve solo se i sottotitoli sono attivi e NON ho gia'
    # la trascrizione completa. Caricato UNA sola volta e riusato (ricaricarlo a
    # ogni clip causava blocchi, specie su GPU).
    transcriber = None
    if subtitles_enabled and transcript is None:
        from .subtitles import WhisperTranscriber
        transcriber = WhisperTranscriber(
            model_size=settings.get("whisper_model", "base"),
            language=settings.get("whisper_language", "it"),
            device=settings.get("whisper_device", "cpu"),
        )

    outputs: List[str] = []
    for i, (start_time, end_time) in enumerate(clips, start=1):
        if should_cancel and should_cancel():
            _log(progress_cb, "[!] Generazione interrotta dall'utente.")
            break
        _log(progress_cb, f"[+] Short {i}/{len(clips)}: {start_time:.0f}s -> {end_time:.0f}s")
        subs = None
        if subtitles_enabled and transcript is not None:
            from .transcript import slice_subtitles
            subs = slice_subtitles(transcript, start_time, end_time)
        out_path = _render_short(
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
            index=i,
            use_face_tracking=use_face_tracking,
            subtitles_color=subtitles_color,
            watermark_enabled=watermark_enabled,
            watermark_text=watermark_text,
            transcriber=transcriber,
            subs=subs,
            settings=settings,
            progress_cb=progress_cb,
        )
        outputs.append(out_path)
        _log(progress_cb, f"[+] Salvato: {out_path}")

    _log(progress_cb, f"[OK] Generati {len(outputs)} short in {OUTPUT_DIR}")
    return outputs


def generate_shorts(
    video_path: str,
    n_clips: int,
    clip_duration: int,
    settings: dict,
    progress_cb: Optional[ProgressCb] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
    bar_cb: Optional[ProgressCb] = None,
) -> List[str]:
    """Rileva gli highlight e genera subito gli short (rilevamento + generazione)."""
    det = detect_clips(video_path, n_clips, clip_duration, settings, progress_cb, bar_cb)
    return render_clips(
        video_path, det["clips"], settings, det["transcript"], progress_cb, should_cancel
    )


def _render_short(
    video_path: str,
    start_time: float,
    end_time: float,
    index: int,
    use_face_tracking: bool,
    subtitles_color: str,
    watermark_enabled: bool,
    watermark_text: str,
    transcriber,
    subs,
    settings: dict,
    progress_cb: Optional[ProgressCb],
) -> str:
    """Crea un singolo short verticale e lo scrive su disco.

    Apre un VideoFileClip dedicato per ogni short (reader isolato): evita i
    blocchi/seek lenti dovuti al riuso/chiusura del reader condiviso tra clip.
    """
    src = VideoFileClip(video_path)
    result = None
    try:
        subclip = src.subclip(start_time, end_time)

        mode = "face-tracking (OpenCV)" if use_face_tracking else "crop centrale"
        _log(progress_cb, f"    - crop verticale: {mode}")
        vertical = crop_to_vertical(subclip, use_face_tracking)

        layers = [vertical]

        # Sottotitoli: o gia' pronti (affettati dalla trascrizione completa), o
        # trascritti al volo per questa clip con Whisper.
        sub_list = None
        if subs is not None:
            _log(progress_cb, "    - sottotitoli: dalla trascrizione completa")
            sub_list = subs
        elif transcriber is not None:
            _log(progress_cb, "    - sottotitoli: trascrizione con Whisper locale...")
            from . import TEMP_DIR

            audio_tmp = str(TEMP_DIR / f"audio_{index}.wav")
            subclip.audio.write_audiofile(audio_tmp, logger=None)
            sub_list = transcriber.transcribe(audio_tmp)

        if sub_list:
            from moviepy.video.tools.subtitles import SubtitlesClip

            # Whisper su audio corto puo' allucinare timestamp oltre la fine clip:
            # vincoliamo i sottotitoli alla durata reale della clip.
            dur = vertical.duration
            sub_list = [((s, min(e, dur)), t) for (s, e), t in sub_list if s < dur]
            if sub_list:
                font_path = str(FONTS_DIR / settings.get("subtitle_font", "ptsans.ttf"))
                gen = _subtitle_generator(
                    subtitles_color, font_path,
                    int(settings.get("subtitle_fontsize", SUBTITLE_FONTSIZE)),
                    int(settings.get("subtitle_stroke", SUBTITLE_STROKE)),
                )
                # Passiamo la lista (non il file) per evitare il bug UTF-8 di moviepy
                subtitles = SubtitlesClip(sub_list, gen)
                layers.append(subtitles.set_pos(("center", vertical.h * 0.6)))

        if watermark_enabled:
            _log(progress_cb, "    - watermark")
            layers.append(_build_watermark(watermark_text, vertical.h, vertical.duration))

        result = CompositeVideoClip(layers) if len(layers) > 1 else vertical
        # La durata dello short e' quella della clip (i layer non devono allungarla)
        result = result.set_duration(vertical.duration)
        # Taglia 0.1s dal fondo per evitare desync audio
        result = result.subclip(0, max(0.1, result.duration - 0.1))

        out_path = str(OUTPUT_DIR / f"short_{index}_{uuid.uuid4().hex[:8]}.mp4")
        result.write_videofile(
            out_path,
            codec="libx264",
            audio_codec="aac",
            threads=settings.get("threads", 4),
            logger=None,
        )
        return out_path
    finally:
        if result is not None:
            try:
                result.close()
            except Exception:
                pass
        src.close()
