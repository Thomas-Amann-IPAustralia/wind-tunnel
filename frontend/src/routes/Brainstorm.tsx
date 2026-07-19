import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { FlowMapPanel, PocPanel } from "../components/BrainstormSynthesis";
import { BrainstormTabs } from "../components/BrainstormTabs";
import type { BrainstormTab } from "../components/BrainstormTabs";
import { Conversation } from "../components/Conversation";
import { FileUpload } from "../components/FileUpload";
import type { UploadPayload } from "../components/FileUpload";
import { OutlineCanvas } from "../components/OutlineCanvas";
import { RunCodeChip } from "../components/RunCodeChip";
import { SufficiencyBanner } from "../components/SufficiencyBanner";
import { Surface } from "../components/Surface";
import {
  ApiError,
  artefactUrl,
  brainstormMessage,
  editOutline,
  fetchArtefactText,
  generateFlowMap,
  generatePoc,
  getBrainstorm,
  NetworkError,
  postFlowMapSvg,
  submitRun,
  uploadBrainstormFile,
} from "../lib/api";
import { parseOutline } from "../lib/outline";
import { isValid } from "../lib/runCode";
import type { FeasibilityVerdict, Sufficiency, TranscriptTurn } from "../lib/types";
import "./Brainstorm.css";

type LoadState = "loading" | "ready" | "error";

/** Lazy-load mermaid.js (a large dependency) only when the user actually draws a map,
 * so it never weighs down the first paint. It renders the flow map to SVG in-browser
 * (CLAUDE.md §9). */
async function renderMermaidLazy(source: string): Promise<string> {
  const { renderMermaid } = await import("../lib/mermaid");
  return renderMermaid(source);
}

/**
 * The Brainstorm co-design canvas (design §6) — the conversation that fills the
 * outline, the live outline canvas, the sufficiency banner, and submission. The
 * backend interview loop (`/brainstorm/message`, `/edit-outline`, `/brainstorm`)
 * does the thinking; this screen renders the exchange and its result, and hands
 * the finished outline to Governance on Submit.
 */
