"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Search, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import type { AnalysisListItem, AnalysisListResponse, AnalysisResponse } from "@/lib/types";
import { Card, PredictionBadge } from "./ui";
import { ResultsPanel } from "./ResultsPanel";

export function HistoryView() {
  const [data, setData] = useState<AnalysisListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [qInput, setQInput] = useState("");
  const [prediction, setPrediction] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sort, setSort] = useState<"asc" | "desc">("desc");
  const [selected, setSelected] = useState<AnalysisResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .listAnalyses({ page, page_size: 15, q: q || undefined, prediction: prediction || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined, sort })
      .then(setData)
      .catch((e) => setError(e?.message ?? "Failed to load history"));
  }, [page, q, prediction, dateFrom, dateTo, sort]);

  useEffect(() => { load(); }, [load]);

  const openDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const d = await api.getAnalysis(id);
      setSelected(d);
    } finally {
      setDetailLoading(false);
    }
  };

  const remove = async (id: string) => {
    await api.deleteAnalysis(id);
    setData((d) => d && { ...d, items: d.items.filter((i) => i.id !== id), total: d.total - 1 });
    if (selected?.id === id) setSelected(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl font-semibold">Analysis History</h1>
        <p className="mt-1 text-sm text-ink-secondary">{data ? `${data.total.toLocaleString()} stored analyses` : "Loading…"}</p>
      </div>

      {/* Filters */}
      <Card className="flex flex-wrap items-center gap-3 p-4">
        <form
          className="flex min-w-[220px] flex-1 items-center gap-2"
          onSubmit={(e) => { e.preventDefault(); setQ(qInput); setPage(1); }}
        >
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
              placeholder="Search title or text…"
              className="input !pl-9"
            />
          </div>
          <button className="btn-ghost" type="submit">Search</button>
        </form>
        <select value={prediction} onChange={(e) => { setPrediction(e.target.value); setPage(1); }} className="input !w-auto">
          <option value="">All classes</option>
          <option value="Fake">Fake</option>
          <option value="Real">Real</option>
        </select>
        <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} className="input !w-auto" title="From" />
        <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} className="input !w-auto" title="To" />
        <select value={sort} onChange={(e) => setSort(e.target.value as "asc" | "desc")} className="input !w-auto">
          <option value="desc">Newest first</option>
          <option value="asc">Oldest first</option>
        </select>
        {(q || prediction || dateFrom || dateTo) && (
          <button
            className="btn-ghost !px-3"
            onClick={() => { setQ(""); setQInput(""); setPrediction(""); setDateFrom(""); setDateTo(""); setPage(1); }}
          >
            <X size={14} /> Reset
          </button>
        )}
      </Card>

      {error && <Card className="border-danger/40 p-4 text-sm text-danger">{error}</Card>}

      <div className="grid gap-6 xl:grid-cols-5">
        {/* List */}
        <Card className="overflow-hidden p-0 xl:col-span-2">
          {!data ? (
            <div className="p-8 text-center text-sm text-ink-muted">Loading…</div>
          ) : data.items.length === 0 ? (
            <div className="p-10 text-center">
              <p className="text-sm text-ink-secondary">No analyses match your filters.</p>
              <Link href="/analyze" className="btn-primary mt-4 !py-2">Run an analysis</Link>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {data.items.map((a: AnalysisListItem) => (
                <li key={a.id} className="group flex items-center gap-3 px-4 py-3.5 hover:bg-bg-secondary/60">
                  <button onClick={() => openDetail(a.id)} className="min-w-0 flex-1 text-left">
                    <p className="truncate text-sm font-medium text-ink-primary">{a.title || "Untitled analysis"}</p>
                    <p className="mt-0.5 text-xs text-ink-muted">
                      {new Date(a.created_at).toLocaleString()} · {a.input_type}
                    </p>
                  </button>
                  <PredictionBadge prediction={a.prediction} confidence={a.confidence} />
                  <button
                    onClick={() => remove(a.id)}
                    className="rounded-lg p-1.5 text-ink-muted opacity-0 transition-opacity hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
              <span className="text-xs text-ink-muted">Page {data.page} of {data.pages}</span>
              <div className="flex gap-2">
                <button className="btn-ghost !px-3 !py-1.5" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                  <ChevronLeft size={14} />
                </button>
                <button className="btn-ghost !px-3 !py-1.5" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </Card>

        {/* Detail */}
        <div className="xl:col-span-3">
          {detailLoading ? (
            <Card className="flex min-h-[300px] items-center justify-center">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            </Card>
          ) : selected ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-serif text-lg font-semibold">Analysis detail</h2>
                <button onClick={() => setSelected(null)} className="btn-ghost !px-3 !py-1.5 text-xs">
                  <X size={13} /> Close
                </button>
              </div>
              <ResultsPanel result={selected} />
            </div>
          ) : (
            <Card className="flex min-h-[300px] flex-col items-center justify-center p-8 text-center">
              <p className="text-sm text-ink-secondary">Select an analysis to view its full results, explanation, and signals.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
