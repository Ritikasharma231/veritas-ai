"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3, BookOpen, ChevronDown, Clock, Cpu, FileText,
  Globe, Info, Languages, Link2, ShieldAlert, Sparkles,
} from "lucide-react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalysisResponse, LinguisticSignal } from "@/lib/types";
import { Card, CardTitle, PredictionBadge } from "./ui";

interface Explanation {
  predicted_label?: string;
  tone?: string;
  guidance?: string;
  confidence_note?: string;
  top_contributing_tokens?: Record<string, number>;
  strongest_signal?: string | null;
  most_influential_sentence?: string | null;
  attribution_method?: string;
  attribution_note?: string;
  probability_breakdown?: Record<string, number>;
  limitations?: string[];
  disclaimer?: string;
  title?: string;
  input_length_chars?: number;
}

interface LingSignals {
  available?: boolean;
  sensationalism_score?: number;
  word_count?: number;
  sentence_count?: number;
  avg_sentence_length?: number;
  interpretation?: LinguisticSignal[];
  lexicon_hits?: Record<string, string[]>;
  metrics?: Record<string, number>;
  disclaimer?: string;
}

const toneColor: Record<string, string> = {
  error: "#E16D78",
  success: "#38B98A",
  warning: "#E9B45C",
  info: "#8B8CF6",
};

