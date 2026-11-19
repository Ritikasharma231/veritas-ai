"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle, Check, Eraser, Globe, Link2, Loader2, Play,
  ShieldAlert, Type,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AnalysisResponse, UrlPreview } from "@/lib/types";
import { ResultsPanel } from "./ResultsPanel";

const EXAMPLES = [
  {
    label: "Sensational claim",
    text: "SHOCKING: You won't believe what doctors don't want you to know! This one weird trick could change everything — act now before they delete it!",
  },
  {
    label: "Standard reporting",
    text: "The central bank announced on Tuesday that interest rates would remain unchanged, citing steady inflation figures in its latest quarterly report. Economists surveyed by the institute had broadly expected the decision.",
  },
  {
    label: "Satire / opinion",
    text: "In a stunning development that absolutely nobody predicted, my neighbor's cat has once again chosen to sit on the keyboard during an important meeting. Sources confirm this is the third consecutive day of feline interference.",
  },
];

const STAGES = ["Validating input", "Fetching content", "Tokenizing", "Running transformer inference", "Computing attribution", "Done"];

type Mode = "text" | "url";

export function AnalyzeWorkspace() {
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [preview, setPreview] = useState<UrlPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [saveHistory, setSaveHistory] = useState(true);

  const charCount = text.length;
  const tooLong = charCount > 50000;

  const canAnalyze = useMemo(() => {
    if (busy) return false;
    if (mode === "text") return text.trim().length >= 20 && !tooLong;
    return preview !== null;
  }, [busy, mode, text, tooLong, preview]);

  const setStageTimed = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setResult(null);
    setStage(0);
    const timers = STAGES.slice(0, -1).map((_, i) =>
      setTimeout(() => setStage(i + 1), 350 * (i + 1))
    );
    try {
      await fn();
      setStage(STAGES.length - 1);
    } catch (e) {
      setError(e instanceof ApiError ? formatDetail(e.detail) : "Analysis failed unexpectedly.");
    } finally {
      timers.forEach(clearTimeout);
      setBusy(false);
    }
  };

  const analyzeText = () =>
    setStageTimed(async () => {
      const r = await api.analyzeText(text, undefined, saveHistory);
      setResult(r);
    });

  const analyzeUrl = () =>
    setStageTimed(async () => {
      const r = await api.analyzeUrl(url, saveHistory);
      setResult(r);
    });

  const fetchPreview = async () => {
    setPreviewLoading(true);
    setError(null);
    setPreview(null);
    try {
      const p = await api.previewUrl(url);
      setPreview(p);
    } catch (e) {
      setError(e instanceof ApiError ? formatDetail(e.detail) : "Could not fetch URL.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const loadExample = (t: string) => {
    setMode("text");
    setText(t);
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl font-semibold">Analysis Workspace</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Submit an article, headline, or claim. Results are statistical estimates — not verdicts of truth.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Input column */}
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex rounded-xl border border-line p-1">
            {(["text", "url"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(null); }}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition-colors ${
                  mode === m ? "bg-accent-soft text-accent" : "text-ink-secondary hover:text-ink-primary"
                }`}
              >
                {m === "text" ? <Type size={14} /> : <Link2 size={14} />}
                {m === "text" ? "Text" : "Article URL"}
              </button>
            ))}
          </div>

          {mode === "text" ? (
            <div>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste a news article, headline, or claim here…"
                className="input min-h-[280px] resize-y font-mono !text-[13px] leading-relaxed"
                maxLength={60000}
              />
              <div className="mt-2 flex items-center justify-between text-xs">
                <span className={tooLong ? "text-danger" : "text-ink-muted"}>
                  {charCount.toLocaleString()} / 50,000
                </span>
                <button
                  onClick={() => setText("")}
                  className="flex items-center gap-1 text-ink-muted hover:text-ink-primary"
                >
                  <Eraser size={12} /> Clear
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex gap-2">
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/news/article"
                  className="input"
                  inputMode="url"
                />
                <button onClick={fetchPreview} disabled={previewLoading || url.trim().length < 8} className="btn-ghost shrink-0">
                  {previewLoading ? <Loader2 size={14} className="animate-spin" /> : <Globe size={14} />}
                  Fetch
                </button>
              </div>
              <p className="mt-2 text-xs text-ink-muted">
                Only public http(s) pages are fetched. Private networks and unsupported protocols are blocked.
              </p>
              <AnimatePresence>
                {preview && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="mt-4 rounded-xl border border-line bg-bg-secondary p-4"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-ink-primary">{preview.title || "Untitled article"}</p>
                        <p className="mt-1 truncate text-xs text-ink-muted">{preview.site_name || preview.final_url}</p>
                      </div>
                      <span className="badge shrink-0 border border-line bg-bg-card text-ink-secondary">
                        {preview.text_length.toLocaleString()} chars
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs text-ink-secondary">
                      {preview.author && <span>Author: {preview.author}</span>}
                      {preview.publish_date && <span>Published: {preview.publish_date.slice(0, 10)}</span>}
                      <span className="col-span-2 text-ink-muted">Extracted via {preview.extractor}</span>
                    </div>
                    <p className="mt-3 line-clamp-4 text-xs leading-relaxed text-ink-muted">{preview.text_preview}…</p>
                    <p className="mt-2 text-[11px] text-ink-muted">
                      Review the extracted text above before analyzing. Metadata is as reported by the publisher.
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          <div className="mt-4">
            <p className="label">Try an example</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex.label}
                  onClick={() => loadExample(ex.text)}
                  className="badge border border-line bg-bg-secondary text-ink-secondary hover:border-accent/50 hover:text-accent"
                >
                  {ex.label}
                </button>
              ))}
            </div>
          </div>

          <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-ink-secondary">
            <input
              type="checkbox"
              checked={saveHistory}
              onChange={(e) => setSaveHistory(e.target.checked)}
              className="h-4 w-4 accent-accent"
            />
            Save to analysis history
          </label>

          <button
            onClick={mode === "text" ? analyzeText : analyzeUrl}
            disabled={!canAnalyze}
            className="btn-primary mt-4 w-full py-3"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {busy ? "Analyzing…" : "Analyze"}
          </button>

          <AnimatePresence>
            {busy && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="mt-4">
                <div className="space-y-1.5">
                  {STAGES.map((s, i) => (
                    <div key={s} className="flex items-center gap-2 text-xs">
                      {i < stage ? (
                        <Check size={12} className="text-success" />
                      ) : i === stage ? (
                        <Loader2 size={12} className="animate-spin text-accent" />
                      ) : (
                        <span className="h-3 w-3 rounded-full border border-line" />
                      )}
                      <span className={i <= stage ? "text-ink-secondary" : "text-ink-muted"}>{s}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 flex items-start gap-2 rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-danger"
              >
                <ShieldAlert size={16} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Results column */}
        <div className="lg:col-span-3">
          <AnimatePresence mode="wait">
            {result ? (
              <ResultsPanel key={result.id ?? "adhoc"} result={result} />
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="card flex min-h-[420px] flex-col items-center justify-center p-10 text-center"
              >
                <AlertTriangle size={28} className="text-ink-muted" />
                <h3 className="mt-4 font-serif text-xl">No analysis yet</h3>
                <p className="mt-2 max-w-sm text-sm text-ink-secondary">
                  Submit text or a URL to run transformer inference. Results will appear here with
                  probabilities, attribution, and linguistic signals.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
      .join("; ");
  }
  return "Request failed.";
}
