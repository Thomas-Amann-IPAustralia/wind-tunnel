# .github/workflows/ — CI + pipeline workflows

**Governs:** TECH_SPEC.md §2, §5 (governance), §8 (ingestion); CLAUDE.md §9 (deploy layer).

Expected workflows:

| Workflow | Trigger | Role |
| --- | --- | --- |
| `governance.yml` | `workflow_dispatch` (from the backend) | Runs the Governance pipeline; commits run state with the built-in `GITHUB_TOKEN` (no PAT needed inside Actions). |
| `ingestion.yml` | manual / push to `corpus/**` | Builds the specialist KBs into `kb/`. |
| `pages.yml` | push, **path-filtered to `frontend/**`** | Deploys the SPA to GitHub Pages. *Not in the tech-spec workflow list — add it (CLAUDE.md §9); path-filter it or every status-commit during a run triggers a needless frontend redeploy.* |

## Notes (CLAUDE.md §9)

- The pipeline commits to the repo every ~20s during a run. Keep workflow triggers **path-filtered** so unrelated jobs don't fire on every status commit.
- Report diagrams in Actions may use `mermaid-cli` (Chromium is available there); the SPA renders flow maps in-browser instead.
- `GEMINI_API_KEY` is a GitHub Actions secret; never commit it.
