import { useEffect, useState } from "react";

import "./TunnelWarmup.css";

/**
 * The "tunnel is warming up" loading animation — an eccentric, on-brand flourish
 * for the waiting states (the Render cold start §5, the first Chamber load, and a
 * run waiting for its Action to spin up §5.7). It flip-books the eleven pixel-art
 * sprites of a seedling growing and bending in the wind (`img/sprites/*.png`),
 * echoing the Windtunnel logo, so a wait reads as *alive and working*, never hung.
 *
 * All frames are stacked and pre-loaded, so cycling is flicker-free after first
 * paint. Under reduced motion it freezes on the grown frame (still clearly the
 * mark, no motion) and the visible copy carries the meaning either way (§9).
 */

// Sorted 00.png … 10.png — the growth sequence in order (Vite resolves each to a
// hashed asset URL at build; the glob is the one place the sprite set is named).
const SPRITES: string[] = Object.entries(
  import.meta.glob("../img/sprites/*.png", { eager: true, import: "default" }) as Record<
    string,
    string
  >,
)
  .sort(([a], [b]) => a.localeCompare(b))
  .map(([, url]) => url);

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function TunnelWarmup({
  size = 72,
  label,
  layout = "stack",
}: {
  size?: number;
  label?: string;
  /** `stack` = sprite above label (waiting screens); `inline` = sprite beside it. */
  layout?: "stack" | "inline";
}) {
  const reduced = prefersReducedMotion();
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    if (reduced || SPRITES.length <= 1) return;
    const h = setInterval(() => setFrame((f) => (f + 1) % SPRITES.length), 140);
    return () => clearInterval(h);
  }, [reduced]);

  const active = reduced ? SPRITES.length - 1 : frame;

  return (
    <span className={`wt-warmup wt-warmup--${layout}`} role="status">
      <span className="wt-warmup__stage" style={{ width: size, height: size }} aria-hidden="true">
        {SPRITES.map((src, i) => (
          <img key={i} className="wt-warmup__frame" src={src} alt="" data-on={i === active} />
        ))}
      </span>
      {label ? <span className="wt-warmup__label">{label}</span> : null}
    </span>
  );
}
