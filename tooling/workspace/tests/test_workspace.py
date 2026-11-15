import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
FIXTURE = MODULE / "tests" / "fixtures" / "mini-repo"


class WorkspaceChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        shutil.copytree(FIXTURE, self.repo)

    def run_cli(self, *args):
        env = dict(os.environ, PYTHONPATH=str(MODULE / "src"))
        return subprocess.run(
            [sys.executable, "-m", "sentinel_workspace", *args, "--repo", str(self.repo)],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def report(self, command="check", *args):
        result = self.run_cli(command, *args)
        self.assertTrue(result.stdout, result.stderr)
        return result, json.loads(result.stdout)

    def update_tasks(self, tasks):
        (self.repo / "docs" / "tasks.json").write_text(json.dumps(tasks))

    def test_discovery_distinguishes_absent_scaffold_and_ready_without_running(self):
        result, report = self.report("discover")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["contract_version"], "module-checks.v1")
        self.assertEqual(
            [m["status"] for m in report["modules"]], ["READY", "ABSENT", "UNIMPLEMENTED", "READY"]
        )
        self.assertFalse((self.repo / "modules" / "good" / "checked").exists())

    def test_check_runs_present_modules_and_reports_missing_without_fabricated_success(self):
        result, report = self.report(
            "check", "--module", "SN-001", "--module", "SN-002", "--module", "SN-003"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [m["status"] for m in report["modules"]], ["PASS", "ABSENT", "UNIMPLEMENTED", "SKIPPED"]
        )
        self.assertEqual(
            (self.repo / "modules" / "good" / "checked").read_text(), "fixture module checked\n"
        )
        self.assertIn("synthetic fixture success", report["modules"][0]["output"])

    def test_failed_module_does_not_stop_later_checks(self):
        tasks = json.loads((self.repo / "docs" / "tasks.json").read_text())
        self.update_tasks([tasks[3], tasks[0]])
        result, report = self.report()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual([m["status"] for m in report["modules"]], ["FAIL", "PASS"])
        self.assertEqual(report["modules"][0]["id"], "SN-004")
        self.assertNotEqual(report["modules"][0]["exit_code"], 0)
        self.assertIn("synthetic check failure", report["modules"][0]["output"])

    def test_changed_paths_select_owned_files_including_deleted_and_extra_paths(self):
        changes = self.repo / "changes.bin"
        changes.write_bytes(b"modules/good/deleted.py\0.github/workflows/fixture.yml\0")
        result, report = self.report("check", "--changed-paths", str(changes))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [m["status"] for m in report["modules"]], ["PASS", "ABSENT", "SKIPPED", "SKIPPED"]
        )

    def test_unrelated_paths_do_not_run_failed_siblings(self):
        changes = self.repo / "changes.bin"
        changes.write_bytes(b"docs/readme.md\0")
        result, report = self.report("check", "--changed-paths", str(changes))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({m["status"] for m in report["modules"]}, {"SKIPPED"})

    def test_unknown_selected_module_fails_before_any_checks(self):
        result = self.run_cli("check", "--module", "SN-999")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown module", result.stderr)
        self.assertFalse((self.repo / "modules" / "good" / "checked").exists())

    def test_malformed_metadata_fails_before_any_checks(self):
        for value in ({}, [None], [{"id": "SN-001"}], "bad"):
            with self.subTest(value=value):
                self.update_tasks(value)
                result = self.run_cli("check")
                self.assertEqual(result.returncode, 2, result.stderr)
        (self.repo / "docs" / "tasks.json").write_text("{")
        result = self.run_cli("check")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.repo / "modules" / "good" / "checked").exists())

    def test_traversal_absolute_duplicate_and_overlapping_roots_rejected_before_execution(self):
        original = json.loads((self.repo / "docs" / "tasks.json").read_text())
        variants = [
            [original[0], {"id": "SN-002", "root": root}]
            for root in ("../outside", "/tmp/outside", "modules/../good", "modules\\good", ".")
        ]
        variants += [
            [original[0], original[0]],
            [original[0], {"id": "SN-002", "root": "modules/good"}],
            [original[0], {"id": "SN-002", "root": "modules/good/nested"}],
        ]
        for tasks in variants:
            with self.subTest(tasks=tasks):
                self.update_tasks(tasks)
                result = self.run_cli("check")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse((self.repo / "modules" / "good" / "checked").exists())

    def test_root_and_makefile_symlink_escape_rejected(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "Makefile").write_text("check:\n\t@touch escaped\n")
        module = self.repo / "modules" / "bad-link"
        module.symlink_to(outside, target_is_directory=True)
        self.update_tasks([{"id": "SN-001", "root": "modules/bad-link"}])
        self.assertEqual(self.run_cli("check").returncode, 2)
        module.unlink()
        module.mkdir()
        (module / "Makefile").symlink_to(outside / "Makefile")
        self.assertEqual(self.run_cli("check").returncode, 2)
        self.assertFalse((outside / "escaped").exists())

    def test_symlink_alias_cannot_run_same_module_twice(self):
        (self.repo / "modules" / "alias").symlink_to(
            self.repo / "modules" / "good", target_is_directory=True
        )
        self.update_tasks(
            [{"id": "SN-001", "root": "modules/good"}, {"id": "SN-002", "root": "modules/alias"}]
        )
        self.assertEqual(self.run_cli("check").returncode, 2)
        self.assertFalse((self.repo / "modules" / "good" / "checked").exists())

    def test_makefile_without_check_target_is_a_failure(self):
        (self.repo / "modules" / "good" / "Makefile").write_text("other:\n\t@echo other\n")
        result, report = self.report("check", "--module", "SN-001")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["modules"][0]["status"], "FAIL")
        self.assertIn("check", report["modules"][0]["output"])

    def test_timeout_kills_child_process_before_it_can_write(self):
        (self.repo / "modules" / "good" / "check.py").write_text(
            "import subprocess, sys\n"
            "subprocess.Popen([sys.executable, '-c', "
            "\"import time; from pathlib import Path; time.sleep(0.8); Path('leaked').touch()\"])\n"
            "import time; time.sleep(10)\n"
        )
        result, report = self.report("check", "--module", "SN-001", "--timeout", "0.2")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["modules"][0]["status"], "TIMEOUT")
        import time

        time.sleep(1)
        self.assertFalse((self.repo / "modules" / "good" / "leaked").exists())

    def test_nonstandard_command_cannot_be_injected_through_metadata(self):
        self.update_tasks(
            [
                {
                    "id": "SN-001",
                    "root": "modules/good",
                    "standalone": {"check_command": "touch unauthorized"},
                }
            ]
        )
        self.assertEqual(self.run_cli("check").returncode, 2)
        self.assertFalse((self.repo / "unauthorized").exists())

    def test_timeout_and_output_limit_are_failures_and_other_modules_continue(self):
        for recipe, options, expected in [
            ("@python3 -c 'import time; time.sleep(10)'", ["--timeout", "0.2"], "TIMEOUT"),
            ("@python3 -c 'print(\"x\" * 200000)'", ["--max-output-bytes", "512"], "OUTPUT_LIMIT"),
        ]:
            with self.subTest(expected=expected):
                (self.repo / "modules" / "fail" / "Makefile").write_text(
                    "check:\n\t" + recipe + "\n"
                )
                tasks = json.loads((FIXTURE / "docs" / "tasks.json").read_text())
                self.update_tasks([tasks[3], tasks[0]])
                result, report = self.report("check", *options)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual([m["status"] for m in report["modules"]], [expected, "PASS"])
                self.assertLessEqual(
                    len(report["modules"][0]["output"].encode()),
                    512 if expected == "OUTPUT_LIMIT" else 65536,
                )

    def test_missing_make_executable_is_visible_not_fixture_success(self):
        from sentinel_workspace.contracts import Module
        from sentinel_workspace.runner import run_check

        result = run_check(
            self.repo,
            Module("SN-001", "modules/good", ()),
            make="/nonexistent/sentinel-make",
            timeout=1,
            max_output_bytes=512,
        )
        self.assertEqual(result.status, "ERROR")
        self.assertIsNone(result.exit_code)

    def test_invalid_limits_rejected_before_checks(self):
        for options in (["--timeout", "0"], ["--timeout", "nan"], ["--max-output-bytes", "0"]):
            result = self.run_cli("check", *options)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((self.repo / "modules" / "good" / "checked").exists())


if __name__ == "__main__":
    unittest.main()
