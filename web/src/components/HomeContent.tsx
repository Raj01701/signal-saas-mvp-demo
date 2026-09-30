"use client";

import Link from "next/link";

import { useI18n } from "@/lib/i18n";

export function HomeContent() {
  const { t } = useI18n();
  const h = t.home;
  const secondary = "rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold dark:border-zinc-700";
  return (
    <main className="mx-auto flex max-w-3xl flex-1 flex-col justify-center gap-6 px-4 py-16">
      <p className="text-sm font-medium uppercase tracking-widest text-amber-700 dark:text-amber-400">{h.kicker}</p>
      <h1 className="text-4xl font-semibold tracking-tight">{h.title}</h1>
      <p className="text-lg leading-8 text-zinc-600 dark:text-zinc-300">{h.body}</p>
      <div className="flex flex-wrap gap-3">
        <Link href="/my" className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800">
          {h.start}
        </Link>
        <Link href="/panchanga" className={secondary}>{h.panchanga}</Link>
        <Link href="/match" className={secondary}>{h.match}</Link>
        <Link href="/workbench" className={secondary}>{h.pro}</Link>
      </div>
    </main>
  );
}
