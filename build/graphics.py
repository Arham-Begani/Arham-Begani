"""The generated graphics: hero stat block, stats panel, ASCII year heatmap."""
from __future__ import annotations

import datetime as dt
import math

from .github import Stats
from .svgkit import Theme, grid_text, hold, svg, text_path, text_width

WIDTH = 880


# --------------------------------------------------------------- small pieces

def _label(s: str, x: float, y: float, theme: Theme, *, size: float = 9.5,
           weight: str = "Medium", fill: str | None = None, tracking: float = 1.6,
           anchor: str = "start") -> str:
    if anchor == "end":
        x -= text_width(s, size, weight, tracking) - tracking
    return text_path(s, size=size, x=x, y=y, weight=weight,
                     fill=fill or theme.muted, tracking=tracking)


def _fade_in(body: str, delay: float, dur: float = 0.5, dy: float = 6.0) -> str:
    """Rise-and-fade, written so the resting state is the *finished* state.

    No static transform: unanimated, the group sits where it belongs. The jump
    back to +{dy} happens at `delay`, the same instant opacity is still 0, so
    the reset is never visible.
    """
    return (
        f'<g opacity="1">'
        f'{hold("opacity", "0")}'
        f'<animate attributeName="opacity" values="0;1" begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="0 {dy};0 0" begin="{delay:.2f}s" dur="{dur}s" '
        f'calcMode="spline" keySplines="0.16 1 0.3 1" fill="freeze"/>'
        f"{body}</g>"
    )


def count_up(value: int, *, x: float, y: float, size: float, theme: Theme,
             steps: int = 14, dur: float = 1.1, weight: str = "ExtraBold") -> str:
    """A ticking number.

    SMIL cannot animate text content, so each frame is its own outlined path
    and <set> hands visibility along the chain.
    """
    if value <= 0:
        return text_path("0", size=size, x=x, y=y, weight=weight, fill=theme.glow)
    frames: list[int] = []
    for i in range(steps):
        t = (i + 1) / steps
        eased = 1 - (1 - t) ** 3
        frames.append(max(0, int(round(value * eased))))
    frames[-1] = value

    # Collapse runs of the same number into one frame held across its slots.
    # The ease flattens hard near the end, so the tail repeats a lot, and every
    # repeat would otherwise cost a full set of outlines.
    per = dur / steps
    runs: list[tuple[int, int, int]] = []              # value, first slot, last+1
    for i, v in enumerate(frames):
        if runs and runs[-1][0] == v:
            runs[-1] = (v, runs[-1][1], i + 1)
        else:
            runs.append((v, i, i + 1))

    final = text_path(f"{value:,}", size=size, x=x, y=y, weight=weight, fill=theme.glow)
    if len(runs) == 1:
        return final

    out = []
    for k, (v, start, stop) in enumerate(runs):
        last = k == len(runs) - 1
        if last:
            # Statically visible, so a still render shows the real number
            # rather than the first frame of a count that never ran.
            out.append(f'<g opacity="1">{hold("opacity", "0")}'
                       f'<set attributeName="opacity" to="1" begin="{start * per:.3f}s"/>'
                       f'{final}</g>')
        else:
            out.append(
                f'<g opacity="0">'
                f'<set attributeName="opacity" to="1" begin="{start * per:.3f}s"/>'
                f'<set attributeName="opacity" to="0" begin="{stop * per:.3f}s"/>'
                f'{text_path(f"{v:,}", size=size, x=x, y=y, weight=weight, fill=theme.glow)}</g>'
            )
    return "".join(out)


def sparkline(values: list[int], *, x: float, y: float, w: float, h: float,
              theme: Theme, delay: float = 0.35, dur: float = 1.6) -> str:
    if not values:
        return ""
    hi = max(values) or 1
    n = len(values)
    pts = [(x + i * (w / max(1, n - 1)), y + h - (v / hi) * h) for i, v in enumerate(values)]

    # Catmull-Rom -> cubic bezier, so the line reads as a trace not a zigzag.
    d = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(n - 1):
        p0 = pts[max(0, i - 1)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(n - 1, i + 2)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    path = "".join(d)
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(n - 1)) * 1.08

    peak = max(range(n), key=lambda i: values[i])
    px, py = pts[peak]
    return (
        f'<path d="{path}" fill="none" stroke="{theme.ink}" stroke-width="1.3" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85" '
        f'stroke-dasharray="{length:.0f}" stroke-dashoffset="0">'
        f'{hold("stroke-dashoffset", f"{length:.0f}")}'
        f'<animate attributeName="stroke-dashoffset" values="{length:.0f};0" '
        f'begin="{delay}s" dur="{dur}s" calcMode="spline" keySplines="0.3 0.8 0.3 1" fill="freeze"/>'
        f"</path>"
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.4" fill="{theme.accent}" opacity="1">'
        f'{hold("opacity", "0")}'
        f'<animate attributeName="opacity" values="0;1" begin="{delay + dur * 0.85:.2f}s" '
        f'dur="0.4s" fill="freeze"/></circle>'
    )


