// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Brainstorm } from "./Brainstorm";

// The Brainstorm canvas over a mocked backend (no network): loading the co-design
// state, one interview turn resolving a section, and Submit handing off to the
// Chamber. The real api module's error classes are preserved so the screen's
// NetworkError/ApiError handling still type-checks and runs.
vi.mock("../lib/api", async (importActual) => {
  const actual = await importActual<typeof import("../lib/api")>();
  return {
    ...actual,
    getBrainstorm: vi.fn(),
    brainstormMessage: vi.fn(),
    editOutline: vi.fn(),
    submitRun: vi.fn(),
  };
});

import { brainstormMessage, getBrainstorm, submitRun } from "../lib/api";

const CODE = "WT-ABCD-EF";

function outlineMd(resolved: string[], bodies: Record<string, string> = {}): string {
  const sections: Array<[string, number, string]> = [
    ["problem", 1, "Problem"],
    ["solution", 2, "Proposed solution"],
    ["users_stakeholders", 3, "Users and stakeholders"],
    ["data", 4, "Data"],
    ["happy_path", 5, "Happy path"],
    ["alternatives", 6, "Alternatives considered"],
    ["ux_ui", 7, "UX and interface"],
    ["constraints", 8, "Constraints and preferences"],
    ["success_criteria", 9, "Success criteria"],
  ];
  const body = sections
    .map(
      ([id, n, title]) =>
        `<!-- section: ${id} -->\n## ${n}. ${title}\n\n${bodies[id] ?? `*guidance for ${id}*`}\n`,
    )
    .join("\n");
  return `---\nschema_version: 1\ntitle: "Idea"\nsummary: "A summary."\nresolved: ${JSON.stringify(
    resolved,
  )}\n---\n\n${body}`;
}

function renderBrainstorm() {
  return render(
    <MemoryRouter initialEntries={[`/run/${CODE}/brainstorm`]}>
      <Routes>
        <Route path="/run/:code/brainstorm" element={<Brainstorm />} />
        <Route path="/run/:code/chamber" element={<div>THE CHAMBER</div>} />
        <Route path="/" element={<div>HOME</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(getBrainstorm).mockReset();
  vi.mocked(brainstormMessage).mockReset();
  vi.mocked(submitRun).mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("Brainstorm canvas", () => {
  it("loads and renders the outline with resolved bodies and the sufficiency banner", async () => {
    vi.mocked(getBrainstorm).mockResolvedValue({
      outline_md: outlineMd(["problem"], { problem: "Citizens wait too long." }),
      transcript: [{ role: "assistant", text: "What data does it touch?", ts: "t" }],
      sufficiency: { ready: false, missing: [{ section_id: "data", reason: "unresolved" }] },
      stage: "BRAINSTORM",
    });

    renderBrainstorm();

    expect(await screen.findByText("Citizens wait too long.")).toBeTruthy();
    // The prior interviewer turn is restored from the transcript.
    expect(screen.getByText("What data does it touch?")).toBeTruthy();
    // 1 of 9 resolved is shown, and the banner nudges the still-open areas.
    expect(screen.getByText(/1 \/ 9 sections/)).toBeTruthy();
    expect(screen.getByText(/would sharpen the assessment/i)).toBeTruthy();
  });

  it("sends a message and folds the reply + newly-resolved section into the canvas", async () => {
    vi.mocked(getBrainstorm).mockResolvedValue({
      outline_md: outlineMd([]),
      transcript: [],
      sufficiency: { ready: false, missing: [] },
      stage: "BRAINSTORM",
    });
    vi.mocked(brainstormMessage).mockResolvedValue({
      assistant_message: "Got it — who are the users?",
      outline_md: outlineMd(["problem"], { problem: "People wait too long." }),
      outline_delta: { updated: ["problem"], newly_resolved: ["problem"], title_changed: false },
      sufficiency: { ready: false, missing: [] },
      stage: "BRAINSTORM",
    });

    renderBrainstorm();
    // Wait for load: the empty-state invitation is present.
    await screen.findByText(/describe your idea in your own words/i);

    fireEvent.change(screen.getByLabelText(/your message/i), {
      target: { value: "People wait too long for replies." },
    });
    fireEvent.click(screen.getByRole("button", { name: /^send$/i }));

    expect(await screen.findByText("Got it — who are the users?")).toBeTruthy();
    expect(screen.getByText("People wait too long.")).toBeTruthy();
    expect(screen.getByText(/1 \/ 9 sections/)).toBeTruthy();
    expect(vi.mocked(brainstormMessage)).toHaveBeenCalledWith(
      CODE,
      "People wait too long for replies.",
    );
  });

  it("submits the run and hands off to the Chamber", async () => {
    vi.mocked(getBrainstorm).mockResolvedValue({
      outline_md: outlineMd(["problem"], { problem: "A resolved problem." }),
      transcript: [],
      sufficiency: { ready: true, missing: [] },
      stage: "BRAINSTORM",
    });
    vi.mocked(submitRun).mockResolvedValue({ run_id: CODE, dispatched: true });

    renderBrainstorm();
    // The ready banner appears once loaded.
    expect(await screen.findByText(/ready to test/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /submit for assessment/i }));

    expect(await screen.findByText("THE CHAMBER")).toBeTruthy();
    expect(vi.mocked(submitRun)).toHaveBeenCalledWith(CODE);
  });

  it("redirects a submitted run on to the Chamber", async () => {
    vi.mocked(getBrainstorm).mockResolvedValue({
      outline_md: outlineMd(["problem"]),
      transcript: [],
      sufficiency: null,
      stage: "THRESHOLD_DRAFTING",
    });

    renderBrainstorm();
    expect(await screen.findByText("THE CHAMBER")).toBeTruthy();
  });
});
