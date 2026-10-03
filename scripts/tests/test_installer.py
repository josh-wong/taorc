#!/usr/bin/env python3
"""Installer behavior and placement-matrix tests (v1-design-doc.md §9 items 8-9).

Exercises scripts/install.sh and scripts/install.ps1 against temp project
directories, using --source/-Source to point at this checkout so no network
access is needed. Requires a real interpreter for each script under test
(bash, pwsh) -- an interpreter that is missing, or present but non-functional
(a WSL bash stub with no distro installed), is skipped, not failed, since a
given CI runner is not expected to carry both. At least one
installer must run somewhere in the 3-OS matrix build-and-test.yaml defines,
or this file would pass vacuously everywhere.

Uses stdlib unittest rather than pytest: nothing else in this repo depends
on a test framework beyond the standard library (see taorc_lint.py's own
stdlib-only constraint), and this script is CI-only tooling, not something
that ships in the skill.
"""

from __future__ import annotations

import os
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


def find_working_bash() -> str | None:
    """Path to a bash that actually runs a command, or None if there isn't one.

    `shutil.which("bash")` alone is not enough on GitHub's windows-latest: the
    first bash on PATH there is the WSL launcher (C:\\Windows\\System32\\bash.exe),
    and with no WSL distro installed on the image it exits nonzero on every
    invocation -- so the installer tests fail instead of skipping. Probe the
    candidate with a trivial command and treat a nonzero exit as "no bash",
    which lets install.sh coverage fall back to the ubuntu and macos matrix
    legs while pwsh still covers Windows.
    """
    bash_on_path = shutil.which("bash")
    if not bash_on_path:
        return None
    try:
        probe = subprocess.run(
            [bash_on_path, "-c", "exit 0"], capture_output=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return bash_on_path if probe.returncode == 0 else None


WORKING_BASH = find_working_bash()


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
            install_output = self.run_install(project_dir)
            self.assertEqual(install_output.returncode, 0, install_output.stderr)
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


@unittest.skipUnless(WORKING_BASH, "no working bash interpreter is available")
class BashInstallerTest(InstallerCase, unittest.TestCase):
    def run_install(
        self, project_dir: Path, *agents: str, detect_only: bool = False
    ) -> subprocess.CompletedProcess:
        return self._run(project_dir, agents, uninstall=False, detect_only=detect_only)

    def run_uninstall(self, project_dir: Path, *agents: str) -> subprocess.CompletedProcess:
        return self._run(project_dir, agents, uninstall=True, detect_only=False)

    def _run(self, project_dir, agents, *, uninstall, detect_only) -> subprocess.CompletedProcess:
        args = [
            WORKING_BASH,
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
        bash_proc = subprocess.run(
            args, cwd=project_dir, capture_output=True, text=True, check=False
        )
        if bash_proc.returncode != 0:
            raise AssertionError(
                f"install.sh exited {bash_proc.returncode}\n"
                f"stdout: {bash_proc.stdout}\nstderr: {bash_proc.stderr}"
            )
        return bash_proc


@unittest.skipUnless(WORKING_BASH, "no working bash interpreter is available")
class BashDownloadUrlTest(unittest.TestCase):
    """The archive URL install.sh builds from TAORC_REF.

    Every other test here installs with --source and never reaches the
    download, so without this a change to the URL would leave CI green. A
    stub curl placed first on PATH records the URL it was handed and fails,
    which stops the installer before it needs a real archive or a network.
    """

    def requested_url(self, taorc_ref: str | None) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            stub_dir = Path(tmp) / "bin"
            stub_dir.mkdir()
            url_log = Path(tmp) / "curl-args.txt"
            stub_curl = stub_dir / "curl"
            stub_curl.write_text(
                f'#!/bin/sh\nprintf \'%s\\n\' "$@" > "{url_log}"\nexit 22\n',
                encoding="utf-8",
            )
            stub_curl.chmod(0o755)
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()

            env = {k: v for k, v in os.environ.items() if k != "TAORC_REF"}
            env["PATH"] = f"{stub_dir}{os.pathsep}{env.get('PATH', '')}"
            if taorc_ref is not None:
                env["TAORC_REF"] = taorc_ref
            install_script = REPO_ROOT / "scripts" / "install.sh"
            subprocess.run(
                [WORKING_BASH, str(install_script), "--dir", str(project_dir)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            curl_args = url_log.read_text(encoding="utf-8").splitlines()
        return next(arg for arg in curl_args if arg.startswith("https://"))

    def test_download_url_accepts_any_git_ref_and_defaults_to_main(self):
        archive_base = "https://github.com/josh-wong/taorc/archive"
        cases = [
            (None, f"{archive_base}/main.tar.gz"),
            ("main", f"{archive_base}/main.tar.gz"),
            ("fix/installer-tag-ref", f"{archive_base}/fix/installer-tag-ref.tar.gz"),
            ("v1.0.0", f"{archive_base}/v1.0.0.tar.gz"),
            ("a0b6aab", f"{archive_base}/a0b6aab.tar.gz"),
        ]
        for taorc_ref, expected_url in cases:
            with self.subTest(taorc_ref=taorc_ref):
                self.assertEqual(self.requested_url(taorc_ref), expected_url)


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
        pwsh_proc = subprocess.run(
            args, cwd=project_dir, capture_output=True, text=True, check=False
        )
        if pwsh_proc.returncode != 0:
            raise AssertionError(
                f"install.ps1 exited {pwsh_proc.returncode}\n"
                f"stdout: {pwsh_proc.stdout}\nstderr: {pwsh_proc.stderr}"
            )
        return pwsh_proc


if __name__ == "__main__":
    if not WORKING_BASH and not shutil.which("pwsh"):
        print(
            "test_installer: neither a working bash nor pwsh is available -- nothing to test here",
            file=sys.stderr,
        )
        sys.exit(1)
    unittest.main()
