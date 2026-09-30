"use client";

import Link from "next/link";

import { useI18n } from "@/lib/i18n";

export function SiteFooter() {
  const { t } = useI18n();
  return (
    <footer className="mt-auto border-t border-zinc-200 print:hidden dark:border-zinc-800">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-xs text-zinc-600 dark:text-zinc-400">
        <span>{t.footer.note}</span>
        <Link href="/privacy" className="underline">{t.footer.privacy}</Link>
        <Link href="/terms" className="underline">{t.footer.terms}</Link>
      </div>
    </footer>
  );
}
