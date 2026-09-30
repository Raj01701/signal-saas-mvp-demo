import type { Metadata } from "next";

import { MyReading } from "@/components/consumer/MyReading";

export const metadata: Metadata = {
  title: "My reading · Jyotish Platform",
  description: "Your day, month and year ahead in plain language, in English or Hindi.",
};

export default function MyReadingPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8">
      <MyReading />
    </main>
  );
}
