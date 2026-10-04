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

import io
import os
import shutil
import subprocess
import sys
import tarfile
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


# The download tests below replace the installer's download command with a
# stub. Stubs read their paths and content from environment variables rather
# than having them pasted into generated code, so a path containing a quote
# or a $ can't break the stub.


def environ_without_taorc_ref() -> dict[str, str]:
    """A copy of this process's environment with TAORC_REF removed, so an
    installer under test downloads its default ref unless a test sets one."""
    return {k: v for k, v in os.environ.items() if k != "TAORC_REF"}


def run_install_sh_with_stub_curl(
    project_dir: Path, stub_body: str, env: dict[str, str], *installer_args: str
) -> subprocess.CompletedProcess:
    """Run install.sh against project_dir with a stub curl first on PATH.

    stub_body is the stub's shell script after its #! line, and sees curl's
    arguments as "$@". The stub is written to a bin/ directory next to
    project_dir. installer_args follow --dir on the installer's command line.
    Returns the finished installer process without checking its exit code.
    Raises FileExistsError if that bin/ directory already exists, so call it
    once per temporary directory.
    """
    stub_dir = project_dir.parent / "bin"
    stub_dir.mkdir()
    stub_curl = stub_dir / "curl"
    stub_curl.write_text("#!/bin/sh\n" + stub_body, encoding="utf-8")
    stub_curl.chmod(0o755)
    stub_env = {**env, "PATH": f"{stub_dir}{os.pathsep}{env.get('PATH', '')}"}
    install_script = REPO_ROOT / "scripts" / "install.sh"
    return subprocess.run(
        [WORKING_BASH, str(install_script), "--dir", str(project_dir), *installer_args],
        capture_output=True,
        text=True,
        env=stub_env,
        check=False,
    )


