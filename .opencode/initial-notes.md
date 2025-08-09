Project: AI CLI — discovery notes

Repo state
- Only `project.md` exists; no code yet.

Intent from `project.md`
- Python CLI named `ai` with subcommands as first-class "use cases" (e.g., `ask`, `task`).
- Prefer latest structured outputs (OpenAI GPT-5 family noted as changing). DSPy suggested as base.
- "ask": Q&A with optional context, no side effects.
- "task": take a task, create a structured TODO/plan, and follow through.

Early architecture thoughts
- Language: Python with `uv` for dependency and virtualenv mgmt; Typer for CLI; Pydantic v2 for typed/JSON-schema I/O; Rich/typer-rich for UX.
- Provider abstraction: wrap OpenAI Responses API structured outputs; design for future providers; prefer JSON Schema + Pydantic models.
- Usecase plugin system: dynamic discovery of modules under `ai_cli/usecases/` exporting `register(app: Typer)`; metadata for help/registry.
- RAG layer optional: local file/directory/repo context with simple BM25/faiss + chunking; leave vector DB optional and lazy.
- State: `.ai/` folder for runs, caches, and `task` state; avoid side effects by default; require flags to write.

Open questions
- Depth of DSPy integration vs. lightweight wrappers; DSPy compilers (e.g., MIPROv2) might overkill for MVP.
- Exact GPT-5 Responses/structured output API surface; design adapter to isolate changes.
- jj integration policy: generate messages/commands vs. executing jj.

Proposed MVP
- `ai ask` with optional `--ctx` sources; `ai task` that outputs a structured plan JSON and optional steps.
- Provider adapter + simple retry/validation loop for structured outputs.


