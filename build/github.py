"""One GraphQL round trip for everything the page shows.

Needs a token in GITHUB_TOKEN. The workflow's built-in token is enough for
public activity; a classic PAT with read:user also picks up private
contributions if you have "include private contributions" switched on in
your GitHub profile settings.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import urllib.error
import urllib.request
from dataclasses import dataclass, field

API = "https://api.github.com/graphql"

QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    name
    followers { totalCount }
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false,
                 orderBy:{field:PUSHED_AT, direction:DESC}) {
      totalCount
      nodes {
        name
        stargazerCount
        isPrivate
        primaryLanguage { name }
        languages(first:8, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


@dataclass
class Day:
    date: dt.date
    count: int


@dataclass
class Stats:
    login: str
    name: str = ""
    days: list[Day] = field(default_factory=list)
    total: int = 0
    commits: int = 0
    prs: int = 0
    issues: int = 0
    private: int = 0
    followers: int = 0
    repos: int = 0
    stars: int = 0
    bytes_by_lang: dict[str, int] = field(default_factory=dict)
    repos_by_lang: dict[str, int] = field(default_factory=dict)

    # -- derived ----------------------------------------------------------
    @property
    def active_days(self) -> int:
        return sum(1 for d in self.days if d.count)

    @property
    def span(self) -> int:
        return len(self.days)

    @property
    def best_day(self) -> Day:
        return max(self.days, key=lambda d: d.count)

    @property
    def best_week(self) -> int:
        counts = [d.count for d in self.days]
        return max((sum(counts[i:i + 7]) for i in range(0, len(counts), 7)), default=0)

    @property
    def current_streak(self) -> int:
        n = 0
        for d in reversed(self.days):
            if d.count:
                n += 1
            elif n or d is self.days[-1]:
                # today still counts as "not broken yet" if it is empty
                if d is self.days[-1]:
                    continue
                break
            else:
                break
        return n

    @property
    def longest_streak(self) -> int:
        best = run = 0
        for d in self.days:
            run = run + 1 if d.count else 0
            best = max(best, run)
        return best

    @property
    def weekly(self) -> list[int]:
        c = [d.count for d in self.days]
        return [sum(c[i:i + 7]) for i in range(0, len(c), 7)]


def _post(token: str, variables: dict) -> dict:
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-builder",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL: {payload['errors']}")
    return payload["data"]


def fetch(login: str, *, token: str | None = None, exclude: list[str] | None = None) -> Stats:
    token = token or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        raise RuntimeError("set GITHUB_TOKEN (or pass --demo to build with sample data)")
    exclude = {e.lower() for e in (exclude or [])}

    to = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    frm = to - dt.timedelta(days=364)
    data = _post(token, {"login": login, "from": frm.isoformat(), "to": to.isoformat()})
    u = data["user"]
    if u is None:
        raise RuntimeError(f"no such user: {login}")

    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [
        Day(dt.date.fromisoformat(d["date"]), d["contributionCount"])
        for w in cal["weeks"] for d in w["contributionDays"]
    ]

    s = Stats(
        login=login,
        name=u.get("name") or login,
        days=days,
        total=cal["totalContributions"],
        commits=cc["totalCommitContributions"],
        prs=cc["totalPullRequestContributions"],
        issues=cc["totalIssueContributions"],
        private=cc["restrictedContributionsCount"],
        followers=u["followers"]["totalCount"],
        repos=u["repositories"]["totalCount"],
    )
    for repo in u["repositories"]["nodes"]:
        s.stars += repo["stargazerCount"]
        seen: set[str] = set()
        for e in repo["languages"]["edges"]:
            lang = e["node"]["name"]
            if lang.lower() in exclude:
                continue
            s.bytes_by_lang[lang] = s.bytes_by_lang.get(lang, 0) + e["size"]
            seen.add(lang)
        prim = (repo.get("primaryLanguage") or {}).get("name")
        if prim and prim.lower() not in exclude:
            s.repos_by_lang[prim] = s.repos_by_lang.get(prim, 0) + 1
        elif seen:
            top = max(seen, key=lambda l: s.bytes_by_lang[l])
            s.repos_by_lang[top] = s.repos_by_lang.get(top, 0) + 1
    return s


def demo(login: str = "octocat") -> Stats:
    """Plausible sample data, so you can build the page before wiring a token."""
    rng = random.Random(7)
    today = dt.date.today()
    start = today - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # align to Sunday
    days, streak = [], 0
    for i in range((today - start).days + 1):
        d = start + dt.timedelta(days=i)
        base = 0.16 if d.weekday() >= 5 else 0.42
        if streak > 0 and rng.random() < 0.5:
            base += 0.22
        hot = 1.9 if 120 < i < 150 or 300 < i < 316 else 1.0
        n = 0 if rng.random() > base else max(1, int(rng.gammavariate(1.5, 2.0) * hot))
        streak = streak + 1 if n else 0
        days.append(Day(d, n))
    s = Stats(login=login, name="Sample User", days=days,
              total=sum(d.count for d in days), followers=128, repos=27, stars=311)
    s.commits = int(s.total * 0.82)
    s.prs, s.issues, s.private = 46, 23, int(s.total * 0.18)
    s.bytes_by_lang = {"Python": 1_840_000, "TypeScript": 1_120_000, "Rust": 430_000,
                       "JavaScript": 260_000, "Go": 150_000, "Shell": 44_000}
    s.repos_by_lang = {"Python": 11, "TypeScript": 7, "Rust": 4, "JavaScript": 3, "Go": 2}
    return s
