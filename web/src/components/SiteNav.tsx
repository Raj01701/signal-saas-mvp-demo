"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/workbench", label: "Workbench" },
  { href: "/panchanga", label: "Panchanga" },
  { href: "/match", label: "Match" },
] as const;

/** Site header with the main navigation; the current page is marked for assistive technology. */
export function SiteNav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-zinc-200 print:hidden dark:border-zinc-800">
      <nav aria-label="Main" className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
        {LINKS.map(({ href, label }) => {
          const current = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={current ? "page" : undefined}
              className={current ? "font-semibold text-amber-800 dark:text-amber-400" : "hover:underline"}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
