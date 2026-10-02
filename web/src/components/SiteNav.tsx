"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { setLang, useI18n } from "@/lib/i18n";

const LINKS = [
  { href: "/", key: "home" },
  { href: "/my", key: "my" },
  { href: "/panchanga", key: "panchanga" },
  { href: "/match", key: "match" },
  { href: "/workbench", key: "workbench" },
  { href: "/rectify", key: "rectify" },
] as const;

/** Site header: main navigation (the current page marked) and the language switch. */
export function SiteNav() {
  const pathname = usePathname();
  const { lang, t } = useI18n();
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  return (
    <header className="border-b border-zinc-200 print:hidden dark:border-zinc-800">
      <nav aria-label={t.nav.main} className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
        {LINKS.map(({ href, key }) => {
          const current = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={current ? "page" : undefined}
              className={current ? "font-semibold text-amber-800 dark:text-amber-400" : "hover:underline"}
            >
              {t.nav[key]}
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => setLang(lang === "hi" ? "en" : "hi")}
          aria-label={t.nav.switchLabel}
          lang={lang === "hi" ? "en" : "hi"}
          className="ml-auto rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700"
        >
          {t.nav.switchTo}
        </button>
      </nav>
    </header>
  );
}
