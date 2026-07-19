// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

// A render smoke test for the app's front door (gate → landing → resume). It
// exercises the real routing, the usage-warning gate (§4), the once-per-session
// acknowledgement, and the local run-code validation on the resume screen (§7.5)
// — the paths that don't need a live backend. fetch is stubbed so the post-gate
// warm-up ping (design §5) never touches the network.

function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  sessionStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App front door", () => {
  it("shows the usage-warning gate before anything else (§4)", () => {
    renderApp();
    expect(screen.getByRole("heading", { name: /a few things to know first/i })).toBeTruthy();
    // The three points the user must hold are present.
    expect(screen.getByText(/this is public/i)).toBeTruthy();
    expect(screen.getByText(/nothing sensitive/i)).toBeTruthy();
    // The landing is not reachable until the gate is passed.
    expect(screen.queryByRole("heading", { name: /test your ai idea/i })).toBeNull();
  });

  it("passes the gate once and lands on the empty state (§5)", () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: /i understand — continue/i }));
    expect(
      screen.getByRole("heading", { name: /test your ai idea before you build it/i }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /start a new idea/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /resume a run/i })).toBeTruthy();
  });

  it("does not re-show the gate once acknowledged this session", () => {
    sessionStorage.setItem("wt.gate.acknowledged", "1");
    renderApp();
    expect(screen.queryByRole("heading", { name: /a few things to know first/i })).toBeNull();
    expect(screen.getByRole("heading", { name: /test your ai idea/i })).toBeTruthy();
  });

  it("rejects a malformed run code locally on the resume screen (§7.5)", () => {
    sessionStorage.setItem("wt.gate.acknowledged", "1");
    renderApp("/resume");
    const input = screen.getByLabelText(/run code/i);
    fireEvent.change(input, { target: { value: "not-a-code" } });
    fireEvent.click(screen.getByRole("button", { name: /^resume$/i }));
    expect(screen.getByRole("alert").textContent).toMatch(/doesn't look like a run code/i);
  });
});