export function Brainstorm() {
  const { code } = useParams();
  const navigate = useNavigate();

  const [load, setLoad] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [redirectStage, setRedirectStage] = useState<string | null>(null);

  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const [outlineMd, setOutlineMd] = useState("");
  const [sufficiency, setSufficiency] = useState<Sufficiency | null>(null);

  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [youEdited, setYouEdited] = useState<ReadonlySet<string>>(new Set());

  const [resolvingIds, setResolvingIds] = useState<ReadonlySet<string>>(new Set());
  const resolveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Which working surface is showing (§6.2): the conversation, or the two more
  // expressive ways to say the same thing — the PoC and the flow map.
  const [tab, setTab] = useState<BrainstormTab>("conversation");

  // Optional synthesis (§6.3/§6.4): the PoC and the flow map.
  const [feasibility, setFeasibility] = useState<FeasibilityVerdict | null>(null);
  const [pocReady, setPocReady] = useState(false);
  const [pocNonce, setPocNonce] = useState(0); // busts the iframe cache on a rebuild
  const [flowSvg, setFlowSvg] = useState<string | null>(null);
  const [building, setBuilding] = useState<"poc" | "map" | null>(null);
  const [synthError, setSynthError] = useState<string | null>(null);
  // A committed flow map to re-render for display on load/resume ({ svgCommitted } says
  // whether we still owe the backend an SVG); cleared once restored.
  const [mapToRestore, setMapToRestore] = useState<{ svgCommitted: boolean } | null>(null);

  const valid = Boolean(code && isValid(code));

  // Highlight newly-resolved / amended sections for one settle beat (§3.6).
  const markResolving = useCallback((ids: string[]) => {
    if (ids.length === 0) return;
    if (resolveTimer.current) clearTimeout(resolveTimer.current);
    setResolvingIds(new Set(ids));
    resolveTimer.current = setTimeout(() => setResolvingIds(new Set()), 1400);
  }, []);

  useEffect(() => () => void (resolveTimer.current && clearTimeout(resolveTimer.current)), []);

  // Load (or resume) the co-design state (§7.5).
  useEffect(() => {
    if (!valid || !code) return;
    let cancelled = false;
    setLoad("loading");
    getBrainstorm(code)
      .then((state) => {
        if (cancelled) return;
        if (state.stage !== "BRAINSTORM") {
          setRedirectStage(state.stage); // a submitted run belongs on the Chamber
          return;
        }
        setTurns(state.transcript);
        setOutlineMd(state.outline_md);
        setSufficiency(state.sufficiency);
        // Restore the optional synthesis so a reload / resume doesn't lose it (§7.5).
        const a = state.artefacts;
        if (a) {
          if (a.feasibility) setFeasibility(a.feasibility);
          if (a.poc) setPocReady(true);
          if (a.flow_map) setMapToRestore({ svgCommitted: a.flow_map_svg });
        }
        setLoad("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(describe(err, "load this run"));
        setLoad("error");
      });
    return () => {
      cancelled = true;
    };
  }, [code, valid]);

  const outline = useMemo(() => parseOutline(outlineMd), [outlineMd]);

  // Re-render a committed flow map from its Mermaid source for display (§6.4). Isolated
  // in its own effect so it never blocks the main load, and so tests can drive the
  // (mocked) renderer directly. A map whose SVG never made it to the server (svgCommitted
  // false — an interrupted post) is healed here.
  useEffect(() => {
    if (!mapToRestore || !code) return;
    let cancelled = false;
    const owed = !mapToRestore.svgCommitted;
    setMapToRestore(null);
    (async () => {
      try {
        const mermaid = await fetchArtefactText(code, "flow-map.mmd");
        const svg = await renderMermaidLazy(mermaid);
        if (cancelled) return;
        setFlowSvg(svg);
        if (owed) await postFlowMapSvg(code, svg);
      } catch {
        /* Non-fatal: the map simply won't show until the user regenerates it. */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mapToRestore, code]);

  const send = useCallback(
    async (message: string) => {
      if (!code) return;
      setSendError(null);
      setPendingUser(message);
      setSending(true);
      try {
        const resp = await brainstormMessage(code, message);
        setTurns((prev) => [
          ...prev,
          { role: "user", text: message, ts: nowIso() },
          { role: "assistant", text: resp.assistant_message, ts: nowIso() },
        ]);
        setOutlineMd(resp.outline_md);
        setSufficiency(resp.sufficiency);
        if (resp.outline_delta) {
          markResolving([...resp.outline_delta.newly_resolved, ...resp.outline_delta.updated]);
        }
      } catch (err) {
        setSendError(describe(err, "send that message"));
      } finally {
        setPendingUser(null);
        setSending(false);
      }
    },
    [code, markResolving],
  );

  // Upload a file instead of chatting (§7 file upload). Plain text seeds the outline (and is
  // recorded as a turn, exactly as a long first message would be); a Mermaid upload becomes the
  // flow map (rendered + posted back like a generated one); an HTML upload becomes the PoC. The
  // result routes the user to the surface that now holds their material.
  const upload = useCallback(
    async (payload: UploadPayload) => {
      if (!code) return;
      setUploadError(null);
      setUploading(true);
      try {
        const resp = await uploadBrainstormFile(code, {
          format: payload.format,
          content: payload.content,
          filename: payload.filename,
          acknowledgeNoSensitive: payload.acknowledgeNoSensitive,
          acknowledgeStartingMaterial: payload.acknowledgeStartingMaterial,
        });
        if (resp.produced === "outline") {
          setTurns((prev) => [
            ...prev,
            { role: "user", text: payload.content, ts: nowIso() },
            { role: "assistant", text: resp.assistant_message ?? "", ts: nowIso() },
          ]);
          if (resp.outline_md) setOutlineMd(resp.outline_md);
          if (resp.sufficiency) setSufficiency(resp.sufficiency);
          if (resp.outline_delta) {
            markResolving([...resp.outline_delta.newly_resolved, ...resp.outline_delta.updated]);
          }
          setTab("conversation");
        } else if (resp.produced === "map") {
          if (resp.mermaid) {
            const svg = await renderMermaidLazy(resp.mermaid);
            setFlowSvg(svg);
            await postFlowMapSvg(code, svg);
          }
          setTab("map");
        } else {
          // An uploaded PoC — exempt from the limitations-banner requirement (§12.4).
          setFeasibility(null);
          setPocReady(true);
          setPocNonce((n) => n + 1);
          setTab("poc");
        }
      } catch (err) {
        setUploadError(describe(err, "upload that file"));
      } finally {
        setUploading(false);
      }
    },
    [code, markResolving],
  );

  const saveSection = useCallback(
    async (id: string, body: string) => {
      if (!code || body.length === 0) return;
      setEditError(null);
      setSavingId(id);
      try {
        const resp = await editOutline(code, { sections: { [id]: body } });
        setOutlineMd(resp.outline_md);
        setSufficiency(resp.sufficiency);
        setYouEdited((prev) => new Set(prev).add(id));
        markResolving([id]);
        setEditingId(null);
      } catch (err) {
        setEditError(describe(err, "save that edit"));
      } finally {
        setSavingId(null);
      }
    },
    [code, markResolving],
  );

  const buildPoc = useCallback(async () => {
    if (!code) return;
    setSynthError(null);
    setBuilding("poc");
    try {
      const resp = await generatePoc(code);
      if (resp.produced === "poc") {
        setFeasibility({ feasible: true, reason: resp.reason });
        setPocReady(true);
        setPocNonce((n) => n + 1);
      } else {
        // The gate decided a static mock isn't a fit — the flow map was produced instead.
        setFeasibility({ feasible: false, reason: resp.reason });
        if (resp.mermaid) {
          const svg = await renderMermaidLazy(resp.mermaid);
          setFlowSvg(svg);
          await postFlowMapSvg(code, svg);
        }
        // Stay on the PoC tab so the honest "not a fit" note is seen; the map is now
        // ready on its own tab (its glyph lights up) for the user to open next.
      }
    } catch (err) {
      setSynthError(describe(err, "build a proof of concept"));
    } finally {
      setBuilding(null);
    }
  }, [code]);

  const generateMap = useCallback(async () => {
    if (!code) return;
    setSynthError(null);
    setBuilding("map");
    try {
      const resp = await generateFlowMap(code);
      const svg = await renderMermaidLazy(resp.mermaid);
      setFlowSvg(svg);
      await postFlowMapSvg(code, svg);
    } catch (err) {
      setSynthError(describe(err, "generate a flow map"));
    } finally {
      setBuilding(null);
    }
  }, [code]);

  const submit = useCallback(async () => {
    if (!code) return;
    setSubmitError(null);
    setSubmitting(true);
    try {
      await submitRun(code);
      navigate(`/run/${code}/chamber`);
    } catch (err) {
      setSubmitting(false);
      setSubmitError(describe(err, "submit this run"));
    }
  }, [code, navigate]);

  if (!valid || !code) return <Navigate to="/" replace />;
  if (redirectStage) return <Navigate to={`/run/${code}/chamber`} replace />;

  const pocNotAFit = feasibility !== null && !feasibility.feasible;
  const pocUrl = pocReady && code ? `${artefactUrl(code, "poc.html")}?v=${pocNonce}` : null;

  const pocState = pocReady ? "ready" : pocNotAFit ? "not-a-fit" : "idle";
  const mapState = flowSvg ? "ready" : "idle";

  return (
    <Surface kind="console" subtitle="Brainstorm" header={<RunCodeChip code={code} />}>
      <div className="wt-brainstorm">
        {load === "loading" ? (
          <p className="wt-brainstorm__status" role="status">
            Loading your co-design space…
          </p>
        ) : load === "error" ? (
          <p className="wt-brainstorm__status wt-brainstorm__status--error" role="alert">
            {loadError}
          </p>
        ) : (
          <>
            <BrainstormTabs
              active={tab}
              onChange={setTab}
              pocState={pocState}
              mapState={mapState}
            />

            <div className="wt-brainstorm__panes">
              <div
                className="wt-brainstorm__surface"
                role="tabpanel"
                id={`wt-panel-${tab}`}
                aria-labelledby={`wt-tab-${tab}`}
              >
                {tab === "conversation" ? (
                  <div className="wt-brainstorm__conversation">
                    <Conversation
                      turns={turns}
                      pendingUser={pendingUser}
                      thinking={sending}
                      onSend={send}
                      disabled={sending || uploading}
                      error={sendError}
                    />
                    <FileUpload uploading={uploading} error={uploadError} onUpload={upload} />
                  </div>
                ) : tab === "poc" ? (
                  <PocPanel
                    feasibility={feasibility}
                    pocUrl={pocUrl}
                    building={building === "poc"}
                    error={synthError}
                    onBuildPoc={buildPoc}
                  />
                ) : (
                  <FlowMapPanel
                    flowSvg={flowSvg}
                    building={building === "map"}
                    error={synthError}
                    onGenerateMap={generateMap}
                  />
                )}
              </div>
              <OutlineCanvas
                outline={outline}
                resolvingIds={resolvingIds}
                youEdited={youEdited}
                editingId={editingId}
                savingId={savingId}
                editError={editError}
                onStartEdit={setEditingId}
                onCancelEdit={() => {
                  setEditingId(null);
                  setEditError(null);
                }}
                onSave={saveSection}
              />
            </div>

            <div className="wt-brainstorm__footer">
              <SufficiencyBanner sufficiency={sufficiency} outline={outline} />
              <div className="wt-brainstorm__submit">
                {submitError ? (
                  <p className="wt-brainstorm__submit-error" role="alert">
                    {submitError}
                  </p>
                ) : null}
                <button
                  type="button"
                  className={`wt-btn ${
                    sufficiency?.ready ? "wt-btn--primary" : "wt-btn--secondary"
                  } wt-brainstorm__submit-btn`}
                  onClick={submit}
                  disabled={submitting}
                >
                  {submitting ? "Submitting…" : "Submit for assessment"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </Surface>
  );
}

function nowIso(): string {
  return new Date().toISOString();
}

function describe(err: unknown, action: string): string {
  if (err instanceof NetworkError) {
    return `Couldn't reach the tunnel to ${action}. It may still be warming up — give it a moment and try again.`;
  }
  if (err instanceof ApiError) {
    // A bare 404 "Not Found" is the framework default the backend sends when *no route*
    // matches — i.e. the server is running an older build than this page and hasn't got the
    // endpoint yet (e.g. after a frontend deploy without the matching backend redeploy). The
    // backend's own 404s carry meaningful text ("No run found for code …"), so only the bare
    // default is rewritten — surfacing a naked "Not Found" to a public servant is meaningless.
    if (err.status === 404 && /^not found\.?$/i.test(err.message.trim())) {
      return `The server didn't recognise the request to ${action} — it may be running an older version that hasn't been updated yet. Please try again shortly, or type your idea into the chat instead.`;
    }
    return err.message;
  }
  return `Something went wrong trying to ${action}. Please try again.`;
}
