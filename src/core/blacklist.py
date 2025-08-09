from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_BLACKLIST: tuple[str, ...] = (
    # VCS / tooling
    ".git/", ".jj/", ".hg/", ".svn/", ".idea/", ".vscode/",
    # env / deps / builds
    ".venv/", "venv/", "node_modules/", "dist/", "build/", "__pycache__/",
    # secrets and env
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "id_*",
    # large/binary-ish common patterns
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.mp4", "*.mov", "*.zip", "*.tar", "*.gz",
)


@dataclass(slots=True)
class Blacklist:
    patterns: Sequence[str] = field(default_factory=lambda: list(DEFAULT_BLACKLIST))
    extra_ignores: Sequence[str] = field(default_factory=list)

    def is_blocked(self, path: Path) -> bool:
        normalized = self._normalize(path)
        for pattern in self.patterns:
            if self._match(normalized, pattern):
                # Allow targeted exceptions
                for ignore in self.extra_ignores:
                    if self._match(normalized, ignore):
                        return False
                return True
        return False

    def filter_paths(self, paths: Iterable[Path]) -> list[Path]:
        return [p for p in paths if not self.is_blocked(p)]

    @staticmethod
    def _normalize(path: Path) -> str:
        # Represent as posix-style relative string for fnmatch
        return path.as_posix()

    @staticmethod
    def _match(candidate: str, pattern: str) -> bool:
        # Support directory suffix slash semantics; fnmatch works on strings
        if candidate.endswith("/") or pattern.endswith("/"):
            candidate = candidate.rstrip("/") + "/"
            pattern = pattern.rstrip("/") + "/"
        return fnmatch(candidate, pattern)
