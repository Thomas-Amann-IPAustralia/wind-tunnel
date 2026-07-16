// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Markdown } from "./markdown";

describe("Markdown", () => {
  it("renders headings, paragraphs, bold and italic", () => {
    render(<Markdown source={"## 3. Inherent risk\n\nThis is **bold** and *emphasised* text."} />);
    expect(screen.getByRole("heading", { name: /3\. Inherent risk/ })).toBeTruthy();
    expect(screen.getByText("bold").tagName).toBe("STRONG");
    expect(screen.getByText("emphasised").tagName).toBe("EM");
  });

  it("renders a pipe table and turns risk-rating cells into shape+label chips", () => {
    const md = [
      "| Area | Consequence | Likelihood | Risk rating |",
      "| --- | --- | --- | --- |",
      "| 3.5 Privacy | Major | Possible | High |",
      "| 3.1 Autonomy | Minor | Rare | Low |",
    ].join("\n");
    render(<Markdown source={md} />);
    expect(screen.getByRole("table")).toBeTruthy();
    const high = screen.getByText("High");
    expect(high.className).toContain("wt-chip--high");
    const low = screen.getByText("Low");
    expect(low.className).toContain("wt-chip--low");
    // The area cell is plain text, not a chip.
    expect(screen.getByText("3.5 Privacy").className).not.toContain("wt-chip");
  });

  it("renders divergence italics (the reconciler's honest note)", () => {
    render(<Markdown source={"*Divergence: A said Moderate; B said Major. Resolved to Major.*"} />);
    expect(screen.getByText(/Divergence:/).tagName).toBe("EM");
  });

  it("is safe: raw HTML in the source is rendered as text, never as markup", () => {
    const { container } = render(<Markdown source={"A <script>alert(1)</script> line."} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
  });
});
