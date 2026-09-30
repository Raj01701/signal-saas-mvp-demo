/** Formatting helpers for the panchanga and matching views. */

import type { Schemas } from "@/lib/api/client";

/** "UTC+05:30" for an offset in seconds. */
export function offsetLabel(seconds: number): string {
  const minutes = Math.round(Math.abs(seconds) / 60);
  const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mm = String(minutes % 60).padStart(2, "0");
  return `UTC${seconds < 0 ? "−" : "+"}${hh}:${mm}`;
}

/**
 * Local clock time (to the nearest minute) of a UTC ISO instant, followed by
 * the local date when that differs from ``day``.
 */
export function clock(iso: string, offsetSeconds: number, day: string): string {
  const local = new Date(Date.parse(iso) + offsetSeconds * 1000 + 30_000).toISOString();
  const time = local.slice(11, 16);
  if (local.slice(0, 10) === day) return time;
  const date = new Date(`${local.slice(0, 10)}T00:00:00Z`);
  return `${time}, ${date.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })}`;
}

/** A day as "30 September 2026". */
export function longDate(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

const KUJA_FROM: Record<string, string> = {
  "dosha.kuja_lagna": "the lagna",
  "dosha.kuja_moon": "the Moon",
  "dosha.kuja_venus": "Venus",
};

export const points = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

/** Mars's placement for Kuja dosha in words: which reference points it counts from, and which exceptions cancel. */
export function kujaText(kuja: Schemas["KujaOut"]): string {
  const from = (ids: string[]) => {
    const names = ids.map((id) => KUJA_FROM[id] ?? id);
    return names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)}` : names[0];
  };
  const parts = [
    kuja.present.length > 0 && `dosha from ${from(kuja.present)}`,
    kuja.cancelled.length > 0 && `from ${from(kuja.cancelled)} the dosha is cancelled by an exception`,
  ].filter(Boolean);
  return `${kuja.manglik ? "Manglik" : "Not manglik"}${parts.length > 0 ? ` (${parts.join("; ")})` : ""}`;
}

/** Whether a prediction tone (-1 to 1) reads as favourable, mixed or challenging. */
export const toneOf = (t: number) => (t > 0.15 ? "favourable" : t < -0.15 ? "challenging" : "mixed");

/** The strongest month of each year of a timeline: its score and tone. */
export function yearly(
  months: string[],
  timeline: { scores: number[]; tones: number[] },
): Map<number, { score: number; tone: number }> {
  const out = new Map<number, { score: number; tone: number }>();
  months.forEach((m, i) => {
    const year = Number(m.slice(0, 4));
    const best = out.get(year);
    if (!best || timeline.scores[i] > best.score) out.set(year, { score: timeline.scores[i], tone: timeline.tones[i] });
  });
  return out;
}
