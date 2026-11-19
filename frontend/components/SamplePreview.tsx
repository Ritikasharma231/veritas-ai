"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { FileText, Link2, ScanSearch } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AnalysisResponse } from "@/lib/types";
import { PredictionBadge } from "./ui";

const SAMPLE =
  "BREAKING: Shocking new report reveals the government is hiding the truth! " +
  "You won't believe what insiders are saying — act now before they delete everything!";

export function SamplePreview() {
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.analyzeText(SAMPLE, undefined, false);
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.detail) : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
        <div className="flex items-center gap-2 text-sm text-ink-secondary">
          <ScanSearch size={15} className="text-accent" />
          Live analysis preview
        </div>
        <button onClick={run} disabled={loading} className="btn-primary !px-3.5 !py-1.5 !text-xs">
          {loading ? "Analyzing…" : result ? "Re-run" : "Run sample"}
        </button>
      </div>
      <div className="grid gap-0 md:grid-cols-2">
        <div className="border-b border-line p-5 md:border-b-0 md:border-r">
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <FileText size={13} /> Sample input — sensational claim style
          </div>
          <p className="mt-3 font-serif text-[15px] leading-relaxed text-ink-primary">
            “{SAMPLE}”
          </p>
        </div>
        <div className="p-5">
          {!result && !loading && !error && (
            <div className="flex h-full min-h-[120px] flex-col items-center justify-center gap-2 text-center text-sm text-ink-muted">
              <Link2 size={18} className="text-ink-muted" />
              <p>Run a real inference against the configured model.<br />No canned results — this calls the live API.</p>
            </div>
          )}
          {loading && (
            <div className="flex h-full min-h-[120px] items-center justify-center">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="h-6 w-6 rounded-full border-2 border-accent border-t-transparent"
              />
            </div>
          )}
          {error && <p className="text-sm text-danger">{error}</p>}
          {result && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
              <div className="flex items-center gap-3">
                <PredictionBadge prediction={result.prediction} confidence={result.confidence} />
                <span className="text-xs text-ink-muted">{result.inference_ms?.toFixed(0)} ms · not saved to history</span>
              </div>
              {result.probabilities && (
                <div className="mt-4 space-y-2">
                  {Object.entries(result.probabilities).map(([k, v]) => (
                    <div key={k}>
                      <div className="mb-1 flex justify-between text-xs text-ink-secondary">
                        <span>{k}</span><span>{Math.round(v * 100)}%</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-bg-secondary">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${v * 100}%` }}
                          className={`h-full rounded-full ${k === "Fake" ? "bg-danger" : "bg-success"}`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
