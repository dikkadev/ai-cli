# Decisions

This document captures the current decisions we agreed on. It will evolve; anything not listed here is undecided or deferred.

## Scope and use cases
- Initial use cases: `ask`, `task`, `testwrite` (names locked).
- `task` will eventually plan and do, but detailed behavior is deferred.
- This tool is not a general-purpose “agent suite.” Keep scope tight and predictable.

## Architecture and libraries
- Language/runtime: Python 3.11+; dependency management via `uv`.
- CLI framework: Typer (Click-based) with non-interactive defaults.
- Output/UI: Rich for pretty output (colors, panels, markdown, syntax highlight). No emoji by default.
- No Textual/TUI for now. No Ink (JS-only).
- Data modeling: Pydantic v2 for typed inputs/outputs and JSON-schema generation.
- Model provider: OpenAI structured outputs adapter behind an internal interface. Provider details/flags deferred.
- DSPy: optional, per-use case only (see below). Not required globally.

## DSPy policy
- Do not couple the core system to DSPy.
- If/when useful (likely for `task` planning), add a DSPy-backed planner behind an adapter. Otherwise stick to a lightweight orchestrator.

## Use case contract (high-level)
- Declaration style: decorator + class with attributes and nested Pydantic models.
- Required pieces per use case:
  - `id: str`, `summary: str`
  - `sandbox: SandboxMode` (enum, see below)
  - `allows_writes: bool` (capability declaration only)
  - `InputModel: pydantic.BaseModel` (defines CLI options/args; supports bool and enum fields)
  - `OutputModel: pydantic.BaseModel` (structured outputs)
  - `execute(input: InputModel, ctx: Context) -> OutputModel`
- The CLI wiring will be auto-generated from `InputModel`. Exact flag shapes are deferred.

## Sandboxing and writes
- Sandboxing is a first-class, centrally enforced policy. Enum, not strings:

```python
from enum import Enum

class SandboxMode(Enum):
    FULL = "full"      # project dir visible, read-only; no subprocess; no VCS
    LIMITED = "limited"  # project dir visible; writes allowed only if use case allows AND user consents
```

- Each use case sets `sandbox` and `allows_writes`.
- User consent to write will be a top-level control later; details deferred. Consent is necessary but not sufficient (use case must also allow).
- "No sandbox" is explicitly deferred (not implemented now).
- Regardless of mode: no VCS access and no shell/subprocess in v0.

## Context handling
- Explicit only. No VCS sources. No retrieval/embeddings/indexing in v0.
- Use cases may declare preferred default context elements (concept only; details deferred). Users can override/augment later via CLI (also deferred).
- Context ingestion applies strict caps (max bytes/files/per-file size) and binary skipping by default.
- Redaction on by default.

## Blacklist policy
- A global blacklist is always applied (e.g., secrets, `.env*`, keys, `.git`, `.jj`, `.venv`, `node_modules`, build/caches, large/binary files).
- There is no hard global opt-out. Only targeted exceptions via a pattern-level ignore mechanism (name TBD, e.g., `--blacklist-ignore PATTERN`).

## UI/UX (pretty mode)
- Minimal, clean aesthetic; readable in narrow terminals; no emoji.
- Components:
  - Compact header with use case name, sandbox badge, model name, elapsed.
  - Context summary: included/skipped counts, redaction indicator, top sources preview.
  - Main content:
    - `ask`: render markdown answer with syntax highlighting for code blocks.
    - `task`: numbered steps with short titles and dimmed rationale (details deferred).
    - `testwrite`: compact list of proposed changes; focused single-file diff view (writes require consent+capability).
  - Progress: unobtrusive spinner for network calls.
  - Footer: effects summary (“no files changed” unless both capability and consent are true).
- CLI flag surface and output formats are intentionally deferred until we tackle the CLI spec.

## Safety and side effects
- Default posture is read-only. Side effects require both capability (use case) and explicit user consent (top-level control, deferred design).
- No automatic external commands, no VCS operations, no shell execution in v0.
- Caching, if any, is local and scoped (directory TBD, likely `.ai/`).

## Out of scope for v0
- VCS integration (read or write).
- Retrieval/embeddings or vector indexes.
- Textual/TUI.
- DSPy as a core dependency.

## Deferred topics / open questions
- Exact CLI flag surface (global and per-use case) and config file (`ai.toml`).
- Concrete context element schema and defaults per use case.
- Provider selection/flags and advanced telemetry.
- “No sandbox” mode semantics and safeguards.


