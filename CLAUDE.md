# Agent Working Agreement (Claude)

**Scope & Precedence**

- This file guides how you (the agent) operate in this repository.
- Overview and non-negotiable guidance is in .specify/memory/constitution.md. If
  any instruction here conflicts with `.specify/memory/constitution.md`, the
  **constitution wins**.
- You must follow the Spec Kit workflow and quality gates defined by the
  constitution.
- Technical standards are summarized in docs/shared-technical-standards.md. Any
  modification of this should be documented in docs/architecture. This should be
  consulted for any extensive tasks that require design/architecture or
  extensive coding.

---

## Rules

1. **No stray scripts or root‑level files**
   - Do NOT create or delete ad‑hoc scripts (e.g., `tmp.py`, `run.py`,
     `one_off.sh`) any outside scripts/temp. Use scripts if they have long-term
     use potential.
   - Try to avoid adding files to the repository root. Only modify allowed
     locations (see “Filesystem Rules”).

2. **Follow the constitution's engineering model**
   - MCP‑centric orchestration (no direct module‑to‑module calls).
   - TDD with coverage gates; Pydantic models first for validation.
   - Contract tests on OpenAPI interfaces; CI quality gates must pass before
     merge.

3. **Pre‑commit is the gatekeeper**
   - Every change must pass: `pixi run pre-commit run --all-files`.
   - Fix formatting/linting locally (`pixi run format`, `pixi run lint`) then
     re‑run pre‑commit.

4. **Do not guess; fail fast with a crisp request**
   - If a step would violate the constitution or these rules, STOP and write a
     short blocking note with the minimal change you need approved i.e. how to
     resolve an apparent conflict between the instruction and the constitution.

5. **Command quoting** for inline Python:
   - Shell: single quotes outside, double quotes inside:
     `pixi run python -c 'print("ok")'`
   - Prefer tasks in `pixi.toml` or formal tests over complex `python -c`
     snippets.

6. **Session Context Management**:
   - All workflow state is persisted in session context (Redis + filesystem)
   - Session context survives server restarts (write-through strategy)
   - Use context manager for all session CRUD operations
   - Never store sensitive data (API keys, credentials) in context

## Filesystem Rules (Strict)

**Allowed to modify or create:**

- `src/**` – implementation
- `tests/**` – unit/integration/e2e tests
- `docs/**` – documentation (adhoc summaries should go in git ignored docs/temp
  to reduce noise)
- `.specify/**` – Spec Kit memory and related artifacts
- `.pre-commit-config.yaml` – quality configuration
