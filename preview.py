#!/usr/bin/env python3
"""Open preview.html to see both themes before you push anything."""
from __future__ import annotations

import pathlib
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent
ORDER = ["portrait", "hero", "h-about", "h-stack", "stack",
         "h-projects", "h-stats", "stats", "heatmap", "h-colophon"]


def column(theme: str) -> str:
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    imgs = []
    for n in ORDER:
        f = ROOT / "out" / f"{n}-{theme}.svg"
        if not f.exists():
            continue
        w = " width=460" if n == "portrait" else ""
        imgs.append(f'<div style="margin:16px 0;text-align:center"><img src="out/{f.name}"{w}></div>')
    return (f'<div style="background:{bg};padding:26px 30px;flex:1">'
            f'<div style="max-width:880px;margin:0 auto">{"".join(imgs)}</div></div>')


def main() -> None:
    html = ("<!doctype html><meta charset=utf-8><title>profile preview</title>"
            "<body style='margin:0;display:flex;align-items:flex-start'>"
            f"{column('light')}{column('dark')}</body>")
    out = ROOT / "preview.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {out}")
    webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
