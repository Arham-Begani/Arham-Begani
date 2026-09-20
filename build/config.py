"""Reads profile.toml -- the one file you actually edit."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Link:
    label: str
    url: str


@dataclass
class Project:
    name: str
    url: str = ""
    meta: str = ""
    blurb: str = ""


@dataclass
class Config:
    username: str
    name: str = ""
    photo: str = "assets/me.jpg"
    about: list[str] = field(default_factory=list)
    stack: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    portrait_cols: int = 108
    portrait_width: int = 460
    portrait_gamma: float = 1.0
    portrait_vignette: float = 0.35
    portrait_ramp: str = "even"
    portrait_polarity: str = "ink"
    portrait_weight: float = 1.0
    portrait_local: float = 0.6
    portrait_scatter: float = 0.35
    portrait_grain: float = 1.0
    portrait_duration: float = 2.2
    exclude_langs: list[str] = field(default_factory=list)
    colophon: bool = True

    @property
    def photo_path(self) -> Path:
        return ROOT / self.photo


def load(path: Path | None = None) -> Config:
    path = path or ROOT / "profile.toml"
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    p = raw.get("profile", {})
    cfg = Config(
        username=p["username"],
        name=p.get("name", ""),
        photo=p.get("photo", "assets/me.jpg"),
        about=[s.strip() for s in p.get("about", [])],
        stack=p.get("stack", []),
        portrait_cols=int(p.get("portrait_cols", 108)),
        portrait_width=int(p.get("portrait_width", 460)),
        portrait_gamma=float(p.get("portrait_gamma", 1.0)),
        portrait_vignette=float(p.get("portrait_vignette", 0.35)),
        portrait_ramp=p.get("portrait_ramp", "even"),
        portrait_polarity=p.get("portrait_polarity", "ink"),
        portrait_weight=float(p.get("portrait_weight", 1.0)),
        portrait_local=float(p.get("portrait_local", 0.6)),
        portrait_scatter=float(p.get("portrait_scatter", 0.35)),
        portrait_grain=float(p.get("portrait_grain", 1.0)),
        portrait_duration=float(p.get("portrait_duration", 2.2)),
        exclude_langs=[s.lower() for s in p.get("exclude_langs", [])],
        colophon=bool(p.get("colophon", True)),
    )
    cfg.links = [Link(l["label"], l["url"]) for l in raw.get("links", [])]
    cfg.projects = [
        Project(pr["name"], pr.get("url", ""), pr.get("meta", ""), pr.get("blurb", "").strip())
        for pr in raw.get("projects", [])
    ]
    return cfg
