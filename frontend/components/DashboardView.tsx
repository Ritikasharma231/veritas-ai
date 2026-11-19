"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Activity, Clock, FileSearch, Gauge, PieChart as PieIcon, ScanSearch } from "lucide-react";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { Card, CardTitle, PredictionBadge } from "./ui";

const tooltipStyle = {
  background: "#171C27",
  border: "1px solid #262C3A",
  borderRadius: 10,
  fontSize: 12,
};

export function DashboardView() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.dashboardStats()
      .then(setStats)
      .catch((e) => setError(e?.message ?? "Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }
  if (error || !stats) {
    return (
      <Card className="p-8 text-center">
        <p className="text-danger">{error ?? "No data"}</p>
        <p className="mt-2 text-sm text-ink-muted">Ensure the backend API is running.</p>
      </Card>
    );
  }

  const dist = stats.classification_distribution;
  const distData = Object.entries(dist).map(([name, value]) => ({
    name, value,
    fill: name.toLowerCase().includes("fake") ? "#E16D78" : "#38B98A",
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-semibold">Dashboard</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            Live statistics from stored analyses · {stats.data_source === "live" ? "database" : stats.data_source}
          </p>
        </div>
        <Link href="/analyze" className="btn-primary">
          <ScanSearch size={15} /> New analysis
        </Link>
      </div>

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi icon={FileSearch} label="Total analyses" value={stats.total_analyses} />
        <Kpi icon={Gauge} label="Avg confidence" value={stats.avg_confidence != null ? `${Math.round(stats.avg_confidence * 100)}%` : "—"} />
        <Kpi icon={Clock} label="Avg inference" value={stats.avg_inference_ms != null ? `${stats.avg_inference_ms} ms` : "—"} />
        <Kpi icon={Activity} label="Fake flagged" value={dist["Fake"] ?? 0} accent="danger" />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Daily trend */}
        <Card className="lg:col-span-2">
          <CardTitle hint="Analyses per day, last 14 days">Analysis trend</CardTitle>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats.daily_trend} margin={{ left: -18, right: 8, top: 4 }}>
                <defs>
                  <linearGradient id="gFake" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#E16D78" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#E16D78" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gReal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#38B98A" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#38B98A" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--c-line))" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#9299A8", fontSize: 10 }} tickFormatter={(d: string) => d.slice(5)} axisLine={false} tickLine={false} interval={2} />
                <YAxis tick={{ fill: "#9299A8", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "#F5F6FA" }} />
                <Area type="monotone" dataKey="Fake" stackId="1" stroke="#E16D78" fill="url(#gFake)" strokeWidth={1.5} />
                <Area type="monotone" dataKey="Real" stackId="1" stroke="#38B98A" fill="url(#gReal)" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex items-center gap-4 text-xs text-ink-secondary">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-danger" /> Fake-flagged</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-success" /> Real-classified</span>
          </div>
        </Card>

        {/* Distribution */}
        <Card>
          <CardTitle hint="Share of completed analyses by class">Classification distribution</CardTitle>
          {distData.length === 0 ? (
            <p className="py-10 text-center text-sm text-ink-muted">No completed analyses yet.</p>
          ) : (
            <>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={distData} margin={{ left: -24, right: 4 }}>
                    <XAxis dataKey="name" tick={{ fill: "#9299A8", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#9299A8", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(139,140,246,0.06)" }} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {distData.map((d) => <Cell key={d.name} fill={d.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 space-y-1.5">
                {distData.map((d) => (
                  <div key={d.name} className="flex items-center justify-between text-sm">
                    <PredictionBadge prediction={d.name} />
                    <span className="font-medium text-ink-primary">{d.value}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Confidence histogram */}
        <Card>
          <CardTitle hint="Distribution of top-class confidence">Confidence distribution</CardTitle>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.confidence_histogram} margin={{ left: -24, right: 4 }}>
                <XAxis dataKey="range" tick={{ fill: "#9299A8", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#9299A8", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(139,140,246,0.06)" }} />
                <Bar dataKey="count" fill="#8B8CF6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Recent activity */}
        <Card className="lg:col-span-2">
          <CardTitle hint="Most recent stored analyses">Recent activity</CardTitle>
          {stats.recent_activity.length === 0 ? (
            <p className="py-8 text-center text-sm text-ink-muted">No analyses yet — run your first one.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-line">
                    <th className="th">Title</th>
                    <th className="th">Prediction</th>
                    <th className="th">Confidence</th>
                    <th className="th">When</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_activity.map((a) => (
                    <tr key={a.id} className="border-b border-line/60 last:border-0 hover:bg-bg-secondary/50">
                      <td className="td max-w-[280px] truncate">{a.title}</td>
                      <td className="td"><PredictionBadge prediction={a.prediction} confidence={a.confidence} /></td>
                      <td className="td font-mono text-xs">{a.confidence != null ? `${Math.round(a.confidence * 100)}%` : "—"}</td>
                      <td className="td text-xs text-ink-muted">{new Date(a.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Kpi({ icon: Icon, label, value, accent }: { icon: any; label: string; value: string | number; accent?: "danger" }) {
  return (
    <Card className="flex items-center gap-4">
      <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${accent === "danger" ? "bg-danger/10 text-danger" : "bg-accent-soft text-accent"}`}>
        <Icon size={19} />
      </div>
      <div>
        <p className="text-2xl font-semibold leading-none text-ink-primary">{value}</p>
        <p className="mt-1 text-xs text-ink-muted">{label}</p>
      </div>
    </Card>
  );
}
