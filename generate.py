#!/usr/bin/env python3
"""Regenerate every graphic and rewrite README.md.

    python generate.py            # live data, needs GITHUB_TOKEN
    python generate.py --demo     # sample data, no token needed
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from build import github, graphics, portrait, readme
from build.config import ROOT, load
from build.headings import heading
from build.svgkit import THEMES, digest

OUT = ROOT / "out"

HEADINGS = {
    "h-about": "about",
    "h-stack": "stack",
    "h-projects": "projects",
    "h-stats": "stats",
    "h-colophon": "about this page",
}


def write(name: str, content: str, ver: dict[str, str], changed: list[str]) -> None:
    path = OUT / f"{name}.svg"
    ver[name] = digest(content)
    if path.exists() and path.read_text() == content:
        return
    path.write_text(content)
    changed.append(path.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="build with sample data")
    ap.add_argument("--token", default=None)
    args = ap.parse_args()

    cfg = load()
    OUT.mkdir(exist_ok=True)

    s = github.demo(cfg.username) if args.demo else github.fetch(
        cfg.username, token=args.token, exclude=cfg.exclude_langs)
    if not cfg.name:
        cfg.name = s.name

    ver: dict[str, str] = {}
    changed: list[str] = []

    if cfg.photo_path.exists():
        lum = portrait.sample(cfg.photo_path, cfg.portrait_cols,
                              gamma=cfg.portrait_gamma, vignette=cfg.portrait_vignette,
                              local=cfg.portrait_local)
    else:
        print(f"! no photo at {cfg.photo_path} -- skipping the portrait", file=sys.stderr)
        lum = None

    for theme in THEMES:
        t = theme.name
        if lum is not None:
            write(f"portrait-{t}",
                  portrait.render(lum, theme, width=cfg.portrait_width, ramp=cfg.portrait_ramp,
                                  polarity=cfg.portrait_polarity, weight=cfg.portrait_weight,
                                  alt=cfg.name or cfg.username),
                  ver, changed)
        write(f"hero-{t}", graphics.hero(s, theme), ver, changed)
        write(f"stats-{t}", graphics.stats_panel(s, theme), ver, changed)
        write(f"heatmap-{t}", graphics.heatmap(s, theme), ver, changed)
        if cfg.stack:
            write(f"stack-{t}", graphics.stack_row(cfg.stack, theme), ver, changed)
        for key, label in HEADINGS.items():
            write(f"{key}-{t}", heading(label, theme), ver, changed)

    md = readme.build(cfg, s, ver)
    rp = ROOT / "README.md"
    if not rp.exists() or rp.read_text() != md:
        rp.write_text(md)
        changed.append("README.md")

    print(f"{s.total} contributions · {s.active_days}/{s.span} active days · "
          f"streak {s.current_streak} (best {s.longest_streak})")
    print(f"{len(changed)} file(s) changed" + (": " + ", ".join(changed[:8]) if changed else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