# ------------------------------------------------------------------- sections

def hero(s: Stats, theme: Theme, *, width: int = WIDTH) -> str:
    h = 132.0
    body = [
        _fade_in(count_up(s.total, x=0, y=64, size=62, theme=theme), 0.05),
        _fade_in(_label("CONTRIBUTIONS IN THE LAST YEAR", 3, 84, theme), 0.35),
        _fade_in(sparkline(s.weekly, x=0, y=96, w=width, h=30, theme=theme), 0.0),
    ]
    col = width
    for value, caption in ((s.best_week, "BEST WEEK"), (s.active_days, "ACTIVE DAYS")):
        block = (
            text_path(f"{value:,}", size=22, x=col - text_width(f"{value:,}", 22, "Bold"),
                      y=22, weight="Bold", fill=theme.ink)
            + _label(caption, col, 36, theme, size=8.5, anchor="end")
        )
        body.append(_fade_in(block, 0.5))
        col -= 118
    return svg(width, h, "".join(body), title=f"{s.total} contributions in the last year")


def _bars(title: str, data: dict[str, int], theme: Theme, *, x: float, y: float,
          w: float, fmt, delay: float, rows: int = 5) -> tuple[str, float]:
    items = sorted(data.items(), key=lambda kv: -kv[1])[:rows]
    total = sum(data.values()) or 1
    out = [_label(title, x, y, theme, size=8.5, fill=theme.dim)]
    top = items[0][1] if items else 1
    label_w, bar_w = 92.0, w - 92 - 52
    for i, (name, v) in enumerate(items):
        ry = y + 20 + i * 19
        frac = v / top
        out.append(text_path(name[:12].lower(), size=11, x=x, y=ry + 4, weight="Medium", fill=theme.ink))
        out.append(f'<rect x="{x + label_w:.1f}" y="{ry - 4:.1f}" width="{bar_w:.1f}" height="7" '
                   f'rx="1" fill="{theme.dim}" opacity="0.5"/>')
        out.append(
            f'<rect x="{x + label_w:.1f}" y="{ry - 4:.1f}" width="{bar_w * frac:.1f}" '
            f'height="7" rx="1" fill="{theme.ink}">'
            f'{hold("width", "0")}'
            f'<animate attributeName="width" values="0;{bar_w * frac:.1f}" '
            f'begin="{delay + i * 0.08:.2f}s" dur="0.9s" calcMode="spline" '
            f'keySplines="0.16 1 0.3 1" fill="freeze"/></rect>'
        )
        out.append(_label(fmt(v, total), x + w, ry + 3, theme, size=9, tracking=0.6, anchor="end"))
    return "".join(out), y + 20 + max(1, len(items)) * 19


def stats_panel(s: Stats, theme: Theme, *, width: int = WIDTH) -> str:
    body = []
    x = 0.0
    figures = [
        (s.current_streak, "DAY STREAK"),
        (s.longest_streak, "LONGEST"),
        (s.repos, "REPOS"),
        (s.stars, "STARS EARNED"),
    ]
    for i, (v, cap) in enumerate(figures):
        block = (text_path(f"{v:,}", size=30, x=x, y=30, weight="Bold", fill=theme.ink)
                 + _label(cap, x + 1, 45, theme, size=8.5))
        body.append(_fade_in(block, 0.1 + i * 0.07))
        x += 152

    colw = (width - 60) / 2
    left, ly = _bars("BY BYTES", s.bytes_by_lang, theme, x=0, y=86, w=colw,
                     fmt=lambda v, t: f"{v / t * 100:.0f}%", delay=0.5)
    right, ry = _bars("BY REPOS", s.repos_by_lang, theme, x=colw + 60, y=86, w=colw,
                      fmt=lambda v, t: str(v), delay=0.6)
    body.append(left)
    body.append(right)
    return svg(width, max(ly, ry) + 8, "".join(body), title="language and repository stats")


LEVELS = (0.30, 0.52, 0.76, 1.0)   # ink opacity per busyness step


