"""A photo, pushed through a character ramp, revealed by a SMIL dissolve.

The reveal is a mask, not a wipe. Its luminance is a vertical ramp plus one
noise value per character cell, and a steep threshold sweeps across it: a cell
appears the moment its own value is crossed. Because the noise scrambles the
order locally while the ramp still leans downward, the picture thickens into
existence head-first with no edge anywhere -- where a growing clip rect always
has one, however you ease it.

`scatter` sets how much of the threshold is noise rather than ramp, so 0 is a
soft top-down wipe, 1 is every cell appearing in pure random order, and the
default sits between. One <animate> drives the whole thing -- no script, which
matters because GitHub renders README images with scripting disabled.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .svgkit import Theme, grid_text, svg

# Ramps run sparse -> dense. Index 0 must be a space.
RAMPS = {
    # Measured, not guessed: each glyph's ink coverage was rasterised in a
    # monospace face and the ramp picked so the steps are perceptually even.
    "even": " `-,~_!r|ljJIkSA6D@M",
    "fine": " .,:;irsXA253hMHGS#9B&@",
    "classic": " .:-=+*#%@",
    "blocks": " ░▒▓█",
    "dots": " .·:•▪■█",
}

CELL_ASPECT = 0.6 / 1.08  # character advance / line height


def _prepare(path: Path, *, gamma: float, vignette: float, local: float = 1.2) -> Image.Image:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        flat = Image.new("RGBA", img.size, (255, 255, 255, 255))
        flat.alpha_composite(img)
        img = flat
    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=(1, 1))

    a = np.asarray(img, dtype=np.float32) / 255.0
    if local > 0:
        # Local contrast. A ramp only has ~20 tones, and in most portraits the
        # face and the background sit within a few tones of each other -- so
        # global levels flatten the subject into the backdrop. Subtracting a
        # wide blur re-separates them the way CLAHE would.
        radius = max(img.size) / 9.0
        blur = np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0
        a = np.clip(a + local * (a - blur), 0, 1)
        a = (a - a.min()) / max(1e-6, a.max() - a.min())

    img = Image.fromarray((a * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.15)
    a = np.asarray(img, dtype=np.float32) / 255.0
    if gamma != 1.0:
        a = np.clip(a, 0, 1) ** gamma
    if vignette > 0:
        h, w = a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        falloff = np.clip(1.0 - vignette * np.clip(r - 0.55, 0, None) / 0.45, 0, 1)
        a = a * falloff + (1 - falloff) * float(np.median(a[:, :3]))
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L")


def sample(path: Path, cols: int, *, gamma: float = 1.0, vignette: float = 0.0,
           local: float = 1.2) -> np.ndarray:
    """Return a rows x cols float array of luminance in 0..1."""
    img = _prepare(path, gamma=gamma, vignette=vignette, local=local)
    w, h = img.size
    rows = max(1, int(round(cols * (h / w) * CELL_ASPECT)))
    small = img.resize((cols, rows), Image.Resampling.LANCZOS)
    return np.asarray(small, dtype=np.float32) / 255.0


def to_rows(lum: np.ndarray, ramp: str, *, invert: bool, weight: float = 1.0) -> list[str]:
    """Map luminance onto the ramp.

    `invert` puts the dense glyphs where the picture is *dark*, so the ASCII
    follows the subject's own ink. `weight` above 1 pulls the mid-tones down,
    which stops a large black mass (a suit, a jacket) from flooding the frame.
    """
    v = 1.0 - lum if invert else lum
    lo, hi = float(v.min()), float(v.max())
    v = (v - lo) / (hi - lo) if hi > lo else v * 0
    if weight != 1.0:
        v = np.clip(v, 0, 1) ** weight
    idx = np.clip((v * (len(ramp) - 1) + 0.5).astype(int), 0, len(ramp) - 1)
    return ["".join(ramp[i] for i in row) for row in idx]


STEEP = 6.0     # threshold sharpness; a cell's own fade is 1/(1+STEEP) of the run
SEED = 11       # fixed, so an unchanged photo regenerates byte-for-byte

# Near-linear, with the deceleration saved for the end. The wipe's old curve
# (0.22 0.61 0.36 1) front-loads so hard that a dissolve driven by it is
# finished barely halfway through its own duration; this one spreads the
# reveal across the run and leaves a thin tail of stragglers.
EASE = "0.35 0.05 0.35 1"


def _dissolve(width: float, height: float, cell: float, line: float,
              *, scatter: float, grain: float, duration: float) -> tuple[str, str]:
    """The mask that does the reveal, as (defs, mask-id).

    Threshold per pixel is  v = ramp(y) + scatter * noise(x, y),  built to span
    exactly 0..1 so neither end is lost to the filter's own clamping. Mask
    luminance is then clamp(intercept - STEEP*v): sweeping intercept from 0 to
    1+STEEP takes it from all-black to all-white, and each cell crosses on its
    own schedule.

    The resting intercept is the *finished* one, so a viewer that never runs
    the animation gets the whole portrait rather than an empty frame.
    """
    a = min(1.0, max(0.0, scatter))
    end = 1.0 + STEEP
    # Ramp carries what the noise does not, so the two always sum to 1.
    foot = round(255 * (1.0 - a))
    # One noise feature per character cell: the grain is the drawing's own
    # resolution, not the device's, so it reads as cells appearing.
    fx = 1.0 / max(0.5, cell * grain)
    fy = 1.0 / max(0.5, line * grain)
    box = f'x="0" y="0" width="{width:.0f}" height="{height:.1f}"'
    anim = (f'<animate attributeName="intercept" values="0;{end:.1f}" dur="{duration}s" '
            f'calcMode="spline" keySplines="{EASE}" fill="freeze"/>')
    func = "".join(
        f'<feFunc{c} type="linear" slope="{-STEEP:.1f}" intercept="{end:.1f}">{anim}</feFunc{c}>'
        for c in "RGB")
    return (
        f'<defs>'
        f'<linearGradient id="pr" x1="0" y1="0" x2="0" y2="{height:.1f}" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#000"/>'
        f'<stop offset="1" stop-color="rgb({foot},{foot},{foot})"/>'
        f'</linearGradient>'
        f'<filter id="pf" filterUnits="userSpaceOnUse" {box} '
        f'color-interpolation-filters="sRGB">'
        f'<feTurbulence type="fractalNoise" baseFrequency="{fx:.4f} {fy:.4f}" '
        f'numOctaves="1" seed="{SEED}" result="n"/>'
        # Read the turbulence's ALPHA into every colour channel. Filter results
        # are premultiplied, so the colour channels come back scaled by that
        # noisy alpha; the alpha channel alone is a clean 0..1 noise value.
        f'<feColorMatrix in="n" type="matrix" result="g" '
        f'values="0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 0 1"/>'
        f'<feComposite in="SourceGraphic" in2="g" operator="arithmetic" '
        f'k1="0" k2="1" k3="{a:.3f}" k4="0" result="v"/>'
        f'<feComponentTransfer in="v">{func}</feComponentTransfer>'
        f'</filter>'
        f'<mask id="pm" maskUnits="userSpaceOnUse" {box}>'
        f'<rect {box} fill="url(#pr)" filter="url(#pf)"/>'
        f'</mask>'
        f'</defs>',
        "pm",
    )


def render(
    lum: np.ndarray,
    theme: Theme,
    *,
    width: int = 460,
    ramp: str = "even",
    polarity: str = "ink",
    weight: float = 1.0,
    duration: float = 2.2,
    scatter: float = 0.35,
    grain: float = 1.0,
    alt: str = "ASCII portrait",
) -> str:
    chars = RAMPS.get(ramp, ramp)
    rows_n, cols = lum.shape
    size = width / (cols * 0.6)
    cell = size * 0.6
    line = size * 1.08
    height = rows_n * line + size * 0.4
    baseline = size * 0.85

    # "ink"   -- dense where the picture is dark, in both themes: the ASCII
    #            follows the drawing's own ink. Right for artwork, line work,
    #            and anything shot against a light background.
    # "light" -- dense where the picture is bright: right for a lit subject
    #            against a dark background.
    # "theme" -- follow the page instead of the picture.
    invert = {"ink": True, "light": False}.get(polarity, theme.name == "light")
    rows = to_rows(lum, chars, invert=invert, weight=weight)

    defs, mask = _dissolve(width, height, cell, line,
                           scatter=scatter, grain=grain, duration=duration)
    body = [
        defs,
        f'<g mask="url(#{mask})">',
        grid_text(rows, x=0, y=baseline, size=size, line_height=line, cell=cell,
                  fill=theme.ink, opacity=0.92),
        "</g>",
    ]
    return svg(width, height, "".join(body), title=alt)
