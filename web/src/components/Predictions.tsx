"use client";

import { useState } from "react";

import type { BirthRequest } from "@/components/BirthForm";
import { Status, title } from "@/components/common";
import { Yoga } from "@/components/Panels";
import { api, type Schemas } from "@/lib/api/client";
import { toneOf, yearly } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

const GROUPS: [Schemas["Category"], string][] = [
  ["lagna", "Rising sign"],
  ["nakshatra", "The Moon's nakshatra"],
  ["planet_in_sign", "Grahas in signs"],
  ["planet_in_house", "Grahas in houses"],
  ["lord_in_house", "House lords"],
];
const LEVELS = ["Mahadasha", "Antardasha", "Pratyantardasha"];
const RGB = { favourable: "22, 163, 74", mixed: "217, 119, 6", challenging: "220, 38, 38" } as const;

const month = (iso: string) =>
  new Date(`${iso.slice(0, 7)}-01T00:00:00Z`).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
const signed = (n: number) => (n > 0 ? `+${n.toFixed(2)}` : n.toFixed(2));

/** Natal readings: the classical result of each placement, grouped by kind. */
export function ReadingsPanel({ request }: { request: BirthRequest }) {
  const { data, error, loading } = useLoad(JSON.stringify(request), () =>
    api.POST("/v1/charts/readings", { body: request }),
  );
  return (
    <div className="grid gap-4">
      <Status loading={loading} error={error} />
      {data && (
        <>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            The classical result of each placement, in our own words with its source. All readings are drafts until a
            qualified Jyotishi reviews them.
          </p>
          {GROUPS.map(([category, heading]) => {
            const items = data.readings.filter((r) => r.category === category);
            if (items.length === 0) return null;
            return (
              <section key={category} aria-labelledby={`readings-${category}`}>
                <h3 id={`readings-${category}`} className="font-semibold">{heading}</h3>
                <ul className="divide-y divide-zinc-100 dark:divide-zinc-800" aria-label={heading}>
                  {items.map((r) => <Yoga key={r.id} yoga={r} />)}
                </ul>
              </section>
            );
          })}
        </>
      )}
    </div>
  );
}

function NowPanel({ request }: { request: BirthRequest }) {
  const { data, error, loading } = useLoad(`now ${JSON.stringify(request)}`, () =>
    api.POST("/v1/charts/period", { body: request }),
  );
  return (
    <section aria-labelledby="now-heading" className="grid gap-2 rounded-lg border border-zinc-200 p-3 text-sm dark:border-zinc-800">
      <h3 id="now-heading" className="font-semibold">Now</h3>
      <Status loading={loading} error={error} />
      {data && (
        <>
          <p>
            {data.dasha.map((p, i) => `${LEVELS[i]} of ${title(p.lords[p.lords.length - 1])} until ${p.end.slice(0, 10)}`).join("; ")}.
          </p>
          <ul className="grid gap-1" aria-label="Readings for now">
            {[...data.dasha_readings, ...data.transit_readings].map((r) => (
              <li key={r.id}>
                <span className="font-medium">{r.name}:</span> {r.summary}
              </li>
            ))}
          </ul>
          {data.cancelled.length > 0 && (
            <p className="text-xs text-zinc-600 dark:text-zinc-400">
              Obstructed by vedha: {data.cancelled.map((r) => r.name).join(", ")}.
            </p>
          )}
        </>
      )}
    </section>
  );
}

