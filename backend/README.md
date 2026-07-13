# backend/ — Brainstorm backend (FastAPI, deployed to Render)

Runs the interactive **Brainstorm** phase with live Gemini calls, issues run
codes, commits brainstorm state to the repo, triggers Governance runs, and
proxies status + artefact downloads for the SPA.

**Governs:** TECH_SPEC.md §7 (API contract), §7.1 (outline contract),
§5.7 & §14 (dispatch + commit helper). Brainstorm behaviour: PROJECT_BRIEF.md §4;
DESIGN_BRIEF.md §6.

## Expected modules (TECH_SPEC §2)

| File | Role |
| --- | --- |
| `app.py` | FastAPI endpoints (§7) |
| `brainstorm/` | interviewer, sufficiency, poc, map, feasibility gate |
| `github_io.py` | commit helper: Contents/Git-Data API, serialise-per-run, retry on non-fast-forward (§14) |
| `dispatch.py` | `workflow_dispatch` trigger + handshake (§5.7, §14) |

## Load-bearing constraints

- **Sole holder of `GEMINI_API_KEY` and `WINDTUNNEL_PAT`** — neither ever reaches the SPA (CLAUDE.md §6).
- **Commits via the GitHub Contents / Git Data API, not a working-copy `git push`** — Render's disk is ephemeral (CLAUDE.md §9).
- **Render auto-deploy is OFF or watch-path-scoped to `backend/**`** — the pipeline commits every ~20s during a run and would otherwise evict in-memory brainstorm sessions (CLAUDE.md §9).

Python 3.11, `uv`, ruff, pytest — see `pyproject.toml`.
