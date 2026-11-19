"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ModelInfo } from "@/lib/types";
import { Card, CardTitle } from "./ui";
import { AlertTriangle, BrainCircuit, CheckCircle2, Cpu, Database, XCircle } from "lucide-react";

interface MetricsPayload {
  available: boolean;
  metrics?: Record<string, any>;
  source?: string;
  detail?: string;
}

export function ModelView() {
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [metrics, setMetrics] = useState<MetricsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.modelInfo(), api.modelMetrics()])
      .then(([i, m]) => { setInfo(i); setMetrics(m); })
      .catch((e) => setError(e?.message ?? "Failed to load model info"));
  }, []);

  if (error) return <Card className="p-8 text-center text-danger">{error}</Card>;
  if (!info) {
    return <div className="flex min-h-[300px] items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" /></div>;
  }

  const m = metrics?.metrics;
  const testMetrics = m?.test ?? m;
  const labels: string[] = (testMetrics?.labels as string[]) ?? info.labels;
  const cm: number[][] | undefined = testMetrics?.confusion_matrix;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl font-semibold">Model Intelligence</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Architecture, training provenance, and measured performance — only real values are shown.
        </p>
      </div>

      {/* Status cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="flex items-center gap-4">
          <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${info.available ? "bg-success/10 text-success" : "bg-danger/10 text-danger"}`}>
            {info.available ? <CheckCircle2 size={19} /> : <XCircle size={19} />}
          </div>
          <div>
            <p className="text-sm font-medium text-ink-primary">{info.available ? "Model loaded" : "Model unavailable"}</p>
            <p className="text-xs text-ink-muted">{info.device}</p>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-soft text-accent"><BrainCircuit size={19} /></div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink-primary" title={info.model_name}>{info.model_name}</p>
            <p className="text-xs text-ink-muted">{info.locally_finetuned ? "Locally fine-tuned checkpoint" : "Pretrained checkpoint (inference only)"}</p>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-warning/10 text-warning"><Database size={19} /></div>
          <div>
            <p className="text-sm font-medium text-ink-primary">Classes: {info.labels.join(" / ") || "—"}</p>
            <p className="text-xs text-ink-muted">{info.hf_id ? `HF: ${info.hf_id}` : info.model_path ?? ""}</p>
          </div>
        </Card>
      </div>

      {info.error && (
        <Card className="border-danger/40">
          <p className="flex items-start gap-2 text-sm text-danger"><AlertTriangle size={15} className="mt-0.5" /> {info.error}</p>
        </Card>
      )}

      {/* Metrics */}
      <Card>
        <CardTitle hint={metrics?.source ? `Source: ${metrics.source}` : undefined}>
          Evaluation metrics {m?.trained_at ? `· trained ${new Date(m.trained_at).toLocaleDateString()}` : ""}
        </CardTitle>
        {!m ? (
          <div className="rounded-xl border border-dashed border-line p-6 text-center">
            <Cpu size={20} className="mx-auto text-ink-muted" />
            <p className="mt-2 text-sm text-ink-secondary">
              {metrics?.available === false
                ? metrics.detail ?? "No evaluation report found."
                : "No evaluation metrics available yet."}
            </p>
            <p className="mt-1 text-xs text-ink-muted">
              Run <code className="rounded bg-bg-secondary px-1.5 py-0.5">python -m ml.training.train_transformer</code> then{" "}
              <code className="rounded bg-bg-secondary px-1.5 py-0.5">python -m ml.evaluation.evaluate</code> to produce them.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <Metric label="Accuracy" value={testMetrics?.accuracy} />
              <Metric label="Precision (macro)" value={testMetrics?.precision_macro} />
              <Metric label="Recall (macro)" value={testMetrics?.recall_macro} />
              <Metric label="F1 (macro)" value={testMetrics?.f1_macro} />
              <Metric label="F1 (weighted)" value={testMetrics?.f1_weighted} />
              <Metric label="ROC-AUC" value={testMetrics?.roc_auc} />
            </div>

            {cm && labels.length >= 2 && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-muted">Confusion matrix (test set)</p>
                <div className="inline-block overflow-hidden rounded-xl border border-line">
                  <table className="text-sm">
                    <thead>
                      <tr className="bg-bg-secondary">
                        <th className="px-4 py-2 text-left text-xs text-ink-muted">Actual → Predicted</th>
                        {labels.map((l) => <th key={l} className="px-4 py-2 text-xs font-medium text-ink-secondary">{l}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {cm.map((row, i) => (
                        <tr key={i} className="border-t border-line">
                          <td className="px-4 py-2 text-xs font-medium text-ink-secondary">{labels[i] ?? i}</td>
                          {row.map((v, j) => {
                            const total = row.reduce((a, b) => a + b, 0) || 1;
                            const intensity = v / total;
                            return (
                              <td key={j} className="px-4 py-2 text-center font-mono text-sm"
                                style={{ background: `rgba(139,140,246,${0.08 + intensity * 0.35})`, color: intensity > 0.5 ? "#fff" : "inherit" }}>
                                {v}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {testMetrics?.per_class && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-muted">Per-class performance</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {Object.entries(testMetrics.per_class as Record<string, any>).map(([name, s]: [string, any]) => (
                    <div key={name} className="rounded-xl border border-line bg-bg-secondary/60 p-4">
                      <p className="text-sm font-medium text-ink-primary">{name}</p>
                      <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                        <MiniStat label="P" value={s.precision} />
                        <MiniStat label="R" value={s.recall} />
                        <MiniStat label="F1" value={s.f1} />
                      </div>
                      <p className="mt-2 text-[11px] text-ink-muted">support: {s.support}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Provenance */}
      <Card>
        <CardTitle>Training provenance</CardTitle>
        <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          <Prov k="Model source" v={info.hf_id ?? info.model_path ?? "—"} />
          <Prov k="Checkpoint type" v={info.locally_finetuned ? "Fine-tuned locally" : "Pretrained (no local fine-tuning)"} />
          <Prov k="Device" v={info.device} />
          <Prov k="Labels" v={(info.labels ?? []).join(", ")} />
          {m?.model && <Prov k="Base model" v={m.model} />}
          {m?.train_rows != null && <Prov k="Train rows" v={String(m.train_rows)} />}
          {m?.test_rows != null && <Prov k="Test rows" v={String(m.test_rows)} />}
          {m?.train_seconds != null && <Prov k="Train time" v={`${Math.round(m.train_seconds / 60)} min`} />}
        </dl>
      </Card>

      {/* Limitations */}
      <Card className="border-warning/30">
        <CardTitle hint="Always shown alongside predictions">
          <span className="flex items-center gap-2 text-warning"><AlertTriangle size={14} /> Known limitations</span>
        </CardTitle>
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink-secondary">
          <li>Trained on English-language news datasets; performance degrades on other languages and domains.</li>
          <li>Binary real/fake framing cannot represent nuance: satire, opinion, sponsored content, and evolving events.</li>
          <li>Dataset labels reflect publisher/source reputation and fact-check outcomes at collection time — label noise exists.</li>
          <li>The model detects stylistic patterns, not factual accuracy. It does not verify claims against external sources.</li>
          <li>Adversarial or heavily edited text can evade detection; confidence scores are not calibrated guarantees.</li>
        </ul>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | undefined | null }) {
  return (
    <div className="rounded-xl border border-line bg-bg-secondary/60 p-3.5 text-center">
      <p className="text-xl font-semibold text-ink-primary">{value != null ? (value * 100).toFixed(1) + "%" : "—"}</p>
      <p className="mt-1 text-[11px] text-ink-muted">{label}</p>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="font-mono text-sm font-semibold text-accent">{(value * 100).toFixed(0)}%</p>
      <p className="text-[10px] text-ink-muted">{label}</p>
    </div>
  );
}

function Prov({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line/60 py-2 last:border-0">
      <dt className="text-ink-muted">{k}</dt>
      <dd className="text-right font-medium text-ink-primary">{v}</dd>
    </div>
  );
}
