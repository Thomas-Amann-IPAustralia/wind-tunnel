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
    generatePoc: vi.fn(),
    generateFlowMap: vi.fn(),
    postFlowMapSvg: vi.fn(),
    fetchArtefactText: vi.fn(),
    uploadBrainstormFile: vi.fn(),
  };
});

// mermaid.js can't lay out an SVG in jsdom; the wrapper is mocked to a stable stub so
// the canvas's render-and-post flow is exercised without the real engine. The route
// dynamic-imports this module, which vi.mock intercepts too.
vi.mock("../lib/mermaid", () => ({
  renderMermaid: vi.fn(async (src: string) => `<svg data-len="${src.length}"><g /></svg>`),
}));

import {
  ApiError,
  brainstormMessage,
  fetchArtefactText,
  generateFlowMap,
  generatePoc,
  getBrainstorm,
  postFlowMapSvg,
  submitRun,
  uploadBrainstormFile,
} from "../lib/api";
import { renderMermaid } from "../lib/mermaid";

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
  vi.mocked(generatePoc).mockReset();
  vi.mocked(generateFlowMap).mockReset();
  vi.mocked(postFlowMapSvg).mockReset();
  vi.mocked(fetchArtefactText).mockReset();
  vi.mocked(uploadBrainstormFile).mockReset();
  vi.mocked(renderMermaid).mockClear();
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

describe("Brainstorm synthesis — PoC and flow map (§6.3/§6.4)", () => {
  function loadReady() {
    vi.mocked(getBrainstorm).mockResolvedValue({
      outline_md: outlineMd(["problem"], { problem: "A resolved problem." }),
      transcript: [],
      sufficiency: { ready: true, missing: [] },
      stage: "BRAINSTORM",
    });
  }

  async function openTab(name: RegExp) {
    fireEvent.click(await screen.findByRole("tab", { name }));
  }

  it("builds a proof of concept and previews it in a sandboxed frame", async () => {
    loadReady();
    vi.mocked(generatePoc).mockResolvedValue({
      produced: "poc",
      reason: "A clickable mock will help here.",
    });

    renderBrainstorm();
    // The PoC is a top-level tab now, not a block at the foot of the page.
    await openTab(/proof of concept/i);
    fireEvent.click(await screen.findByRole("button", { name: /build a proof of concept/i }));

    const frame = (await screen.findByTitle("Proof-of-concept preview")) as HTMLIFrameElement;
    expect(frame.getAttribute("src")).toContain(`/artefact/poc.html`);
    expect(frame.getAttribute("sandbox")).toBe(""); // display only — the artefact can't act
    expect(vi.mocked(generatePoc)).toHaveBeenCalledWith(CODE);
    // The action becomes a "rebuild" once a PoC exists, never a dead button.
    expect(screen.getByRole("button", { name: /rebuild the proof of concept/i })).toBeTruthy();
  });

  it("when a PoC is not a fit, says so honestly and draws the flow map instead", async () => {
    loadReady();
    vi.mocked(generatePoc).mockResolvedValue({
      produced: "map",
      reason: "This idea is a data pipeline, not an interface.",
      mermaid: "flowchart TD\n  A-->B",
    });
    vi.mocked(postFlowMapSvg).mockResolvedValue({ run_id: CODE, committed: true });

    renderBrainstorm();
    await openTab(/proof of concept/i);
    fireEvent.click(await screen.findByRole("button", { name: /build a proof of concept/i }));

    // The honest conditional-stage note (§6.1), not an error — shown on the PoC tab.
    expect(await screen.findByText(/not a fit for this idea/i)).toBeTruthy();
    expect(screen.getByText(/data pipeline, not an interface/i)).toBeTruthy();
    // The PoC build action is gone (the gate ruled it out); no dead button.
    expect(screen.queryByRole("button", { name: /build a proof of concept/i })).toBeNull();
    // The flow map was rendered client-side and posted back (CLAUDE.md §9)…
    expect(vi.mocked(renderMermaid)).toHaveBeenCalledWith("flowchart TD\n  A-->B");
    expect(vi.mocked(postFlowMapSvg)).toHaveBeenCalledWith(CODE, expect.stringContaining("<svg"));
    // …and is waiting on its own tab.
    await openTab(/flow map/i);
    expect(await screen.findByTitle("Information-flow map")).toBeTruthy();
  });

  it("generates a flow map on demand, renders it, and commits the SVG", async () => {
    loadReady();
    vi.mocked(generateFlowMap).mockResolvedValue({
      produced: "map",
      mermaid: "flowchart LR\n  User-->System",
    });
    vi.mocked(postFlowMapSvg).mockResolvedValue({ run_id: CODE, committed: true });

    renderBrainstorm();
    await openTab(/flow map/i);
    fireEvent.click(await screen.findByRole("button", { name: /generate a flow map/i }));

    expect(await screen.findByTitle("Information-flow map")).toBeTruthy();
    expect(vi.mocked(generateFlowMap)).toHaveBeenCalledWith(CODE);
    expect(vi.mocked(renderMermaid)).toHaveBeenCalledWith("flowchart LR\n  User-->System");
    expect(vi.mocked(postFlowMapSvg)).toHaveBeenCalledWith(CODE, expect.stringContaining("<svg"));
    // Now offered as a regenerate.
    expect(screen.getByRole("button", { name: /regenerate the flow map/i })).toBeTruthy();
  });

  it("restores a committed PoC and flow map on resume without re-posting the SVG", async () => {
    vi.mocked(getBrainstorm).mockResolvedValue({
      outline_md: outlineMd(["problem"], { problem: "A resolved problem." }),
      transcript: [],
      sufficiency: { ready: true, missing: [] },
      stage: "BRAINSTORM",
      artefacts: {
        poc: true,
        flow_map: true,
        flow_map_svg: true, // already committed — the resume must not re-post it
        feasibility: { feasible: true, reason: "A mock helps." },
      },
    });
    vi.mocked(fetchArtefactText).mockResolvedValue("flowchart TD\n  A-->B");

    renderBrainstorm();

    // Both artefacts come back from committed state (§7.5), each on its own tab.
    await openTab(/proof of concept/i);
    expect(await screen.findByTitle("Proof-of-concept preview")).toBeTruthy();
    await openTab(/flow map/i);
    expect(await screen.findByTitle("Information-flow map")).toBeTruthy();
    expect(vi.mocked(fetchArtefactText)).toHaveBeenCalledWith(CODE, "flow-map.mmd");
    expect(vi.mocked(postFlowMapSvg)).not.toHaveBeenCalled();
  });
});