def heatmap(s: Stats, theme: Theme, *, width: int = WIDTH) -> str:
    """The contribution year.

    Drawn as rects rather than block characters: the viewer's machine supplies
    the font for a <text> element, and U+2588 and friends are not on every
    system. A rect is the same mark with none of the risk.
    """
    days = s.days
    lead = (days[0].date.weekday() + 1) % 7          # pad to a Sunday start
    cells: list[int | None] = [None] * lead + [d.count for d in days]
    while len(cells) % 7:
        cells.append(None)
    weeks = len(cells) // 7

    hi = max((c for c in cells if c), default=1)
    grid_x, top = 34.0, 46.0
    pitch = (width - grid_x) / weeks
    box = pitch - 3.0
    row = box + 3.0

    body = [
        _label("THE YEAR", 0, 12, theme, size=8.5, fill=theme.dim),
        text_path(f"{s.active_days} of {s.span} days had a contribution",
                  size=11, x=0, y=29, weight="Medium", fill=theme.muted),
        f'<defs><clipPath id="hm">'
        f'<rect x="{grid_x - 2}" y="0" width="{weeks * pitch + 6:.1f}" height="999">'
        f'{hold("width", "0")}'
        f'<animate attributeName="width" values="0;{weeks * pitch + 6:.1f}" begin="0.2s" '
        f'dur="1.5s" calcMode="spline" keySplines="0.25 0.7 0.3 1" fill="freeze"/>'
        f'</rect></clipPath></defs>',
        '<g clip-path="url(#hm)">',
    ]

    # A year is ~365 cells but only five appearances: empty, plus one per
    # busyness step. Carrying fill and opacity on every rect repeats those five
    # strings 365 times, so bucket the cells and let the group carry them.
    buckets: dict[tuple[str, float], list[str]] = {}
    for w in range(weeks):
        for r in range(7):
            c = cells[w * 7 + r]
            if c is None:
                continue
            x, y = grid_x + w * pitch, top + r * row
            if c == 0:
                key = (theme.dim, 1.0)
            else:
                key = (theme.ink, LEVELS[min(3, int((c / hi) ** 0.5 * 3.999))])
            buckets.setdefault(key, []).append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{box:.1f}" height="{box:.1f}" rx="2"/>')
    for (fill, op), rects in sorted(buckets.items()):
        attrs = f'fill="{fill}"' + ("" if op == 1.0 else f' opacity="{op}"')
        body.append(f'<g {attrs}>{"".join(rects)}</g>')
    body.append("</g>")

    for i, name in ((1, "mon"), (3, "wed"), (5, "fri")):
        body.append(_label(name, 0, top + i * row + box * 0.75, theme, size=8, tracking=0.6))

    seen: set[int] = set()
    for w in range(weeks):
        idx = w * 7
        if idx < lead or idx - lead >= len(days):
            continue
        d = days[idx - lead].date
        if d.month in seen or d.day > 7:
            continue
        seen.add(d.month)
        body.append(_label(d.strftime("%b").lower(), grid_x + w * pitch,
                           top + 7 * row + 12, theme, size=8, tracking=0.6))

    lx = width - 92
    body.append(_label("less", lx - 28, 29, theme, size=8, tracking=0.4))
    body.append(f'<rect x="{lx:.1f}" y="21" width="9" height="9" rx="2" fill="{theme.dim}"/>')
    for i, op in enumerate(LEVELS):
        body.append(f'<rect x="{lx + (i + 1) * 12:.1f}" y="21" width="9" height="9" rx="2" '
                    f'fill="{theme.ink}" opacity="{op}"/>')
    body.append(_label("more", lx + 5 * 12 + 4, 29, theme, size=8, tracking=0.4))

    return svg(width, top + 7 * row + 22, "".join(body),
               title=f"{s.active_days} active days in the last year")


def stack_row(items: list[str], theme: Theme, *, width: int = WIDTH,
              size: float = 11.5, gap: float = 26.0) -> str:
    """The stack, set in the page's own typeface instead of GitHub's."""
    x, y, lines = 0.0, 14.0, 1
    body = []
    for i, item in enumerate(items):
        w = text_width(item, size, "Medium", 0.4)
        if x + w > width and x > 0:
            x, y, lines = 0.0, y + 22, lines + 1
        body.append(
            f'<g opacity="1">'
            f'{hold("opacity", "0")}'
            f'<animate attributeName="opacity" values="0;1" begin="{0.1 + i * 0.045:.2f}s" '
            f'dur="0.45s" fill="freeze"/>'
            f'{text_path(item, size=size, x=x, y=y, weight="Medium", fill=theme.ink, tracking=0.4)}'
            f"</g>"
        )
        x += w + gap
    return svg(width, lines * 22 + 4, "".join(body), title=", ".join(items))
