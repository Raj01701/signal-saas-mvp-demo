import type { Metadata } from "next";

import { PageHeading } from "@/components/PageHeading";
import { PanchangaView } from "@/components/PanchangaView";

export const metadata: Metadata = {
  title: "Panchanga · Jyotish Platform",
  description: "Tithi, nakshatra, yoga and karana with end times, the lunar calendar and muhurtas for any date and place.",
};

export default function PanchangaPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8">
      <PageHeading page="panchanga" />
      <PanchangaView />
    </main>
  );
}
