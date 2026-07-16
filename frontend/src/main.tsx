import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";

import App from "./App";
import "./styles/tokens.css";
import "./styles/base.css";

// Hash routing: GitHub Pages project sites have no server-side rewrites
// (CLAUDE.md §9), so all app routing lives after the # and Pages always serves
// index.html.
const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element.");

createRoot(root).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
