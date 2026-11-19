import Link from "next/link";
import { ScanSearch } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-line bg-bg-secondary">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
        <div>
          <div className="flex items-center gap-2">
            <ScanSearch size={18} className="text-accent" />
            <span className="font-serif text-base font-semibold">VERITAS AI</span>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-ink-secondary">
            Intelligence beyond headlines. Transformer-powered analysis of news
            content, linguistic signals, and sources.
          </p>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Product</h4>
          <ul className="mt-3 space-y-2 text-sm text-ink-secondary">
            <li><Link className="hover:text-ink-primary" href="/analyze">Analyze</Link></li>
            <li><Link className="hover:text-ink-primary" href="/dashboard">Dashboard</Link></li>
            <li><Link className="hover:text-ink-primary" href="/history">History</Link></li>
            <li><Link className="hover:text-ink-primary" href="/model">Model Intelligence</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Transparency</h4>
          <ul className="mt-3 space-y-2 text-sm text-ink-secondary">
            <li>Model confidence ≠ factual truth</li>
            <li>Attribution ≠ evidence of falsity</li>
            <li>No independent fact-checking claims</li>
          </ul>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Status</h4>
          <p className="mt-3 text-sm text-ink-secondary">
            Predictions are statistical estimates produced by a machine-learning
            model trained on labeled news datasets.
          </p>
        </div>
      </div>
      <div className="border-t border-line py-5 text-center text-xs text-ink-muted">
        © {new Date().getFullYear()} VERITAS AI — For informational purposes only. Always verify with primary sources.
      </div>
    </footer>
  );
}
