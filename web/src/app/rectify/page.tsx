import type { Metadata } from "next";

import { RectifyView } from "@/components/RectifyView";

export const metadata: Metadata = {
  title: "Birth-time rectification · Jyotish Platform",
  description: "Rank candidate birth times by how well their dashas fit the dated events of a life.",
};

export default function RectifyPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Birth-time rectification</h1>
      <RectifyView />
    </main>
  );
}
