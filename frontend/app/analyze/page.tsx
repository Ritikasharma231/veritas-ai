import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { AnalyzeWorkspace } from "@/components/AnalyzeWorkspace";

export const metadata = { title: "Analyze — VERITAS AI" };

export default function AnalyzePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <AnalyzeWorkspace />
      </main>
      <Footer />
    </div>
  );
}