/** The prediction timeline: a heat map of life domains by year, and each domain's windows. */
export function TimelinePanel({ request }: { request: BirthRequest }) {
  const [domain, setDomain] = useState<string>("career");
  const { data, error, loading } = useLoad(JSON.stringify(request), () =>
    api.POST("/v1/charts/predictions", { body: request }),
  );
  const years = data ? [...new Set(data.months.map((m) => Number(m.slice(0, 4))))] : [];
  const selected = data?.domains.find((d) => d.domain === domain);
  return (
    <div className="grid gap-4">
      <NowPanel request={request} />
      <Status loading={loading} error={error} />
      {data && selected && (
        <>
          <div role="region" tabIndex={0} aria-label="Life-domain timeline" className="relative overflow-x-auto">
            <table className="border-separate border-spacing-px text-xs">
              <caption className="mb-2 text-left text-sm text-zinc-600 dark:text-zinc-400">
                Each cell is the strongest month of a year: darker means more emphasis; green favourable, amber mixed,
                red challenging. Choose a domain to see its windows.
              </caption>
              <thead>
                <tr>
                  <th scope="col"><span className="sr-only">Domain</span></th>
                  {years.map((y) => (
                    <th key={y} scope="col" className="px-0 text-left font-normal text-zinc-500">
                      {y % 10 === 0 ? y : <span className="sr-only">{y}</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.domains.map((d) => {
                  const cells = yearly(data.months, d);
                  const top = Math.max(0.01, ...d.scores);
                  return (
                    <tr key={d.domain}>
                      <th scope="row" className="pr-2 text-left font-medium whitespace-nowrap">
                        <button
                          type="button"
                          aria-pressed={d.domain === domain}
                          onClick={() => setDomain(d.domain)}
                          className={d.domain === domain ? "text-amber-800 underline dark:text-amber-400" : "hover:underline"}
                        >
                          {title(d.domain)}
                        </button>
                      </th>
                      {years.map((y) => {
                        const cell = cells.get(y) ?? { score: 0, tone: 0 };
                        const tone = toneOf(cell.tone);
                        const alpha = cell.score > 0 ? 0.12 + 0.88 * (cell.score / top) : 0.04;
                        return (
                          <td
                            key={y}
                            aria-label={`${y}: ${cell.score.toFixed(2)}, ${tone}`}
                            title={`${y}: ${cell.score.toFixed(2)}, ${tone}`}
                            className="h-5 w-3 min-w-3 rounded-sm"
                            style={{ backgroundColor: `rgba(${RGB[tone]}, ${alpha.toFixed(2)})` }}
                          />
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <section aria-labelledby="windows-heading" className="grid gap-2">
            <h3 id="windows-heading" className="font-semibold">
              {title(selected.domain)}: natal promise {selected.promise.score.toFixed(2)} (0.5 is neutral)
            </h3>
            <details className="text-sm">
              <summary className="cursor-pointer">Why this promise</summary>
              <ul className="mt-1 grid gap-0.5">
                {selected.promise.factors.map((f) => (
                  <li key={f.label}>
                    {f.label} <span className="text-zinc-500">{signed(f.score)}</span>
                  </li>
                ))}
              </ul>
            </details>
            <ol className="grid gap-2 text-sm" aria-label={`${title(selected.domain)} windows`}>
              {selected.windows.map((w) => (
                <li key={w.start} className="rounded-md border border-zinc-200 p-2 dark:border-zinc-800">
                  <details>
                    <summary className="cursor-pointer">
                      <span className="font-medium">
                        {month(w.start)} to {month(new Date(Date.parse(w.end) - 86_400_000).toISOString())}
                      </span>{" "}
                      <span className="text-zinc-600 dark:text-zinc-400">
                        · {w.confidence} · {toneOf(w.tone)} · {w.dasha.map(title).join(" / ")}
                      </span>
                    </summary>
                    <ul className="mt-2 grid gap-0.5">
                      {w.factors.map((f) => (
                        <li key={f.label}>
                          <span className="text-zinc-500">{f.kind}:</span> {f.label}
                        </li>
                      ))}
                    </ul>
                    {w.rules.length > 0 && (
                      <ul className="mt-2 grid gap-0.5 border-l-2 border-amber-600 pl-2">
                        {w.rules.map((r) => (
                          <li key={r.id}>
                            <span className="font-medium">{r.name}:</span> {r.summary}
                          </li>
                        ))}
                      </ul>
                    )}
                  </details>
                </li>
              ))}
            </ol>
          </section>
          <p className="text-xs text-zinc-500">{data.notes.join(" ")}</p>
        </>
      )}
    </div>
  );
}
