import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { DashboardView } from "@/components/DashboardView";

export const metadata = { title: "Dashboard — VERITAS AI" };

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        <DashboardView />
      </main>
      <Footer />
    </div>
  );
}
