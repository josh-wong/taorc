#!/usr/bin/env python3
"""Installer behavior and placement-matrix tests (v1-design-doc.md §9 items 8-9).

Exercises scripts/install.sh and scripts/install.ps1 against temp project
directories, using --source/-Source to point at this checkout so no network
access is needed. Requires a real interpreter for each script under test
(bash, pwsh) -- an interpreter that is not on PATH is skipped, not failed,
since a given CI runner is not expected to carry both. At least one
installer must run somewhere in the 3-OS matrix build-and-test.yaml defines,
or this file would pass vacuously everywhere.

Uses stdlib unittest rather than pytest: nothing else in this repo depends
on a test framework beyond the standard library (see taorc_lint.py's own
stdlib-only constraint), and this script is CI-only tooling, not something
that ships in the skill.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The 10 R3.2 targets an --agents=all install must place (v1-product-
# requirements-doc.md R3.2; the Agent Skills runtime and prompts/system-
# prompt.md targets are source-tree artifacts, not installer output, and are
# covered by validate.py instead).
EXPECTED_BLOCK_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursor/rules/readable-code.mdc",
    ".github/copilot-instructions.md",
    ".github/instructions/readable-code.instructions.md",
    ".clinerules/readable-code.md",
    ".windsurf/rules/readable-code.md",
]
EXPECTED_SKILL_DIRS = [
    ".claude/skills/readable-code",
    ".github/skills/readable-code",
]


def read_version() -> str:
    return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


class InstallerCase:
    """Mixin the concrete bash/pwsh test classes implement.

    Subclasses provide `run_install` and `run_uninstall`, which invoke their
    respective script against a project directory. Test bodies stay
    interpreter-agnostic so the same assertions run against both scripts.
    """

    def run_install(self, project_dir: Path, *extra_args: str) -> subprocess.CompletedProcess:
        raise NotImplementedError

    def assert_placement_matrix(self, project_dir: Path) -> None:
        version = read_version()
        marker = f"<!-- taorc:begin v{version} -->"
        for relative_path in EXPECTED_BLOCK_FILES:
            path = project_dir / relative_path
            self.assertTrue(path.exists(), f"{relative_path} was not installed")
            text = path.read_text(encoding="utf-8")
            self.assertIn(marker, text, f"{relative_path} is missing the v{version} marker")
            self.assertIn("<!-- taorc:end -->", text)
        for relative_path in EXPECTED_SKILL_DIRS:
            skill_md = project_dir / relative_path / "SKILL.md"
            self.assertTrue(skill_md.exists(), f"{relative_path}/SKILL.md was not installed")

    def test_fresh_install_placement_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            result = self.run_install(project_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_placement_matrix(project_dir)

    def test_idempotent_reinstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            self.run_install(project_dir)
            before = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.run_install(project_dir)
            after = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(before, after, "a second install changed AGENTS.md")
            # A third pass catches an off-by-one that only a second replace
            # would reveal (e.g. a blank line that accumulates one per run).
            self.run_install(project_dir)
            third = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(after, third, "a third install changed AGENTS.md")

    def test_preserves_existing_user_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            (project_dir / "AGENTS.md").write_text(
                "# My project\n\nSome existing instructions.\n", encoding="utf-8"
            )
            self.run_install(project_dir, "agents")
            text = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Some existing instructions.", text)
            self.assertIn("<!-- taorc:begin", text)

    def test_detect_skips_uninstalled_adapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            self.run_install(project_dir, "gemini", detect_only=True)
            self.assertFalse(
                (project_dir / "GEMINI.md").exists(),
                "--detect created an adapter that was never installed",
            )

    def test_uninstall_removes_block_and_keeps_user_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            (project_dir / "AGENTS.md").write_text(
                "# My project\n\nSome existing instructions.\n", encoding="utf-8"
            )
            self.run_install(project_dir, "claude")
            self.run_uninstall(project_dir, "claude")

            agents_text = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertNotIn("taorc:begin", agents_text)
            self.assertIn("Some existing instructions.", agents_text)
            self.assertFalse(
                (project_dir / "CLAUDE.md").exists(), "taorc-only CLAUDE.md should be removed"
            )
            self.assertFalse(
                (project_dir / ".claude" / "skills" / "readable-code").exists(),
                "skill copy should be removed on uninstall",
            )


@unittest.skipUnless(shutil.which("bash"), "bash is not on PATH")
class BashInstallerTest(InstallerCase, unittest.TestCase):
    def run_install(
        self, project_dir: Path, *agents: str, detect_only: bool = False
    ) -> subprocess.CompletedProcess:
        return self._run(project_dir, agents, uninstall=False, detect_only=detect_only)

    def run_uninstall(self, project_dir: Path, *agents: str) -> subprocess.CompletedProcess:
        return self._run(project_dir, agents, uninstall=True, detect_only=False)

    def _run(self, project_dir, agents, *, uninstall, detect_only) -> subprocess.CompletedProcess:
        args = [
            "bash",
            str(REPO_ROOT / "scripts" / "install.sh"),
            "--source",
            str(REPO_ROOT),
        ]
        if agents:
            args += ["--agents", ",".join(agents)]
        if uninstall:
            args.append("--uninstall")
        if detect_only:
            args.append("--detect")
        result = subprocess.run(args, cwd=project_dir, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AssertionError(
                f"install.sh exited {result.returncode}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result


@unittest.skipUnless(shutil.which("pwsh"), "pwsh is not on PATH")
class PowerShellInstallerTest(InstallerCase, unittest.TestCase):
    def run_install(
        self, project_dir: Path, *agents: str, detect_only: bool = False
    ) -> subprocess.CompletedProcess:
        return self._run(project_dir, agents, uninstall=False, detect_only=detect_only)

    def run_uninstall(self, project_dir: Path, *agents: str) -> subprocess.CompletedProcess:
        return self._run(project_dir, agents, uninstall=True, detect_only=False)

    def _run(self, project_dir, agents, *, uninstall, detect_only) -> subprocess.CompletedProcess:
        args = [
            "pwsh",
            "-NoProfile",
            "-File",
            str(REPO_ROOT / "scripts" / "install.ps1"),
            "-Source",
            str(REPO_ROOT),
        ]
        if agents:
            args += ["-Agents", ",".join(agents)]
        if uninstall:
            args.append("-Uninstall")
        if detect_only:
            args.append("-Detect")
        result = subprocess.run(args, cwd=project_dir, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AssertionError(
                f"install.ps1 exited {result.returncode}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result


if __name__ == "__main__":
    if not shutil.which("bash") and not shutil.which("pwsh"):
        print(
            "test_installer: neither bash nor pwsh is on PATH -- nothing to test here",
            file=sys.stderr,
        )
        sys.exit(1)
    unittest.main()
