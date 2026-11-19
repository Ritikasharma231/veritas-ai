"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Activity } from "lucide-react";

export function LiveStatus() {
  const [state, setState] = useState<{ ok: boolean; model: boolean } | null>(null);

  useEffect(() => {
    api.health()
      .then((h) => setState({ ok: h.status === "ok", model: h.model_available }))
      .catch(() => setState({ ok: false, model: false }));
  }, []);

  if (!state) return null;
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-line bg-bg-card px-3.5 py-1.5 text-xs text-ink-secondary">
      <Activity size={13} className={state.ok ? "text-success" : "text-danger"} />
      API {state.ok ? "operational" : "unreachable"}
      <span className="text-ink-muted">·</span>
      Model {state.model ? "loaded" : "unavailable"}
    </div>
  );
}
