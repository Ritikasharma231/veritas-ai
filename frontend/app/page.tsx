import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
  ArrowRight, BrainCircuit, FileSearch, LineChart, ShieldCheck,
  Languages, Link2, History, AlertTriangle, CheckCircle2, XCircle,
} from "lucide-react";
import { LiveStatus } from "@/components/LiveStatus";
import { SamplePreview } from "@/components/SamplePreview";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(800px_400px_at_50%_0%,rgb(var(--c-accent)/0.08),transparent_70%)]" />
        <div className="mx-auto max-w-5xl px-4 pb-20 pt-20 text-center sm:px-6 sm:pt-28">
          <LiveStatus />
          <h1 className="mt-6 font-serif text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
            Truth deserves more than{" "}
            <span className="text-accent">a headline.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-ink-secondary">
            Analyze news, uncover linguistic patterns, investigate claims, and
            understand the signals behind information with transformer-powered
            intelligence.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/analyze" className="btn-primary px-6 py-3 text-base">
              Analyze News <ArrowRight size={16} />
            </Link>
            <Link href="/model" className="btn-ghost px-6 py-3 text-base">
              How the model works
            </Link>
          </div>
          <p className="mt-6 text-xs text-ink-muted">
            Predictions are statistical estimates — not verdicts of factual truth.
          </p>
        </div>
      </section>

      {/* Preview */}
      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <SamplePreview />
      </section>

      {/* Features */}
      <section className="border-t border-line bg-bg-secondary/50">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <h2 className="text-center font-serif text-3xl font-semibold">Beyond a yes/no answer</h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-ink-secondary">
            VERITAS decomposes an article into model confidence, linguistic
            signals, and token-level attribution — so you can see <em>why</em>.
          </p>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: BrainCircuit, title: "Transformer classification", desc: "A fine-tuned transformer model scores content against learned real/fake patterns from labeled news corpora." },
              { icon: Languages, title: "Linguistic signal analysis", desc: "Sensational wording, urgency, clickbait phrasing, punctuation and vocabulary diversity — presented as signals, not proof." },
              { icon: FileSearch, title: "Explainable attribution", desc: "Gradient-based token saliency highlights which words most influenced the prediction." },
              { icon: Link2, title: "URL ingestion", desc: "Paste a link; we securely fetch and extract readable article text with SSRF protections." },
              { icon: History, title: "Analysis history", desc: "Every analysis is stored, searchable, filterable, and exportable for review." },
              { icon: LineChart, title: "Platform analytics", desc: "Live dashboard of classification distribution, confidence trends, and model latency." },
            ].map((f) => (
              <div key={f.title} className="card p-6 transition-colors hover:border-accent/40">
                <f.icon size={20} className="text-accent" />
                <h3 className="mt-4 font-medium text-ink-primary">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <h2 className="text-center font-serif text-3xl font-semibold">How detection works</h2>
        <div className="mt-12 grid gap-8 md:grid-cols-4">
          {[
            { n: "01", t: "Ingest", d: "Paste text, a headline, or a URL. Content is cleaned and normalized without destroying linguistic signals." },
            { n: "02", t: "Encode", d: "A transformer tokenizer converts the text into contextual token embeddings with attention masking." },
            { n: "03", t: "Classify", d: "The fine-tuned model outputs calibrated probabilities across learned classes." },
            { n: "04", t: "Explain", d: "Token attribution and rule-based linguistic analysis surface the signals behind the score." },
          ].map((s) => (
            <div key={s.n} className="relative">
              <span className="font-serif text-4xl font-semibold text-accent/40">{s.n}</span>
              <h3 className="mt-2 font-medium">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-secondary">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Honesty / limitations */}
      <section className="border-t border-line bg-bg-secondary/50">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2">
          <div>
            <div className="flex items-center gap-2 text-warning">
              <AlertTriangle size={18} />
              <h2 className="font-serif text-2xl font-semibold text-ink-primary">Read this before trusting any score</h2>
            </div>
            <ul className="mt-6 space-y-4 text-sm leading-relaxed text-ink-secondary">
              <li className="flex gap-3"><XCircle size={16} className="mt-0.5 shrink-0 text-danger" /> A high "Fake" score means the text resembles fabricated-news patterns in training data — it does not prove the claims are false.</li>
              <li className="flex gap-3"><XCircle size={16} className="mt-0.5 shrink-0 text-danger" /> Real news can be rated "Fake" and fabricated content can slip through, especially satire, opinion, and non-English text.</li>
              <li className="flex gap-3"><XCircle size={16} className="mt-0.5 shrink-0 text-danger" /> The model has no access to external facts and does not independently verify claims.</li>
            </ul>
          </div>
          <div className="card p-6">
            <div className="flex items-center gap-2 text-success">
              <ShieldCheck size={18} />
              <h3 className="font-medium">What we do to stay honest</h3>
            </div>
            <ul className="mt-5 space-y-3 text-sm text-ink-secondary">
              {[
                "Model unavailable? The API returns a clear 503 — never a fabricated prediction.",
                "URL extraction failure is reported explicitly; we never claim to have analyzed what we couldn't read.",
                "Every result page carries a disclaimer and links to primary-source verification.",
                "Metrics on the Model page come from actual evaluation runs — or are shown as absent.",
              ].map((t) => (
                <li key={t} className="flex gap-3">
                  <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-success" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
        <h2 className="font-serif text-3xl font-semibold">Start analyzing</h2>
        <p className="mx-auto mt-3 max-w-lg text-ink-secondary">
          Paste an article, try a URL, or explore the dashboard to see how the
          platform performs on your own content.
        </p>
        <Link href="/analyze" className="btn-primary mt-8 px-8 py-3.5 text-base">
          Open the Analysis Workspace <ArrowRight size={16} />
        </Link>
      </section>

      <Footer />
    </div>
  );
}
