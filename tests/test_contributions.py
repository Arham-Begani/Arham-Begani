import unittest
from unittest.mock import patch

from build.github import PullRequest, _pull_requests
from build.readme import _stars, contributions


def node(owner, *, private=False, number=1, state="OPEN", merged_at=None):
    return {
        "number": number, "title": "Fix a regression", "url": f"https://github.com/{owner}/tool/pull/{number}",
        "state": state, "isDraft": False, "mergedAt": merged_at,
        "repository": {"nameWithOwner": f"{owner}/tool", "isPrivate": private,
                       "owner": {"login": owner}},
    }


class ContributionTests(unittest.TestCase):
    def test_pagination_excludes_private_and_own_repositories(self):
        first = {"nodes": [node("ARHAM-BEGANI"), node("private-org", private=True), node("public-org")],
                 "pageInfo": {"hasNextPage": True, "endCursor": "page-two"}}
        last = {"nodes": [node("another-org", number=2)],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}
        with patch("build.github._post", return_value={"user": {"pullRequests": last}}) as request:
            prs = _pull_requests("test-token", "Arham-Begani", first)
        self.assertEqual([pr.repository for pr in prs], ["public-org/tool", "another-org/tool"])
        self.assertEqual(request.call_args.args[1], {"login": "Arham-Begani", "after": "page-two"})

    def test_readme_separates_states_and_escapes_untrusted_titles(self):
        prs = [
            PullRequest("org/tool", 1, "Fix | [parser]\n<script>", "https://github.com/org/tool/pull/1", "OPEN"),
            PullRequest("org/tool", 2, "Draft fix", "https://github.com/org/tool/pull/2", "OPEN", draft=True),
            PullRequest("org/tool", 3, "Merged fix", "https://github.com/org/tool/pull/3", "MERGED", merged_at="2026-10-17T12:00:00Z"),
            PullRequest("org/tool", 4, "Closed attempt", "https://github.com/org/tool/pull/4", "CLOSED"),
        ]
        result = contributions(prs, "Arham-Begani")
        self.assertIn("**Merged**", result)
        self.assertIn("Merged · 2026-10-17", result)
        self.assertIn("| Open |", result)
        self.assertIn("| Draft |", result)
        self.assertIn("<summary>Closed without merging · 1</summary>", result)
        self.assertIn(r"Fix \| \[parser\] &lt;script&gt;", result)
        self.assertNotIn("<script>", result)
        self.assertNotIn("Draft · 2026", result)

    def test_closed_pull_requests_labeled_merged_count_as_merged(self):
        landed = dict(node("meta", number=7, state="CLOSED"), closedAt="2026-11-07T01:00:00Z",
                      labels={"nodes": [{"name": "cla signed"}, {"name": "Merged"}]})
        rejected = dict(node("org", number=8, state="CLOSED"), closedAt="2026-11-01T00:00:00Z",
                        labels={"nodes": [{"name": "wontfix"}]})
        page = {"nodes": [landed, rejected], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        prs = _pull_requests("test-token", "Arham-Begani", page)
        self.assertEqual([(pr.state, pr.merged_at) for pr in prs],
                         [("MERGED", "2026-11-07T01:00:00Z"), ("CLOSED", None)])
        result = contributions(prs, "Arham-Begani")
        self.assertIn("Merged · 2026-11-07", result)
        self.assertIn("<summary>Closed without merging · 1</summary>", result)

    def test_stars_are_read_and_shown_in_short_form(self):
        page = {"nodes": [dict(node("org"), repository={"nameWithOwner": "org/tool", "isPrivate": False,
                                                        "stargazerCount": 182_400, "owner": {"login": "org"}})],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}
        prs = _pull_requests("test-token", "Arham-Begani", page)
        self.assertEqual(prs[0].stars, 182_400)
        self.assertIn("| [tool](https://github.com/org/tool) | 182k |", contributions(prs, "Arham-Begani"))
        self.assertEqual([_stars(n) for n in (950, 1_200, 1_000, 48_400, 1_100_000)],
                         ["950", "1.2k", "1k", "48k", "1.1M"])

    def test_summary_sorting_and_hidden_entries(self):
        prs = [
            PullRequest("small/lib", 1, "Small", "https://github.com/small/lib/pull/1", "OPEN", stars=10),
            PullRequest("big/app", 2, "Big", "https://github.com/big/app/pull/2", "OPEN", stars=90_000),
            PullRequest("big/app", 3, "Draft", "https://github.com/big/app/pull/3", "OPEN", draft=True, stars=90_000),
            PullRequest("org/tool", 4, "Merged", "https://github.com/org/tool/pull/4", "MERGED",
                        merged_at="2026-10-17T12:00:00Z"),
            PullRequest("practice/repo", 5, "Hello", "https://github.com/practice/repo/pull/5", "MERGED",
                        merged_at="2024-07-20T12:00:00Z"),
            PullRequest("org/tool", 6, "One-off", "https://github.com/org/tool/pull/6", "OPEN"),
        ]
        result = contributions(prs, "Arham-Begani", ["Practice/Repo", "org/tool#6"])
        self.assertIn("**1 merged** · **3 in review** across 3 projects.", result)
        self.assertNotIn("practice/repo", result)
        self.assertNotIn("One-off", result)
        # Ready pull requests first, most-starred project first, drafts last.
        self.assertLess(result.index("Big · #2"), result.index("Small · #1"))
        self.assertLess(result.index("Small · #1"), result.index("Draft · #3"))


if __name__ == "__main__":
    unittest.main()
