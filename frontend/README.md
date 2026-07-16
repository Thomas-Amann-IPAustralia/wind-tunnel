# frontend/ — React/Vite SPA (deployed to GitHub Pages)

The whole UI: the **Console** (light, where you build and review) and the
**Chamber** (dark, where you watch the governance run) of `DESIGN_BRIEF.md`. Talks
to the Render backend and polls run `status.json` to animate the pipeline and
detect the two user pauses (threshold review, question checkpoint).

**Governs:** DESIGN_BRIEF.md (interface, transparency animation, report);
TECH_SPEC.md §6 (`status.json` the animation consumes), §7 (API contract).

## Run it

```bash
npm install
npm run dev        # vite dev server on :5173, talks to a local backend on :8000
```

Point the SPA at a backend with `VITE_BACKEND_URL` (defaults to
`http://localhost:8000` for `npm run dev`):

```bash
VITE_BACKEND_URL=https://your-backend.onrender.com npm run build
```

## Checks

```bash
npm run build         # tsc -b (strict) + vite production build
npm run lint          # eslint
npm run format:check  # prettier
npm test              # vitest (run-code mirror + app-render smoke)
```

## Conventions (CLAUDE.md §4)

- **TypeScript**, React + Vite. ESLint + Prettier.
- **No CSS framework.** The design brief's type/token system (design §3) is
  implemented as CSS custom properties in `src/styles/tokens.css`; components read
  the tokens, never hard-code a hex or a family.
- **One poll fully determines visible state.** The frontend may miss polls and
  must still render correctly (TECH_SPEC §6) — `getStatus` in `src/lib/api.ts` is
  built for whole-graph payloads with stable event ids.

## Layout

- `src/config.ts` — deployment identity, mirrored by hand from `backend/config.py`
  (CLAUDE.md §6). Kept in sync with Vite's `base` (`/wind-tunnel/`).
- `src/lib/runCode.ts` — the one unavoidable TS copy of `pipeline/runcode.py`
  (CLAUDE.md §6); pinned to the Python owner by `runCode.test.ts`.
- `src/lib/api.ts` — the typed backend client (§7), incl. the honest Render
  cold-start warm-up (design §5).
- `src/lib/types.ts` — the wire shapes the backend returns / writes to
  `status.json` (design §7.2.6, pipeline/status.py §6).
- `src/components/` — the shared design-system pieces: the usage-warning gate
  (§4), standing disclaimer (§4.2), run-code chip (§7.5), the Console/Chamber
  surfaces (§3.4), and the Brainstorm focus track (§6.1).
- `src/routes/` — Landing (§5), Resume (§7.5), and the Brainstorm (§6) / Chamber
  (§7) shells the next phase fills in.

## Deploy-layer facts (CLAUDE.md §9)

- **Path-aware:** GitHub Pages project sites serve from `/<repo>/`, so Vite `base`
  is `/wind-tunnel/` and routing is **hash-based** (Pages has no server-side
  rewrites).
- Deployment identity the SPA needs — backend base URL, repo `owner/name`,
  run-code alphabet — lives in the one committed typed config `src/config.ts`,
  *not* hardcoded across files. One owner per fact.
- `.github/workflows/pages.yml` (path-filtered to `frontend/**`) builds and
  deploys this. The production backend URL comes from the `WINDTUNNEL_BACKEND_URL`
  repo variable at build time.
- **Mermaid → SVG renders client-side here** (`mermaid.js`), then the SVG is
  posted back for commit — `mermaid-cli` is a poor fit for Render's 512MB tier.
  (The generator backend + `POST /flow-map/svg` are built; the in-browser render
  lands with the Brainstorm canvas — next phase.)
