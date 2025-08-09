from pathlib import Path
import pytest

from core.sandbox import SandboxMode, SandboxPolicy, SandboxGuard, SandboxViolation


def make_guard(tmp_path: Path, mode: SandboxMode, allows_writes: bool, consent: bool) -> SandboxGuard:
    return SandboxGuard(
        SandboxPolicy(
            mode=mode,
            project_root=tmp_path,
            allows_writes=allows_writes,
            user_write_consent=consent,
        )
    )


def test_read_allowed_within_project(tmp_path: Path):
    guard = make_guard(tmp_path, SandboxMode.FULL, allows_writes=False, consent=False)
    guard.assert_read_allowed(tmp_path / "README.md")  # should not raise


def test_read_disallowed_outside_project(tmp_path: Path):
    guard = make_guard(tmp_path, SandboxMode.FULL, allows_writes=False, consent=False)
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(SandboxViolation):
        guard.assert_read_allowed(outside)


def test_write_disallowed_in_full(tmp_path: Path):
    guard = make_guard(tmp_path, SandboxMode.FULL, allows_writes=True, consent=True)
    with pytest.raises(SandboxViolation):
        guard.assert_write_allowed(tmp_path / "file.txt")


def test_write_disallowed_in_limited_without_capability(tmp_path: Path):
    guard = make_guard(tmp_path, SandboxMode.LIMITED, allows_writes=False, consent=True)
    with pytest.raises(SandboxViolation):
        guard.assert_write_allowed(tmp_path / "file.txt")


def test_write_disallowed_in_limited_without_consent(tmp_path: Path):
    guard = make_guard(tmp_path, SandboxMode.LIMITED, allows_writes=True, consent=False)
    with pytest.raises(SandboxViolation):
        guard.assert_write_allowed(tmp_path / "file.txt")


def test_write_allowed_in_limited_with_capability_and_consent(tmp_path: Path):
    guard = make_guard(tmp_path, SandboxMode.LIMITED, allows_writes=True, consent=True)
    # should not raise
    guard.assert_write_allowed(tmp_path / "file.txt")


def test_subprocess_and_vcs_always_disallowed(tmp_path: Path):
    guard = make_guard(tmp_path, SandboxMode.LIMITED, allows_writes=True, consent=True)
    with pytest.raises(SandboxViolation):
        guard.assert_subprocess_disallowed()
    with pytest.raises(SandboxViolation):
        guard.assert_vcs_disallowed()
