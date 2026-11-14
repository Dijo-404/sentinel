"""Regression checks for repository ownership and publication safety."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.repository.validate import (
    is_ignored_markdown_path,
    validate_repository,
    validate_tasks,
    valid_markdown_whitespace,
)
from scripts.repository.tasks import index_issues, merge_issue_maps, render_issue, require_commit_files


ROOT = Path(__file__).resolve().parents[2]


class RepositoryTests(unittest.TestCase):
    def test_preserves_markdown_hard_breaks_in_supplied_specs(self):
        self.assertTrue(valid_markdown_whitespace("Title  \nText\n"))
        self.assertFalse(valid_markdown_whitespace("Text \n"))
        self.assertFalse(valid_markdown_whitespace("Text\t\n"))
        self.assertFalse(valid_markdown_whitespace("Missing newline"))

    def test_markdown_scan_skips_dependency_and_build_trees(self):
        self.assertTrue(is_ignored_markdown_path("node_modules/pkg/README.md"))
        self.assertTrue(is_ignored_markdown_path("apps/web/node_modules/x/CHANGELOG.md"))
        self.assertTrue(is_ignored_markdown_path(".venv/lib/README.md"))
        self.assertTrue(is_ignored_markdown_path("dist/docs/index.md"))
        self.assertTrue(is_ignored_markdown_path("build/out.md"))
        self.assertTrue(is_ignored_markdown_path("coverage/lcov-report/index.md"))
        self.assertTrue(is_ignored_markdown_path(".git/hooks/README.md"))
        self.assertFalse(is_ignored_markdown_path("docs/architecture.md"))
        self.assertFalse(is_ignored_markdown_path("services/workflow/README.md"))

    def test_validate_repository_ignores_node_modules_markdown(self):
        junk_dir = ROOT / "node_modules" / "dep-docs"
        junk = junk_dir / "README.md"
        junk_dir.mkdir(parents=True, exist_ok=True)
        try:
            junk.write_text("bad trailing space \nno final rules\n")
            errors = validate_repository(ROOT)
            self.assertFalse(any("node_modules" in error for error in errors), errors)
        finally:
            junk.unlink(missing_ok=True)
            try:
                junk_dir.rmdir()
                junk_dir.parent.rmdir()
            except OSError:
                pass

    def setUp(self):
        self.tasks = json.loads((ROOT / "docs/tasks.json").read_text())

    def test_independent_plan_is_valid(self):
        self.assertEqual(validate_tasks(self.tasks, ROOT), [])

    def test_rejects_task_completion_prerequisite(self):
        self.tasks[1]["depends_on"] = ["SN-001"]
        self.assertTrue(any("prerequisite" in e for e in validate_tasks(self.tasks, ROOT)))

    def test_rejects_overlapping_roots(self):
        self.tasks[1]["root"] = "tooling/workspace/nested"
        self.tasks[1]["paths"] = ["tooling/workspace/nested/**"]
        self.assertTrue(any("overlap" in e for e in validate_tasks(self.tasks, ROOT)))

    def test_rejects_cross_module_owned_path(self):
        self.tasks[1]["paths"].append("services/simulator/**")
        self.assertTrue(any("owned path" in e for e in validate_tasks(self.tasks, ROOT)))

    def test_rejects_stale_contract_digest(self):
        self.tasks[0]["contract_baseline"]["sha256"] = "0" * 64
        self.assertTrue(any("digest" in e for e in validate_tasks(self.tasks, ROOT)))

    def test_rejects_hidden_optional_mvp_peer(self):
        self.tasks[7]["consumes"].append("indic-context.v1")
        self.tasks[7]["standalone"]["peer_stubs"].append({"port": "indic-context.v1"})
        self.assertTrue(any("optional" in e for e in validate_tasks(self.tasks, ROOT)))

    def test_rejects_missing_peer_stub(self):
        self.tasks[5]["standalone"]["peer_stubs"] = []
        self.assertTrue(any("stub" in e for e in validate_tasks(self.tasks, ROOT)))

    def test_rejects_duplicate_ids_and_branches(self):
        self.tasks.append(copy.deepcopy(self.tasks[0]))
        errors = validate_tasks(self.tasks, ROOT)
        self.assertTrue(any("duplicate task" in e for e in errors))
        self.assertTrue(any("duplicate branch" in e for e in errors))

    def test_rejects_contract_path_outside_repository(self):
        self.tasks[0]["contract_baseline"]["document"] = "../outside.md"
        self.assertTrue(any("contract path" in e for e in validate_tasks(self.tasks, ROOT)))

    def test_renamed_issue_keeps_stable_identity(self):
        issues = [{"number": 7, "title": "A renamed task", "body": "<!-- sentinel-task: SN-001 -->", "html_url": "https://github.com/example/repo/issues/7"}]
        self.assertEqual(index_issues(issues)["SN-001"]["number"], 7)

    def test_closed_issue_also_prevents_duplicate(self):
        issues = [{"number": 9, "title": "[SN-001] Previous implementation", "body": "", "state": "closed"}]
        self.assertEqual(index_issues(issues)["SN-001"]["number"], 9)

    def test_duplicate_or_conflicting_identity_fails_closed(self):
        first = {"number": 1, "title": "[SN-001] One", "body": ""}
        with self.assertRaises(ValueError):
            index_issues([first, {"number": 2, "title": "[SN-001] Two", "body": ""}])
        with self.assertRaises(ValueError):
            index_issues([{**first, "body": "<!-- sentinel-task: SN-002 -->"}])

    def test_recorded_issue_survives_title_and_marker_removal(self):
        issue = {"number": 7, "title": "Renamed", "body": "No HTML marker", "state": "closed"}
        mapping = {"SN-001": {"number": 7, "url": "https://github.com/example/repo/issues/7"}}
        self.assertEqual(index_issues([issue], mapping)["SN-001"], issue)

    def test_recorded_identity_cannot_disappear_or_change(self):
        mapping = {"SN-001": {"number": 7, "url": "https://github.com/example/repo/issues/7"}}
        with self.assertRaisesRegex(ValueError, "missing"):
            index_issues([], mapping)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            index_issues([{"number": 7, "title": "[SN-002] Other task", "body": ""}], mapping)

    def test_publication_checkpoint_preserves_identity_and_rejects_conflicts(self):
        first = {"number": 7, "url": "https://github.com/example/repo/issues/7"}
        second = {"number": 8, "url": "https://github.com/example/repo/issues/8"}
        self.assertEqual(merge_issue_maps({}, {"SN-001": first}), {"SN-001": first})
        with self.assertRaisesRegex(ValueError, "conflicting"):
            merge_issue_maps({"SN-001": first}, {"SN-001": second})

    def test_rendered_task_contains_complete_baseline_and_exact_scope(self):
        task = self.tasks[8]
        baseline = (ROOT / task["contract_baseline"]["document"]).read_text()
        body = render_issue(task, "Dijo-404/sentinel", "a" * 40, baseline)
        self.assertIn("<!-- sentinel-task: SN-009 -->", body)
        self.assertIn("No task-completion prerequisites", body)
        self.assertIn(task["standalone"]["check_command"], body)
        self.assertIn(baseline, body)
        self.assertIn(hashlib.sha256(baseline.encode()).hexdigest(), body)
        self.assertIn("services/action-ledger/**", body)
        self.assertLess(len(body.encode()), 60000)

    def test_renderer_refuses_mismatched_baseline(self):
        with self.assertRaises(ValueError):
            render_issue(self.tasks[0], "Dijo-404/sentinel", "a" * 40, "wrong baseline")

    def test_publisher_rejects_working_files_that_differ_from_linked_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*arguments):
                return subprocess.run(["git", "-C", str(root), *arguments],
                                      check=True, capture_output=True, text=True).stdout.strip()
            git("init", "-q", "--initial-branch=main")
            (root / "baseline.md").write_text("reviewed baseline\n")
            git("add", "baseline.md")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
            commit = git("rev-parse", "HEAD")
            require_commit_files(root, commit, ["baseline.md"])
            (root / "baseline.md").write_text("unreviewed changes\n")
            with self.assertRaisesRegex(ValueError, "differs from"):
                require_commit_files(root, commit, ["baseline.md"])


if __name__ == "__main__":
    unittest.main()
