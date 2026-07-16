// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Chamber } from "./Chamber";
import type { StatusDoc } from "../lib/types";

// The Chamber over a mocked backend (no network, no polling to a real server): the
// one status poll fully determines which face shows (design §7.2 / CLAUDE.md §3).
// Each test drives a different overall_state and asserts the right screen renders.
vi.mock("../lib/api", async (importActual) => {
  const actual = await importActual<typeof import("../lib/api")>();
  return { ...actual, getStatus: vi.fn(), fetchArtefactText: vi.fn() };
});

import { fetchArtefactText, getStatus } from "../lib/api";

const CODE = "WT-ABCD-EF";

function baseDoc(overrides: Partial<StatusDoc>): StatusDoc {
  return {
    schema_version: 1,
    run_id: CODE,
    run_code: CODE,
    phase: "threshold",
    overall_state: "running",
    updated_at: "2026-07-16T00:00:00Z",
    nodes: {},
    log: [],
    questions: null,
    failure: null,
    expected_ranges: { threshold: [300, 600], full: [600, 1800] },
    ...overrides,
  };
}

function serve(doc: StatusDoc) {
  vi.mocked(getStatus).mockResolvedValue({ notModified: false, doc, etag: null });
}

function renderChamber() {
  return render(
    <MemoryRouter initialEntries={[`/run/${CODE}/chamber`]}>
      <Routes>
        <Route path="/run/:code/chamber" element={<Chamber />} />
        <Route path="/" element={<div>HOME</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(getStatus).mockReset();
  vi.mocked(fetchArtefactText).mockReset();
});
afterEach(() => vi.clearAllMocks());

describe("Chamber state routing", () => {
  it("running: shows the pipeline graph and the activity log", async () => {
    serve(
      baseDoc({
        overall_state: "running",
        nodes: { "threshold.generalist_a": "active", "threshold.reconciler": "pending" },
        log: [
          {
            id: "evt_1",
            ts: "2026-07-16T00:00:01Z",
            agent: "threshold.generalist_a",
            type: "retrieval",
            detail: "reading OAIC PIA guidance, p.14",
          },
        ],
      }),
    );
    renderChamber();
    // The graph names the node, and the log names it too (agent → friendly) — the
    // log mirrors the graph, so the name appears in both places.
    expect((await screen.findAllByText("Assessor A")).length).toBeGreaterThanOrEqual(2);
    // The detail appears twice: as the active node's genuine sub-activity in the
    // graph, and as a line in the log (no event exists only in the graph, §7.2.1).
    const subs = screen.getAllByText(/reading OAIC PIA guidance/);
    expect(subs.length).toBeGreaterThanOrEqual(2);
  });

  it("paused with no questions: shows the threshold review screen", async () => {
    vi.mocked(fetchArtefactText).mockResolvedValue(
      "## 3. Inherent risk\n\n| Area | Consequence | Likelihood | Risk rating |\n| --- | --- | --- | --- |\n| 3.5 Privacy | Major | Possible | High |\n",
    );
    serve(baseDoc({ overall_state: "paused", questions: null }));
    renderChamber();
    expect(await screen.findByRole("button", { name: /run the full assessment/i })).toBeTruthy();
    expect(await screen.findByText("High")).toBeTruthy(); // the computed risk chip
    expect(screen.getByRole("button", { name: /conclude here/i })).toBeTruthy();
  });

  it("paused with questions: shows the checkpoint UI grouped by specialist", async () => {
    serve(
      baseDoc({
        phase: "full",
        overall_state: "paused",
        nodes: { "full.checkpoint": "waiting_user" },
        questions: {
          batch_id: "q-1",
          specialists: [
            {
              node_id: "full.specialist.privacy",
              friendly: "Privacy specialist",
              why: "Asking so the privacy risk rests on fact.",
              items: [
                {
                  question_id: "q1",
                  text: "Does the solution store personal information?",
                  options: ["It doesn't", "On-prem", "Cloud"],
                },
              ],
            },
          ],
          counts: { total: 1, answered: 0, skipped: 0 },
        },
      }),
    );
    renderChamber();
    expect(await screen.findByText("Privacy specialist")).toBeTruthy();
    expect(screen.getByText(/Does the solution store personal information/)).toBeTruthy();
    expect(screen.getByText(/Skip this — note it as a gap/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /resume the run/i })).toBeTruthy();
  });

  it("failed: shows the calm, resumable failure state with the run code", async () => {
    serve(
      baseDoc({
        phase: "full",
        overall_state: "failed",
        nodes: { "full.specialist.privacy": "failed" },
        failure: {
          stage: "full.specialist.privacy",
          message: "The run stopped at the specialist stage.",
          run_code: CODE,
          technical: "GeminiTransport: 503",
        },
      }),
    );
    renderChamber();
    expect(await screen.findByText(/your progress is saved/i)).toBeTruthy();
    expect(screen.getByText(/The run stopped at the specialist stage/)).toBeTruthy();
    // Technical detail is available but collapsed by default (§7.2.4).
    expect(screen.getByRole("button", { name: /show technical detail/i })).toBeTruthy();
    expect(screen.queryByText(/GeminiTransport: 503/)).toBeNull();
  });

  it("complete (full): shows the report with the revision affordance", async () => {
    serve(baseDoc({ phase: "full", overall_state: "complete" }));
    renderChamber();
    expect(await screen.findByTitle(/draft impact assessment report/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /request a revision/i })).toBeTruthy();
  });

  it("complete (threshold): shows the concluded view, not the full report", async () => {
    serve(baseDoc({ phase: "threshold", overall_state: "complete" }));
    renderChamber();
    expect(await screen.findByText(/threshold assessment is complete/i)).toBeTruthy();
    expect(screen.queryByTitle(/draft impact assessment report/i)).toBeNull();
  });
});
