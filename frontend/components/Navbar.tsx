"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, Moon, Sun, ScanSearch } from "lucide-react";
import { useTheme } from "./ThemeProvider";

const links = [
  { href: "/", label: "Overview" },
  { href: "/analyze", label: "Analyze" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/history", label: "History" },
  { href: "/model", label: "Model" },
];

export function Navbar() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-bg/80 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white">
            <ScanSearch className="h-4.5 w-4.5" size={18} />
          </span>
          <span className="font-serif text-lg font-semibold tracking-tight">VERITAS</span>
          <span className="rounded-md bg-accent-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-accent">
            AI
          </span>
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-lg px-3.5 py-2 text-sm transition-colors ${
                  active ? "bg-accent-soft text-accent" : "text-ink-secondary hover:text-ink-primary"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggle}
            className="btn-ghost !px-3 !py-2"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <Link href="/analyze" className="btn-primary hidden !py-2 md:inline-flex">
            Analyze News
          </Link>
          <button className="btn-ghost !px-3 !py-2 md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
            <Menu size={16} />
          </button>
        </div>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-line md:hidden"
          >
            <div className="flex flex-col gap-1 px-4 py-3">
              {links.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className={`rounded-lg px-3 py-2.5 text-sm ${
                    pathname === l.href ? "bg-accent-soft text-accent" : "text-ink-secondary"
                  }`}
                >
                  {l.label}
                </Link>
              ))}
              <Link href="/analyze" className="btn-primary mt-1" onClick={() => setOpen(false)}>
                Analyze News
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
