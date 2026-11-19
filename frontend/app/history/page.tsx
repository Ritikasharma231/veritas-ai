import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { HistoryView } from "@/components/HistoryView";

export const metadata = { title: "History — VERITAS AI" };

export default function HistoryPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        <HistoryView />
      </main>
      <Footer />
    </div>
  );
}
