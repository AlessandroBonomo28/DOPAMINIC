"""Rendering del testo con Pillow (niente ImageMagick).

Produce array RGBA che MoviePy puo' usare come ImageClip trasparente, per
watermark e sottotitoli. Sostituisce i TextClip (che richiedevano ImageMagick),
rendendo l'app autocontenuta e facilmente impacchettabile.
"""
from functools import lru_cache
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=8)
def _font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, size)


def _hex_to_rgba(color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Converte '#RRGGBB' o '#RRGGBBAA' in (r, g, b, a)."""
    c = color.lstrip("#")
    if len(c) == 8:  # include alpha
        r, g, b, a = (int(c[i:i + 2], 16) for i in (0, 2, 4, 6))
        return (r, g, b, a)
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def render_text(
    text: str,
    font_path: str,
    fontsize: int,
    fill: str,
    stroke_color: str = "#000000",
    stroke_width: int = 0,
    fill_alpha: int = 255,
    padding: int = 12,
) -> np.ndarray:
    """Rende il testo come array RGBA (H, W, 4) con sfondo trasparente.

    Args:
        text: testo da disegnare.
        font_path: percorso al file .ttf.
        fontsize: dimensione del font in px.
        fill: colore del testo ('#RRGGBB' o '#RRGGBBAA').
        stroke_color: colore del contorno.
        stroke_width: spessore del contorno in px (0 = nessuno).
        fill_alpha: opacita' del testo (0-255), usata se `fill` non ha alpha.
        padding: margine trasparente attorno al testo.
    """
    font = _font(font_path, fontsize)

    # Misura il testo (incluso il contorno)
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = measure.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w = bbox[2] - bbox[0] + 2 * padding
    h = bbox[3] - bbox[1] + 2 * padding

    img = Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text(
        (padding - bbox[0], padding - bbox[1]),
        text,
        font=font,
        fill=_hex_to_rgba(fill, fill_alpha),
        stroke_width=stroke_width,
        stroke_fill=_hex_to_rgba(stroke_color),
    )
    return np.array(img)
