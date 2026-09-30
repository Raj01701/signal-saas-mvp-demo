"use client";

import { useI18n } from "@/lib/i18n";

/** A page's main heading in the interface language. */
export function PageHeading({ page }: { page: "panchanga" | "match" }) {
  const { t } = useI18n();
  return <h1 className="mb-6 text-2xl font-semibold tracking-tight">{t[page].title}</h1>;
}
