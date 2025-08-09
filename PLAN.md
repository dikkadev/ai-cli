# Plan of Work (estimates)

Estimates assume focused solo work; adjust as needed. Each phase ships incremental value.

## Phase 0 - Repo init and scaffolding (0.5–1 day)
- Initialize Python project with `uv` (pyproject, lockfile, scripts).
- Add basic structure (no implementations):
  - `ai_cli/cli.py` (Typer app stub)
  - `ai_cli/core/` (`sandbox.py`, `context.py`, `blacklist.py`, `models.py`)
  - `ai_cli/llm/` (`provider.py`, `openai_provider.py` stub)
  - `ai_cli/usecases/` (`ask.py`, `task.py`, `testwrite.py` stubs)
  - `ai_cli/utils/` (`render.py`, `fs.py`)
- Add `DECISIONS.md`, `PLAN.md`, and a minimal `README.md`.

## Phase 1 - Core contracts and UI skeleton (1–1.5 days)
- Implement `SandboxMode` enum and enforcement shim.
- Implement use case decorator + loader; `InputModel`/`OutputModel` base types.
- Implement blacklist module with strict defaults and targeted ignore mechanism.
- Implement context ingestion skeleton (paths, stdin; caps; binary skip; redaction switch only).
- Rich-based pretty renderer prototype: header, context summary, and a placeholder result panel.
- Typer wiring: auto-generate commands from discovered use cases (no flags finalized yet).

## Phase 2 - Provider adapter and structured outputs (1–1.5 days)
- Define provider interface for structured outputs (Pydantic models to JSON Schema).
- Implement OpenAI provider via structured outputs (non-streaming first).
- Add retries, timeouts, and minimal error mapping.
- Add a small validation loop (model -> schema -> validate -> fallbacks).

## Phase 3 - Use case MVPs (read-only first) (1.5–2 days)
- `ask`: implement execution path (no writes), context inclusion, pretty rendering of answer and sources.
- `task`: produce a structured plan skeleton (no doing yet), render numbered steps.
- `testwrite`: compute proposed changes only; show compact diffs; writing is disabled initially.

## Phase 4 - Write pathway (capability + consent) (1–1.5 days)
- Central consent-to-write mechanism (top-level control), enforced with sandbox and `allows_writes`.
- Enable `testwrite` to write files when capability + consent conditions are met.
- Effects summary footer and guardrails.

## Phase 5 - Hardening and polish (1–2 days)
- Error taxonomy and exit codes.
- Redaction defaults and a minimal heuristic secret scanner.
- Pretty-mode refinements (colors, widths, truncation and expanders for long lists/diffs).
- Basic docs: quickstart, safety notes, and use case authoring guide.

## Phase 6 - Optional enhancements (as needed)
- Streaming render for `ask`.
- Planner swap interface and an optional DSPy-backed planner for `task`.
- Config file `ai.toml` and env vars.
- Tests: unit (contracts), golden tests for renderers, e2e smoke.

---

## Milestones
- M1 (end Phase 2, ~3 days): CLI skeleton with pretty output; structured outputs wired; use case stubs.
- M2 (end Phase 3, ~5 days): `ask` usable; `task` returns a structured plan; `testwrite` shows proposed changes.
- M3 (end Phase 4, ~6–6.5 days): controlled writes enabled for `testwrite`; safety enforced.
- M4 (end Phase 5, ~7.5–9.5 days): hardened UX, docs, and safety.

Notes
- Keep non-interactive by default; add interactivity later only if needed.
- No VCS integration; no retrieval/embeddings in v0.
- "No sandbox" mode deferred.
