import logo from "../img/WindTunnelLogo.png";
import "./Wordmark.css";

/**
 * The wordmark (design §1, §3.3 — Archivo) with the Windtunnel emblem — the sapling
 * bending in the tunnel. One word, product-not-facility. Name is a one-token change
 * if Tom picks an alternative (§1); everything downstream is name-agnostic. The
 * emblem sits in a round tile so it reads cleanly on both the light Console and the
 * dark Chamber.
 */
export function Wordmark({ subtitle }: { subtitle?: string }) {
  return (
    <div className="wt-wordmark">
      <img className="wt-wordmark__logo" src={logo} alt="" width={30} height={30} />
      <span className="wt-wordmark__name">Windtunnel</span>
      {subtitle ? <span className="wt-wordmark__subtitle">{subtitle}</span> : null}
    </div>
  );
}
