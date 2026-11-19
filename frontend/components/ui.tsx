import { ReactNode } from "react";

const styles: Record<string, string> = {
  Fake: "bg-danger/10 text-danger border-danger/30",
  Real: "bg-success/10 text-success border-success/30",
};

export function PredictionBadge({ prediction, confidence }: { prediction: string | null; confidence?: number | null }) {
  const key = prediction ?? "Unknown";
  const cls = styles[key] ?? "bg-bg-secondary text-ink-secondary border-line";
  return (
    <span className={`badge border ${cls}`}>
      {key}
      {confidence != null && (
        <span className="opacity-80">{Math.round(confidence * 100)}%</span>
      )}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card p-5 ${className}`}>{children}</div>;
}

export function CardTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-semibold text-ink-primary">{children}</h3>
      {hint && <p className="mt-0.5 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}
