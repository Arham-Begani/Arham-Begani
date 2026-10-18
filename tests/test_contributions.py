import unittest
from unittest.mock import patch

from build.github import PullRequest, _pull_requests
from build.readme import contributions


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


if __name__ == "__main__":
    unittest.main()
