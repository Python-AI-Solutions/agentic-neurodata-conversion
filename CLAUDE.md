# Agent Working Agreement (Claude)

**Scope & Precedence**

- This file guides how you (the agent) operate in this repository.
- Overview and non-negotiable guidance is in .specify/memory/constitution.md. If
  any instruction here conflicts with `.specify/memory/constitution.md`, the
  **constitution wins**.
- You must follow the Spec Kit workflow and quality gates defined by the
  constitution.

---

## Rules

1. **Pixi‑only**
   - All commands not available on the shell MUST be run via `pixi`:
     `pixi run <task>` or `pixi <subcommand>`. pixi tasks can be used for all
     development related tasks. If too extensive the task can just run a python
     script stored in the scripts directory.
   - Do NOT use `pip`, `conda`, `venv`, `python -m pip`, system Python, or
     `PYTHONPATH` hacks.
   - Run scripts through pixi which can add custom dependencies to the script:
     `pixi run python your_script.py`

2. **No stray scripts or root‑level files**
   - Do NOT create or delete ad‑hoc scripts (e.g., `tmp.py`, `run.py`,
     `one_off.sh`) any outside scripts/temp. Use scripts if they have long-term
     use potential.
   - Try to avoid adding files to the repository root. Only modify allowed
     locations (see “Filesystem Rules”).

3. **Follow the constitution’s engineering model**
   - MCP‑centric orchestration (no direct module‑to‑module calls).
   - TDD with coverage gates; schema‑first (LinkML/NWB); DataLad Python API
     only.
   - Contract tests on OpenAPI interfaces; CI quality gates must pass before
     merge.

4. **Pre‑commit is the gatekeeper**
   - Every change must pass: `pixi run pre-commit run --all-files`.
   - Fix formatting/linting locally (`pixi run format`, `pixi run lint`) then
     re‑run pre‑commit.

5. **Do not guess; fail fast with a crisp request**
   - If a step would violate the constitution or these rules, STOP and write a
     short blocking note with the minimal change you need approved i.e. how to
     resolve an apparent conflict between the instruction and the constitution.

6. **Command quoting** for inline Python:
   - Shell: single quotes outside, double quotes inside:
     `pixi run python -c 'print("ok")'`
   - Prefer tasks in `pixi.toml` or formal tests over complex `python -c`
     snippets.

7. **Data handling**:
   - DataLad is installed as a Python package through pixi

- **DO NOT** use `datalad` CLI commands directly
- **DO NOT** use `pixi run datalad` or `pixi run python -m datalad` for CLI
- **ALWAYS** use the Python API (likely using scripts):
- Example usage:

  ```python
  import datalad.api as dl

  # Create a dataset
  dl.create(path="my-dataset", description="My dataset")

  # Save changes
  dl.save(message="Add files")

  # Check status
  dl.status()

  # Work with subdatasets
  dl.subdatasets()
  ```

- **Use Cases**:
  - Managing large NWB datasets from DANDI
  - Handling pre-existing conversions as submodules
  - Version control for evaluation datasets
  - Efficient storage of large test datasets on remote annexes (gin.g-node.org)

## Filesystem Rules (Strict)

**Allowed to modify or create:**

- `src/**` – implementation
- `tests/**` – unit/integration/e2e tests
- `docs/**` – documentation (adhoc summaries should go in git ignored docs/temp
  to reduce noise)
- `.specify/**` – Spec Kit memory and related artifacts
- `.pre-commit-config.yaml` – quality configuration
