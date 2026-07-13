# fixtures/ — Golden-path project + hand-worked rating cases

**Governs:** TECH_SPEC.md §15 (testing).

- A **golden-path project** to drive the pipeline end-to-end in tests.
- **Hand-worked rating cases** — the non-negotiable test target for `pipeline/rating/`. The Stage 2 exit test is that threshold output for a known test case matches a hand-worked assessment's ratings **exactly** (PROJECT_BRIEF.md §9).

Keep these deterministic and independent of any live LLM call.
