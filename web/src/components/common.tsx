/** Small pieces shared by the workbench, panchanga and matching views. */

import type { Schemas } from "@/lib/api/client";

export const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replaceAll("_", " ");
export const TEXTS: Record<string, string> = {
  bphs: "Brihat Parashara Hora Shastra",
  brihat_jataka: "Brihat Jataka",
  saravali: "Saravali",
  phaladeepika: "Phaladeepika",
  jataka_parijata: "Jataka Parijata",
  uttara_kalamrita: "Uttara Kalamrita",
  laghu_parashari: "Laghu Parashari",
  raman_300: "B.V. Raman, Three Hundred Important Combinations",
  raman_how_to_judge: "B.V. Raman, How to Judge a Horoscope",
  raman_muhurtha: "B.V. Raman, Muhurtha (Electional Astrology)",
  maitreya: "Maitreya astrology software, Asta Koota documentation",
  popular_practice: "Contemporary practice",
};

export function Status({ loading, error }: { loading: boolean; error?: string }) {
  if (loading) return <p className="text-sm text-zinc-500" role="status">Calculating…</p>;
  if (error) return <p className="text-sm text-red-700 dark:text-red-400" role="status">{error}</p>;
  return null;
}

export function Citation({ c }: { c: Schemas["CitationOut"] }) {
  const where = [c.chapter !== null && `ch. ${c.chapter}`, c.verses && `v. ${c.verses}`, c.locator]
    .filter(Boolean)
    .join(", ");
  return (
    <li>
      {TEXTS[c.text] ?? c.text}
      {c.edition ? ` (${c.edition} edition)` : ""}
      {where ? `: ${where}` : ""}
      {!c.verified && <span className="ml-1 rounded bg-zinc-100 px-1 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">unverified</span>}
    </li>
  );
}
