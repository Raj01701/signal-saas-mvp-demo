import type { Metadata } from "next";

import { MatchView } from "@/components/MatchView";

export const metadata: Metadata = {
  title: "Horoscope matching · Jyotish Platform",
  description: "Ashtakoota points with Nadi, Bhakoot and Gana doshas, the ten South Indian kutas and Kuja dosha.",
};

export default function MatchPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Horoscope matching</h1>
      <MatchView />
    </main>
  );
}
