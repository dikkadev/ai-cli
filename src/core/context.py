from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .blacklist import Blacklist


@dataclass
class ContextCaps:
    max_files: int = 200
    max_total_bytes: int = 5 * 1024 * 1024  # 5 MiB
    max_file_bytes: int = 512 * 1024  # 512 KiB


TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".ts", ".tsx", ".js", ".json", ".toml", ".yaml", ".yml",
    ".go", ".rs", ".java", ".kt", ".sh", ".bash", ".zsh", ".sql",
}


def looks_binary(path: Path) -> bool:
    # Heuristic: extension or initial bytes check
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        try:
            with path.open("rb") as f:
                head = f.read(4000)
            if b"\0" in head:
                return True
        except Exception:
            return True
    return False


@dataclass
class IngestResult:
    included: list[Path]
    skipped: list[Path]
    total_bytes: int


def collect_paths(
    roots: Iterable[Path],
    blacklist: Blacklist,
    caps: ContextCaps | None = None,
) -> IngestResult:
    caps = caps or ContextCaps()
    included: list[Path] = []
    skipped: list[Path] = []
    total = 0

    for root in roots:
        root = root if root.is_absolute() else Path.cwd() / root
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates = [p for p in root.rglob("*") if p.is_file()]
        else:
            skipped.append(root)
            continue

        for p in candidates:
            if blacklist.is_blocked(p):
                skipped.append(p)
                continue
            if looks_binary(p):
                skipped.append(p)
                continue
            try:
                size = p.stat().st_size
            except Exception:
                skipped.append(p)
                continue
            if size > caps.max_file_bytes:
                skipped.append(p)
                continue
            if total + size > caps.max_total_bytes:
                skipped.append(p)
                continue
            included.append(p)
            total += size
            if len(included) >= caps.max_files:
                break

    return IngestResult(included=included, skipped=skipped, total_bytes=total)
