import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ModelView } from "@/components/ModelView";

export const metadata = { title: "Model Intelligence — VERITAS AI" };

export default function ModelPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <ModelView />
      </main>
      <Footer />
    </div>
  );
}