describe("Brainstorm file upload (§7)", () => {
  function loadFresh() {
    vi.mocked(getBrainstorm).mockResolvedValue({
      outline_md: outlineMd([]),
      transcript: [],
      sufficiency: { ready: false, missing: [] },
      stage: "BRAINSTORM",
    });
  }

  async function openUploader() {
    fireEvent.click(await screen.findByRole("button", { name: /or upload a file instead/i }));
  }

  function pick(name: string, content: string, type = "text/plain") {
    const file = new File([content], name, { type });
    fireEvent.change(screen.getByLabelText(/choose a file to upload/i), {
      target: { files: [file] },
    });
  }

  it("uploads a plain-text file as seed material and folds the result into the outline", async () => {
    loadFresh();
    vi.mocked(uploadBrainstormFile).mockResolvedValue({
      produced: "outline",
      assistant_message: "I've drafted the problem — who are the users?",
      outline_md: outlineMd(["problem"], { problem: "Citizens wait too long." }),
      outline_delta: { updated: ["problem"], newly_resolved: ["problem"], title_changed: false },
      sufficiency: { ready: false, missing: [] },
      stage: "BRAINSTORM",
    });

    renderBrainstorm();
    await openUploader();
    pick("idea.txt", "We run an enquiries team and want AI to help draft replies.");

    // Gated on the no-sensitive acknowledgement — Upload is disabled until it's ticked.
    const ack = await screen.findByLabelText(/no sensitive information/i);
    const uploadBtn = () => screen.getByRole("button", { name: /^upload$/i });
    expect((uploadBtn() as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(ack);
    expect((uploadBtn() as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(uploadBtn());

    expect(await screen.findByText("I've drafted the problem — who are the users?")).toBeTruthy();
    expect(screen.getByText("Citizens wait too long.")).toBeTruthy();
    expect(vi.mocked(uploadBrainstormFile)).toHaveBeenCalledWith(
      CODE,
      expect.objectContaining({ format: "text", acknowledgeNoSensitive: true }),
    );
  });

  it("requires the extra starting-material acknowledgement for a Mermaid upload, then draws the map", async () => {
    loadFresh();
    vi.mocked(uploadBrainstormFile).mockResolvedValue({
      produced: "map",
      mermaid: "flowchart TD\n  A-->B",
    });
    vi.mocked(postFlowMapSvg).mockResolvedValue({ run_id: CODE, committed: true });

    renderBrainstorm();
    await openUploader();
    pick("flow.mmd", "flowchart TD\n  A-->B", "text/plain");

    const uploadBtn = () => screen.getByRole("button", { name: /^upload$/i });
    // With only the no-sensitive ack, a Mermaid upload stays disabled…
    fireEvent.click(await screen.findByLabelText(/no sensitive information/i));
    expect((uploadBtn() as HTMLButtonElement).disabled).toBe(true);
    // …until the starting-material ack is given too.
    fireEvent.click(screen.getByLabelText(/starting material/i));
    expect((uploadBtn() as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(uploadBtn());

    // Rendered client-side, posted back, and shown on the flow-map tab (CLAUDE.md §9).
    expect(await screen.findByTitle("Information-flow map")).toBeTruthy();
    expect(vi.mocked(renderMermaid)).toHaveBeenCalledWith("flowchart TD\n  A-->B");
    expect(vi.mocked(postFlowMapSvg)).toHaveBeenCalledWith(CODE, expect.stringContaining("<svg"));
    expect(vi.mocked(uploadBrainstormFile)).toHaveBeenCalledWith(
      CODE,
      expect.objectContaining({
        format: "mermaid",
        acknowledgeNoSensitive: true,
        acknowledgeStartingMaterial: true,
      }),
    );
  });

  it("uploads an HTML file as the proof of concept and shows it in the sandboxed frame", async () => {
    loadFresh();
    vi.mocked(uploadBrainstormFile).mockResolvedValue({ produced: "poc" });

    renderBrainstorm();
    await openUploader();
    pick("mock.html", "<!doctype html><html><body>Mock</body></html>", "text/html");

    fireEvent.click(await screen.findByLabelText(/no sensitive information/i));
    fireEvent.click(screen.getByRole("button", { name: /^upload$/i }));

    const frame = (await screen.findByTitle("Proof-of-concept preview")) as HTMLIFrameElement;
    expect(frame.getAttribute("src")).toContain("/artefact/poc.html");
    expect(frame.getAttribute("sandbox")).toBe("");
    expect(vi.mocked(uploadBrainstormFile)).toHaveBeenCalledWith(
      CODE,
      expect.objectContaining({ format: "html", acknowledgeNoSensitive: true }),
    );
  });

  it("turns a bare 404 (server missing the endpoint) into an honest, actionable message", async () => {
    // The reported bug: a backend running an older build than this page has no
    // /brainstorm/upload route, so it answers the SPA's POST with the framework's default
    // 404 whose detail is the naked string "Not Found". The user must see why, not that.
    loadFresh();
    vi.mocked(uploadBrainstormFile).mockRejectedValue(new ApiError(404, "Not Found"));

    renderBrainstorm();
    await openUploader();
    pick("idea.txt", "We run an enquiries team and want AI to help draft replies.");
    fireEvent.click(await screen.findByLabelText(/no sensitive information/i));
    fireEvent.click(screen.getByRole("button", { name: /^upload$/i }));

    expect(await screen.findByText(/older version that hasn't been updated/i)).toBeTruthy();
    // The cryptic default is never surfaced verbatim.
    expect(screen.queryByText(/^Not Found$/)).toBeNull();
  });
});
