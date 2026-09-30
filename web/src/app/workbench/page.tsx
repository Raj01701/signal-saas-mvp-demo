import type { Metadata } from "next";

import { Workbench } from "@/components/Workbench";

export const metadata: Metadata = {
  title: "Workbench · Jyotish Platform",
  description: "Birth chart, divisional charts, planets and dashas, calculated to the arcsecond.",
};

export default function WorkbenchPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Astrologer workbench</h1>
      <Workbench />
    </main>
  );
}
