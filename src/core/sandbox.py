"""Sandbox policy scaffolding (to be implemented in Phase 1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SandboxMode(Enum):
    """Sandbox policy levels.

    FULL:
        - Project directory is visible but treated as read-only by policy
        - No subprocess/spawned shells allowed
        - No VCS interactions allowed
    LIMITED:
        - Project directory is visible; writes are permitted only if BOTH the
          use case declares capability and the user has granted consent.
        - No subprocess/spawned shells allowed
        - No VCS interactions allowed
    """

    FULL = "full"
    LIMITED = "limited"


@dataclass(frozen=True)
class SandboxPolicy:
    """Effective sandbox configuration for a run.

    Notes
    -----
    - "user_write_consent" is a top-level control that we'll wire later in the CLI.
    - "allows_writes" comes from the use case capability declaration.
    - Enforcement is centralized in SandboxGuard.
    """

    mode: SandboxMode
    project_root: Path
    allows_writes: bool
    user_write_consent: bool = False


class SandboxViolation(PermissionError):
    """Raised when an action violates the sandbox policy."""


class SandboxGuard:
    """Central guard for sandbox restrictions.

    This is a minimal skeleton for Phase 1. It provides explicit checks that
    callers should use prior to performing side-effecting operations.
    """

    def __init__(self, policy: SandboxPolicy) -> None:
        self._policy = policy

    @property
    def policy(self) -> SandboxPolicy:
        return self._policy

    def assert_path_within_project(self, path: Path) -> None:
        try:
            path.resolve().relative_to(self._policy.project_root.resolve())
        except Exception as exc:  # Path is outside project
            raise SandboxViolation(
                f"Path '{path}' escapes project root '{self._policy.project_root}'"
            ) from exc

    def assert_read_allowed(self, path: Path) -> None:
        self.assert_path_within_project(path)
        # FULL and LIMITED both allow reads within the project
        # (Additional per-path rules go elsewhere)

    def assert_write_allowed(self, path: Path) -> None:
        self.assert_path_within_project(path)
        if self._policy.mode is SandboxMode.FULL:
            raise SandboxViolation("Writes are disallowed in FULL sandbox mode")
        if not self._policy.allows_writes:
            raise SandboxViolation(
                "This use case does not allow writes (capability is disabled)"
            )
        if not self._policy.user_write_consent:
            raise SandboxViolation(
                "User has not granted write consent for this run"
            )

    def assert_subprocess_disallowed(self) -> None:
        raise SandboxViolation("Subprocess execution is disallowed by sandbox policy")

    def assert_vcs_disallowed(self) -> None:
        raise SandboxViolation("VCS interaction is disallowed by sandbox policy")