def run_install_ps1_with_stub_web_request(
    project_dir: Path, stub_body: str, env: dict[str, str], *installer_args: str
) -> subprocess.CompletedProcess:
    """Run install.ps1 against project_dir with Invoke-WebRequest shadowed.

    PowerShell resolves a function before a cmdlet of the same name, including
    inside the script it runs, so a function defined in the calling scope
    replaces the real download. stub_body is that function's body, and sees
    the installer's arguments as $Uri and $OutFile. A throw from it lands in
    install.ps1's own download catch. installer_args follow -Dir on the
    installer's command line, so they must be literal switches with no
    quoting. Returns the finished installer process without checking its
    exit code.
    """
    stub_env = {
        **env,
        "TAORC_TEST_INSTALL_SCRIPT": str(REPO_ROOT / "scripts" / "install.ps1"),
        "TAORC_TEST_PROJECT_DIR": str(project_dir),
    }
    command = (
        "function Invoke-WebRequest {"
        " param([string]$Uri, [string]$OutFile, [switch]$UseBasicParsing) "
        + stub_body
        + " }; & $env:TAORC_TEST_INSTALL_SCRIPT -Dir $env:TAORC_TEST_PROJECT_DIR "
        + " ".join(installer_args)
    )
    return subprocess.run(
        ["pwsh", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        env=stub_env,
        check=False,
    )


ARCHIVE_BASE_URL = "https://github.com/josh-wong/taorc/archive"


class DownloadUrlCase:
    """The archive URL each installer builds from TAORC_REF.

    Every installer test above passes --source/-Source and never reaches the
    download, so these are the only tests that check the URL an installer
    asks for. They check that string only. Whether GitHub serves it, and what
    the archive unpacks to, needs a real download against a real ref.

    Subclasses replace the download command with a stub that records the URL
    it was handed and then fails, which stops the installer before it needs a
    real archive or a network.
    """

    def run_with_download_stub(
        self, project_dir: Path, url_log: Path, env: dict[str, str]
    ) -> subprocess.CompletedProcess:
        """Run the installer against project_dir with its download stubbed.

        The stub must write the requested URL to url_log and then fail, so the
        installer stops before extraction. env is the environment to run the
        installer with, TAORC_REF already set or unset; the stub may add to
        it. Returns the finished installer process, whose exit code is
        expected to be nonzero.
        """
        raise NotImplementedError

    def requested_url(self, taorc_ref: str | None) -> str:
        """The URL the installer tried to download, with TAORC_REF set to
        taorc_ref, or unset when taorc_ref is None.

        Fails the test, showing the installer's output, when the installer
        stops without requesting a download.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            url_log = Path(tmp) / "requested-url.txt"
            env = environ_without_taorc_ref()
            if taorc_ref is not None:
                env["TAORC_REF"] = taorc_ref
            installer_proc = self.run_with_download_stub(project_dir, url_log, env)
            if not url_log.exists():
                self.fail(
                    f"the installer exited {installer_proc.returncode} without requesting "
                    f"a download\nstdout: {installer_proc.stdout}\nstderr: {installer_proc.stderr}"
                )
            return url_log.read_text(encoding="utf-8").strip()

    def test_download_url_accepts_any_git_ref_and_defaults_to_main(self):
        cases = [
            (None, f"{ARCHIVE_BASE_URL}/main.tar.gz"),
            ("main", f"{ARCHIVE_BASE_URL}/main.tar.gz"),
            ("feature/example", f"{ARCHIVE_BASE_URL}/feature/example.tar.gz"),
            ("v1.0.0", f"{ARCHIVE_BASE_URL}/v1.0.0.tar.gz"),
            ("a0b6aab", f"{ARCHIVE_BASE_URL}/a0b6aab.tar.gz"),
        ]
        for taorc_ref, expected_url in cases:
            with self.subTest(taorc_ref=taorc_ref):
                self.assertEqual(self.requested_url(taorc_ref), expected_url)


@unittest.skipUnless(WORKING_BASH, "no working bash interpreter is available")
class BashDownloadUrlTest(DownloadUrlCase, unittest.TestCase):
    def run_with_download_stub(self, project_dir, url_log, env):
        """Runs install.sh with a stub curl that records its https://
        argument to url_log and exits 22."""
        stub_body = (
            'for arg in "$@"; do\n'
            '    case "$arg" in\n'
            '        https://*) printf \'%s\\n\' "$arg" > "$TAORC_TEST_URL_LOG" ;;\n'
            "    esac\n"
            "done\n"
            "exit 22\n"
        )
        env = {**env, "TAORC_TEST_URL_LOG": str(url_log)}
        return run_install_sh_with_stub_curl(project_dir, stub_body, env)


@unittest.skipUnless(shutil.which("pwsh"), "pwsh is not on PATH")
class PowerShellDownloadUrlTest(DownloadUrlCase, unittest.TestCase):
    def run_with_download_stub(self, project_dir, url_log, env):
        """Runs install.ps1 with a stub Invoke-WebRequest that records -Uri
        to url_log and throws."""
        stub_body = (
            "Set-Content -LiteralPath $env:TAORC_TEST_URL_LOG -Value $Uri;"
            " throw 'download stubbed out by test_installer.py'"
        )
        env = {**env, "TAORC_TEST_URL_LOG": str(url_log)}
        return run_install_ps1_with_stub_web_request(project_dir, stub_body, env)


# Download stubs that "succeed" by copying the file at $TAORC_TEST_DOWNLOAD
# to where the installer expects its archive.
CURL_STUB_COPYING_TEST_DOWNLOAD = (
    'while [ "$#" -gt 0 ]; do\n'
    '    if [ "$1" = "-o" ]; then cp "$TAORC_TEST_DOWNLOAD" "$2"; fi\n'
    "    shift\n"
    "done\n"
)
WEB_REQUEST_STUB_COPYING_TEST_DOWNLOAD = (
    "Copy-Item -LiteralPath $env:TAORC_TEST_DOWNLOAD -Destination $OutFile"
)

NOT_AN_ARCHIVE = b"<html>not an archive</html>"

# Both installers start every fatal message with this.
INSTALLER_ERROR_PREFIX = "taorc-install: error:"

# A fragment of the default download URL short enough that PowerShell's error
# view, which wraps at word boundaries, keeps it on one line.
DEFAULT_ARCHIVE_URL_FRAGMENT = "archive/main.tar.gz"


def gzipped_tar_without_taorc_folder() -> bytes:
    """A valid .tar.gz whose only top-level folder is not named taorc-*, so
    tar extracts it successfully on every platform."""
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
        readme = tarfile.TarInfo("other-project-1.0/README")
        readme.size = 0
        archive.addfile(readme, io.BytesIO(b""))
    return archive_buffer.getvalue()


class ExtractionFailureCase:
    """Each installer must stop with an error that names the download when
    the downloaded file isn't a usable taorc archive.

    Subclasses replace the download with a stub that "succeeds" by copying
    the file at $TAORC_TEST_DOWNLOAD into place. Before #41, install.ps1
    carried on past tar's failure and stopped one step later with a
    misleading "could not locate extracted taorc source".

    Message assertions match only the start of each message or a short URL
    fragment, because PowerShell's error view wraps long lines.
    """

    def run_with_downloaded_file(
        self, project_dir: Path, env: dict[str, str]
    ) -> subprocess.CompletedProcess:
        """Run the installer against project_dir with a download stub that
        copies $TAORC_TEST_DOWNLOAD to where the archive should go and
        reports success. env is the environment to run with, TAORC_REF unset
        and TAORC_TEST_DOWNLOAD set. Returns the finished installer process
        without checking its exit code."""
        raise NotImplementedError

    def run_installer_on(self, downloaded_bytes: bytes) -> tuple[int, str]:
        """The installer's exit code and combined output after a download
        that delivered downloaded_bytes, which may be empty."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            download = Path(tmp) / "download.bin"
            download.write_bytes(downloaded_bytes)
            env = {**environ_without_taorc_ref(), "TAORC_TEST_DOWNLOAD": str(download)}
            installer_proc = self.run_with_downloaded_file(project_dir, env)
        return installer_proc.returncode, installer_proc.stdout + installer_proc.stderr

    def installer_error(self, exit_code: int, installer_output: str) -> str:
        """The installer's error message and everything after it. Fails the
        test if the installer exited 0 or printed no error.

        Matching from the error prefix matters: the installer logs the URL it
        is downloading before any error, so a URL found anywhere in the output
        would prove nothing about the error itself.
        """
        self.assertNotEqual(exit_code, 0, installer_output)
        self.assertIn(INSTALLER_ERROR_PREFIX, installer_output)
        return installer_output[installer_output.index(INSTALLER_ERROR_PREFIX) :]

    def test_corrupt_download_stops_with_tar_error_naming_the_download(self):
        error = self.installer_error(*self.run_installer_on(NOT_AN_ARCHIVE))
        self.assertIn("tar exited", error)
        self.assertIn(DEFAULT_ARCHIVE_URL_FRAGMENT, error)

    def test_archive_without_taorc_folder_stops_with_error_naming_the_download(self):
        error = self.installer_error(*self.run_installer_on(gzipped_tar_without_taorc_folder()))
        self.assertIn("no taorc source found", error)
        self.assertIn(DEFAULT_ARCHIVE_URL_FRAGMENT, error)

    def test_empty_download_stops_with_error_naming_the_download(self):
        error = self.installer_error(*self.run_installer_on(b""))
        # GNU tar fails on an empty file and bsdtar (macOS, Windows) exits 0,
        # so the installer legitimately stops at either message.
        self.assertTrue("tar exited" in error or "no taorc source found" in error, error)
        self.assertIn(DEFAULT_ARCHIVE_URL_FRAGMENT, error)


@unittest.skipUnless(
    WORKING_BASH and shutil.which("tar"), "needs a working bash interpreter and tar"
)
class BashExtractionFailureTest(ExtractionFailureCase, unittest.TestCase):
    def run_with_downloaded_file(self, project_dir, env):
        """Runs install.sh with a stub curl that copies $TAORC_TEST_DOWNLOAD
        to the file named by its -o argument and exits 0."""
        return run_install_sh_with_stub_curl(project_dir, CURL_STUB_COPYING_TEST_DOWNLOAD, env)


@unittest.skipUnless(shutil.which("pwsh") and shutil.which("tar"), "needs pwsh and tar")
class PowerShellExtractionFailureTest(ExtractionFailureCase, unittest.TestCase):
    def run_with_downloaded_file(self, project_dir, env):
        """Runs install.ps1 with a stub Invoke-WebRequest that copies
        $TAORC_TEST_DOWNLOAD to -OutFile and returns normally."""
        return run_install_ps1_with_stub_web_request(
            project_dir, WEB_REQUEST_STUB_COPYING_TEST_DOWNLOAD, env
        )


# Any version the checkout's own VERSION will never hold.
OTHER_VERSION = "9.9.9"


def gzipped_taorc_archive(version: str) -> bytes:
    """A .tar.gz laid out like GitHub's archive of this checkout, with its
    VERSION file set to version. Holds only the files the installers read."""

    def skip_bytecode(member: tarfile.TarInfo) -> tarfile.TarInfo | None:
        return None if "__pycache__" in member.name else member

    version_bytes = f"{version}\n".encode()
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
        for relative_path in ("skills/readable-code", "templates/agent-block.md"):
            archive.add(
                REPO_ROOT / relative_path,
                arcname=f"taorc-main/{relative_path}",
                filter=skip_bytecode,
            )
        version_file = tarfile.TarInfo("taorc-main/VERSION")
        version_file.size = len(version_bytes)
        archive.addfile(version_file, io.BytesIO(version_bytes))
    return archive_buffer.getvalue()


class InstallerVersionCheckCase:
    """With TAORC_REF unset, each installer must stop when the downloaded
    VERSION differs from its own, so an installer fetched from a release tag
    never quietly installs whatever main holds (#42).

    Subclasses stub the download the same way ExtractionFailureCase's do,
    and set AGENTS_MD_UNINSTALL_ARGS to their installer's arguments for
    uninstalling the AGENTS.md adapter alone.
    """

    AGENTS_MD_UNINSTALL_ARGS: tuple[str, ...] = ()

    def run_with_downloaded_file(
        self, project_dir: Path, env: dict[str, str], *installer_args: str
    ) -> subprocess.CompletedProcess:
        """Run the installer against project_dir with a download stub that
        copies $TAORC_TEST_DOWNLOAD into place. installer_args are appended
        to the installer's command line. Returns the finished installer
        process without checking its exit code."""
        raise NotImplementedError

    def install_from_archive(
        self,
        project_dir: Path,
        archive_version: str,
        *installer_args: str,
        taorc_ref: str | None = None,
    ) -> subprocess.CompletedProcess:
        """Run the installer against project_dir after a download of a taorc
        archive whose VERSION is archive_version, with TAORC_REF set to
        taorc_ref, or unset when it is None. Returns the finished installer
        process without checking its exit code."""
        download = project_dir.parent / "download.tar.gz"
        download.write_bytes(gzipped_taorc_archive(archive_version))
        env = {**environ_without_taorc_ref(), "TAORC_TEST_DOWNLOAD": str(download)}
        if taorc_ref is not None:
            env["TAORC_REF"] = taorc_ref
        return self.run_with_downloaded_file(project_dir, env, *installer_args)

    def test_default_download_of_another_version_stops_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            installer_proc = self.install_from_archive(project_dir, OTHER_VERSION)
            installer_output = installer_proc.stdout + installer_proc.stderr
            self.assertNotEqual(installer_proc.returncode, 0, installer_output)
            self.assertIn(INSTALLER_ERROR_PREFIX, installer_output)
            error = installer_output[installer_output.index(INSTALLER_ERROR_PREFIX) :]
            # Short fragments only: PowerShell's error view wraps long lines.
            self.assertIn(f"v{read_version()}", error)
            self.assertIn(f"v{OTHER_VERSION}", error)
            self.assertIn("TAORC_REF", error)
            self.assertEqual(list(project_dir.iterdir()), [], "files were written before the stop")

    def test_default_download_of_own_version_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            installer_proc = self.install_from_archive(project_dir, read_version())
            self.assertEqual(
                installer_proc.returncode, 0, installer_proc.stdout + installer_proc.stderr
            )
            agents_text = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(f"<!-- taorc:begin v{read_version()} -->", agents_text)

    def test_explicit_taorc_ref_installs_another_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            installer_proc = self.install_from_archive(project_dir, OTHER_VERSION, taorc_ref="main")
            self.assertEqual(
                installer_proc.returncode, 0, installer_proc.stdout + installer_proc.stderr
            )
            agents_text = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(f"<!-- taorc:begin v{OTHER_VERSION} -->", agents_text)

    def test_uninstall_after_default_download_of_another_version_removes_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "proj"
            project_dir.mkdir()
            (project_dir / "AGENTS.md").write_text(
                "# My project\n\n<!-- taorc:begin v0.1.0 -->\nold\n<!-- taorc:end -->\n",
                encoding="utf-8",
            )
            installer_proc = self.install_from_archive(
                project_dir, OTHER_VERSION, *self.AGENTS_MD_UNINSTALL_ARGS
            )
            self.assertEqual(
                installer_proc.returncode, 0, installer_proc.stdout + installer_proc.stderr
            )
            agents_text = (project_dir / "AGENTS.md").read_text(encoding="utf-8")
            self.assertNotIn("taorc:begin", agents_text)
            self.assertIn("# My project", agents_text)


@unittest.skipUnless(
    WORKING_BASH and shutil.which("tar"), "needs a working bash interpreter and tar"
)
class BashInstallerVersionCheckTest(InstallerVersionCheckCase, unittest.TestCase):
    AGENTS_MD_UNINSTALL_ARGS = ("--uninstall", "--agents=agents")

    def run_with_downloaded_file(self, project_dir, env, *installer_args):
        return run_install_sh_with_stub_curl(
            project_dir, CURL_STUB_COPYING_TEST_DOWNLOAD, env, *installer_args
        )


@unittest.skipUnless(shutil.which("pwsh") and shutil.which("tar"), "needs pwsh and tar")
class PowerShellInstallerVersionCheckTest(InstallerVersionCheckCase, unittest.TestCase):
    AGENTS_MD_UNINSTALL_ARGS = ("-Uninstall", "-Agents", "agents")

    def run_with_downloaded_file(self, project_dir, env, *installer_args):
        return run_install_ps1_with_stub_web_request(
            project_dir, WEB_REQUEST_STUB_COPYING_TEST_DOWNLOAD, env, *installer_args
        )


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