export function ResultsPanel({ result }: { result: AnalysisResponse }) {
  const [tab, setTab] = useState<"overview" | "signals" | "explain">("overview");
  const explanation = (result.explanation ?? {}) as Explanation;
  const signals = (result.linguistic_signals ?? {}) as LingSignals;
  const meta = (result.metadata ?? {}) as Record<string, unknown>;

  const probData = useMemo(() => {
    if (!result.probabilities) return [];
    return Object.entries(result.probabilities).map(([name, p]) => ({
      name,
      value: Math.round(p * 100),
      fill: name.toLowerCase().includes("fake") ? "#E16D78" : "#38B98A",
    }));
  }, [result.probabilities]);

  const tokenEntries = useMemo(
    () =>
      Object.entries(explanation.top_contributing_tokens ?? {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 12),
    [explanation]
  );
  const maxToken = tokenEntries.length ? tokenEntries[0][1] : 1;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      {/* Verdict card */}
      <Card className="relative overflow-hidden">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">Predicted classification</p>
            <div className="mt-2 flex items-center gap-3">
              <PredictionBadge prediction={result.prediction} confidence={result.confidence} />
              <span className="text-sm text-ink-secondary">
                {result.confidence != null && `${Math.round(result.confidence * 100)}% model confidence`}
              </span>
            </div>
            {explanation.guidance && (
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-secondary">{explanation.guidance}</p>
            )}
          </div>
          <div className="text-right text-xs text-ink-muted">
            <div className="flex items-center justify-end gap-1.5"><Cpu size={12} /> {result.model_name ?? "model"}</div>
            <div className="mt-1 flex items-center justify-end gap-1.5"><Clock size={12} /> {result.inference_ms?.toFixed(0)} ms inference</div>
            {result.created_at && <div className="mt-1">{new Date(result.created_at).toLocaleString()}</div>}
            {result.id && <div className="mt-1 font-mono">id: {result.id.slice(0, 8)}</div>}
          </div>
        </div>

        {probData.length > 0 && (
          <div className="mt-6">
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-muted">Class probabilities</p>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={probData} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: "#9299A8", fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                  <YAxis type="category" dataKey="name" width={70} tick={{ fill: "#F5F6FA", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: "rgba(139,140,246,0.08)" }}
                    contentStyle={{ background: "#171C27", border: "1px solid #262C3A", borderRadius: 10, fontSize: 12 }}
                    formatter={(v: number) => [`${v}%`, "Probability"]}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={22}>
                    {probData.map((d) => <Cell key={d.name} fill={d.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {result.truncated && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-warning">
            <AlertTriangleIcon /> Input exceeded the model's context window and was truncated.
          </p>
        )}
      </Card>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl border border-line bg-bg-secondary p-1">
        {(
          [
            ["overview", "Overview", FileText],
            ["signals", "Linguistic signals", Languages],
            ["explain", "Explanation", Sparkles],
          ] as const
        ).map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
              tab === key ? "bg-bg-card text-ink-primary shadow-sm" : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            <Icon size={13} /> {label}
          </button>
        ))}
      </div>

      <AnimateTab show={tab === "overview"}>
        <div className="grid gap-5 md:grid-cols-2">
          <Card>
            <CardTitle hint="Metadata reported by the source — not independently verified">
              <span className="flex items-center gap-2"><Globe size={14} className="text-accent" /> Source metadata</span>
            </CardTitle>
            <dl className="space-y-2.5 text-sm">
              <MetaRow k="Title" v={String(result.title ?? meta.title ?? explanation.title ?? "—")} />
              <MetaRow k="URL" v={result.source_url ? String(result.source_url) : "—"} link />
              <MetaRow k="Site" v={String(meta.site_name ?? "—")} />
              <MetaRow k="Author" v={String(meta.author ?? "—")} />
              <MetaRow k="Published" v={meta.publish_date ? String(meta.publish_date).slice(0, 10) : "—"} />
              <MetaRow k="Input type" v={result.input_type} />
              <MetaRow k="Characters" v={signals.word_count ? `${signals.word_count} words` : String(explanation.input_length_chars ?? "—")} />
              <MetaRow k="Extracted by" v={String(meta.extractor ?? "—")} />
            </dl>
            {result.source_url && (
              <a href={result.source_url} target="_blank" rel="noopener noreferrer nofollow"
                className="mt-4 inline-flex items-center gap-1.5 text-xs text-accent hover:underline">
                <Link2 size={12} /> Open original article
              </a>
            )}
          </Card>

          <Card>
            <CardTitle hint="Headline-style summary of what drove the score">
              <span className="flex items-center gap-2"><BarChart3 size={14} className="text-accent" /> Signal snapshot</span>
            </CardTitle>
            <div className="space-y-3">
              <div>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-ink-secondary">Sensationalism score</span>
                  <span className="font-medium text-ink-primary">{((signals.sensationalism_score ?? 0) * 100).toFixed(0)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-bg-secondary">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(signals.sensationalism_score ?? 0) * 100}%` }}
                    className="h-full rounded-full bg-warning"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-1 text-sm">
                <Stat label="Words" value={signals.word_count} />
                <Stat label="Sentences" value={signals.sentence_count} />
                <Stat label="Avg sentence length" value={signals.avg_sentence_length} />
                <Stat label="Exclamations" value={signals.metrics?.exclamation_marks} />
              </div>
              {explanation.most_influential_sentence && (
                <div className="rounded-xl border border-line bg-bg-secondary p-3">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">Most influential sentence</p>
                  <p className="mt-1.5 font-serif text-sm italic leading-relaxed text-ink-secondary">
                    “{explanation.most_influential_sentence}”
                  </p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </AnimateTab>

      <AnimateTab show={tab === "signals"}>
        <Card>
          <CardTitle hint="Rule-based stylistic features. Signals describe writing style — not factual truth.">
            <span className="flex items-center gap-2"><Languages size={14} className="text-accent" /> Linguistic signal analysis</span>
          </CardTitle>
          {signals.available === false ? (
            <p className="text-sm text-ink-muted">No linguistic analysis available for this input.</p>
          ) : (
            <div className="space-y-3">
              {(signals.interpretation ?? []).map((s, i) => (
                <div key={i} className="flex items-start gap-3 rounded-xl border border-line bg-bg-secondary/60 p-3.5">
                  <span
                    className="mt-1 h-2 w-2 shrink-0 rounded-full"
                    style={{ background: toneColor[s.severity] ?? "#8B8CF6" }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="text-sm font-medium text-ink-primary">{s.label}</p>
                      <span className="font-mono text-xs text-ink-muted">{String(s.value)}</span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-ink-secondary">{s.detail}</p>
                  </div>
                </div>
              ))}
              {signals.disclaimer && (
                <p className="flex items-start gap-2 pt-1 text-xs text-ink-muted">
                  <Info size={13} className="mt-0.5 shrink-0" /> {signals.disclaimer}
                </p>
              )}
            </div>
          )}
        </Card>
      </AnimateTab>

      <AnimateTab show={tab === "explain"}>
        <div className="grid gap-5 lg:grid-cols-2">
          <Card>
            <CardTitle hint="Tokens the model relied on most (gradient saliency)">
              <span className="flex items-center gap-2"><Sparkles size={14} className="text-accent" /> Top contributing tokens</span>
            </CardTitle>
            {tokenEntries.length === 0 ? (
              <p className="text-sm text-ink-muted">Attribution unavailable for this result.</p>
            ) : (
              <div className="space-y-2">
                {tokenEntries.map(([tok, score]) => (
                  <div key={tok} className="flex items-center gap-3">
                    <span className="w-32 truncate text-right text-xs text-ink-secondary" title={tok}>{tok}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-bg-secondary">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(score / maxToken) * 100}%` }}
                        className="h-full rounded-full bg-accent"
                      />
                    </div>
                    <span className="w-16 text-right font-mono text-[11px] text-ink-muted">{score.toFixed(3)}</span>
                  </div>
                ))}
                <p className="pt-2 text-[11px] leading-relaxed text-ink-muted">{explanation.attribution_note}</p>
              </div>
            )}
          </Card>

          <Card>
            <CardTitle>Model limitations &amp; disclaimer</CardTitle>
            <ul className="space-y-2.5">
              {(explanation.limitations ?? []).map((l, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-ink-secondary">
                  <ShieldAlert size={14} className="mt-0.5 shrink-0 text-warning" /> {l}
                </li>
              ))}
            </ul>
            {explanation.disclaimer && (
              <div className="mt-4 rounded-xl border border-warning/30 bg-warning/10 p-3.5">
                <p className="flex items-start gap-2 text-xs leading-relaxed text-ink-secondary">
                  <BookOpen size={13} className="mt-0.5 shrink-0 text-warning" /> {explanation.disclaimer}
                </p>
              </div>
            )}
            <p className="mt-4 text-[11px] text-ink-muted">
              Attribution method: {explanation.attribution_method ?? "gradient-based token saliency"}.
            </p>
          </Card>
        </div>
      </AnimateTab>
    </motion.div>
  );
}

function AnimateTab({ show, children }: { show: boolean; children: React.ReactNode }) {
  if (!show) return null;
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      {children}
    </motion.div>
  );
}

function AlertTriangleIcon() {
  return <span className="text-warning">▲</span>;
}

function MetaRow({ k, v, link }: { k: string; v: string; link?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="shrink-0 text-xs text-ink-muted">{k}</dt>
      <dd className="min-w-0 text-right text-sm text-ink-primary">
        {link && v !== "—" ? (
          <a href={v} target="_blank" rel="noopener noreferrer nofollow" className="break-all text-accent hover:underline">{v}</a>
        ) : (
          <span className="break-words">{v}</span>
        )}
      </dd>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="rounded-xl border border-line bg-bg-secondary/60 p-3">
      <p className="text-lg font-semibold text-ink-primary">{value ?? "—"}</p>
      <p className="text-[11px] text-ink-muted">{label}</p>
    </div>
  );
}
