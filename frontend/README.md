# frontend/ — React/Vite SPA (deployed to GitHub Pages)

The whole UI. Talks to the Render backend and polls run `status.json` to
animate the pipeline and detect the two user pauses (threshold review, question
checkpoint).

**Governs:** DESIGN_BRIEF.md (interface, transparency animation, report);
TECH_SPEC.md §6 (`status.json` the animation consumes), §7 (API contract).

## Conventions (CLAUDE.md §4)

- **TypeScript**, React + Vite. ESLint + Prettier.
- **No CSS framework.** Implement the design brief's type/token system (design §3) as CSS custom properties; don't reach for a component kit that fights them.
- **One poll fully determines visible state.** The frontend may miss polls and must still render correctly (TECH_SPEC §6).

## Deploy-layer facts (CLAUDE.md §9)

- **Path-aware:** GitHub Pages project sites serve from `/<repo>/`, so Vite `base` is set accordingly and routing is **hash-based**.
- Deployment identity the SPA needs — backend base URL, repo `owner/name`, run-code alphabet — lives in **one committed typed config** (e.g. `frontend/config.ts`), *not* hardcoded across files. One owner per fact.
- A path-filtered `.github/workflows/pages.yml` (filter `frontend/**`) deploys this; add it when the SPA is scaffolded.
- **Mermaid → SVG renders client-side here** (`mermaid.js`), then the SVG is posted back for commit — `mermaid-cli` is a poor fit for Render's 512MB tier.
