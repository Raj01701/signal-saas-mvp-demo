"use client";

import { useState } from "react";

import type { BirthRequest } from "@/components/BirthForm";
import { Citation, Status, title } from "@/components/common";
import { api, type Schemas } from "@/lib/api/client";
import { formatLongitude } from "@/lib/angles";
import { jdToDate, useLoad } from "@/lib/use-load";

const SIGNS = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"];

function Yoga({ yoga, cancelled }: { yoga: Schemas["YogaOut"]; cancelled?: boolean }) {
  return (
    <li className="py-2">
      <details>
        <summary className="cursor-pointer">
          <span className="font-medium">{yoga.name}</span>
          <span className="ml-2 text-xs text-zinc-500">
            {title(yoga.category)} · {yoga.provenance} · {yoga.polarity}
            {cancelled ? " · cancelled" : ""}
          </span>
          <p className="text-sm text-zinc-700 dark:text-zinc-300">{yoga.summary}</p>
        </summary>
        <div className="mt-2 grid gap-2 border-l-2 border-amber-600 pl-3 text-sm">
          <div>
            <p className="font-semibold">Why it applies</p>
            <ul className="font-mono text-xs">{yoga.evidence.map((e) => <li key={e}>{e}</li>)}</ul>
          </div>
          {cancelled && yoga.cancel_evidence.length > 0 && (
            <div>
              <p className="font-semibold">Why it is cancelled</p>
              <ul className="font-mono text-xs">{yoga.cancel_evidence.map((e) => <li key={e}>{e}</li>)}</ul>
            </div>
          )}
          <div>
            <p className="font-semibold">Sources</p>
            <ul className="list-disc pl-5">{yoga.sources.map((c, i) => <Citation key={i} c={c} />)}</ul>
          </div>
        </div>
      </details>
    </li>
  );
}

export function YogasPanel({ request }: { request: BirthRequest }) {
  const [filter, setFilter] = useState("");
  const { data, error, loading } = useLoad(JSON.stringify(request), () =>
    api.POST("/v1/charts/yogas", { body: request }),
  );
  const match = (y: Schemas["YogaOut"]) => `${y.name} ${y.category}`.toLowerCase().includes(filter.toLowerCase());
  return (
    <div className="grid gap-3">
      <Status loading={loading} error={error} />
      {data && (
        <>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            {data.present.length} present and {data.cancelled.length} cancelled of {data.catalogue_size} rules. All rules
            are drafts until a qualified Jyotishi reviews them.
          </p>
          <label className="grid max-w-xs gap-1 text-sm" htmlFor="yoga-filter">
            Filter
            <input id="yoga-filter" type="search" value={filter} onChange={(e) => setFilter(e.target.value)} className="rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900" />
          </label>
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800" aria-label="Yogas present">
            {data.present.filter(match).map((y) => <Yoga key={y.id} yoga={y} />)}
          </ul>
          {data.cancelled.length > 0 && (
            <>
              <h3 className="font-semibold">Cancelled</h3>
              <ul className="divide-y divide-zinc-100 dark:divide-zinc-800" aria-label="Yogas cancelled">
                {data.cancelled.filter(match).map((y) => <Yoga key={y.id} yoga={y} cancelled />)}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}

export function StrengthsPanel({ request, ascendantSign }: { request: BirthRequest; ascendantSign: number }) {
  const { data, error, loading } = useLoad(JSON.stringify(request), () =>
    api.POST("/v1/charts/strengths", { body: request }),
  );
  return (
    <div className="grid gap-6">
      <Status loading={loading} error={error} />
      {data && (
        <>
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Shadbala table">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <caption className="mb-1 text-left font-semibold">Shadbala (rupas)</caption>
              <thead className="text-xs uppercase text-zinc-500">
                <tr><th className="py-1">Graha</th><th>Strength</th><th>Required</th><th className="w-1/3">Ratio</th><th>Ishta / Kashta</th></tr>
              </thead>
              <tbody>
                {data.shadbala.map((s) => (
                  <tr key={s.body} className="border-t border-zinc-100 dark:border-zinc-800">
                    <th scope="row" className="py-1 font-medium">{title(s.body)}</th>
                    <td className="tabular-nums">{s.rupas.toFixed(2)}</td>
                    <td className="tabular-nums">{s.required_rupas.toFixed(1)}</td>
                    <td>
                      <div className="h-2 rounded bg-zinc-100 dark:bg-zinc-800" role="img" aria-label={`ratio ${s.ratio.toFixed(2)}`}>
                        <div className={`h-2 rounded ${s.ratio >= 1 ? "bg-emerald-600" : "bg-amber-600"}`} style={{ width: `${Math.min(100, (s.ratio / 2) * 100)}%` }} />
                      </div>
                    </td>
                    <td className="tabular-nums">{s.ishta_phala.toFixed(1)} / {s.kashta_phala.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Ashtakavarga table">
            <table className="w-full min-w-[36rem] text-center text-sm tabular-nums">
              <caption className="mb-1 text-left font-semibold">Ashtakavarga</caption>
              <thead className="text-xs text-zinc-500">
                <tr><th className="text-left">Sign</th>{SIGNS.map((s, i) => <th key={s} scope="col">{s}<br /><span className="font-normal">H{((i - ascendantSign + 12) % 12) + 1}</span></th>)}</tr>
              </thead>
              <tbody>
                {Object.entries(data.ashtakavarga.bav).map(([body, row]) => (
                  <tr key={body} className="border-t border-zinc-100 dark:border-zinc-800">
                    <th scope="row" className="text-left font-medium">{title(body)}</th>
                    {row.map((n, i) => <td key={i}>{n}</td>)}
                  </tr>
                ))}
                <tr className="border-t-2 border-zinc-300 font-semibold dark:border-zinc-600">
                  <th scope="row" className="text-left">SAV</th>
                  {data.ashtakavarga.sav.map((n, i) => <td key={i} className={n >= 28 ? "text-emerald-700 dark:text-emerald-400" : n < 25 ? "text-amber-700 dark:text-amber-400" : ""}>{n}</td>)}
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export function TransitsPanel({ request }: { request: BirthRequest }) {
  const year = new Date().getFullYear();
  const [span, setSpan] = useState({ start: `${year - 5}-01-01`, end: `${year + 15}-01-01` });
  const body = { ...request, ...span };
  const { data, error, loading } = useLoad(JSON.stringify(body), () => api.POST("/v1/charts/transits", { body }));
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap gap-3 text-sm">
        {(["start", "end"] as const).map((k) => (
          <label key={k} className="grid gap-1" htmlFor={`transit-${k}`}>
            {k === "start" ? "From" : "To"}
            <input id={`transit-${k}`} type="date" value={span[k]} onChange={(e) => setSpan({ ...span, [k]: e.target.value })} className="rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900" />
          </label>
        ))}
      </div>
      <Status loading={loading} error={error} />
      {data && (
        <div className="grid gap-4 sm:grid-cols-2">
          <section aria-label="Saturn transits from the Moon">
            <h3 className="mb-1 font-semibold">Saturn from the natal Moon</h3>
            <ul className="text-sm">
              {Object.entries(data.saturn).flatMap(([kind, episodes]) =>
                episodes.map((e) => (
                  <li key={`${kind}-${e.start_jd_ut}`}>
                    <span className="font-medium">{title(kind)}</span>: {jdToDate(e.start_jd_ut)}
                    {e.open_start ? " (already running)" : ""} to {jdToDate(e.end_jd_ut)}
                    {e.open_end ? " (still running)" : ""}
                  </li>
                )),
              )}
            </ul>
          </section>
          <section aria-label="Double transits from the Moon">
            <h3 className="mb-1 font-semibold">Jupiter and Saturn double transit (from the Moon)</h3>
            <ul className="text-sm">
              {data.double_from_moon.slice(0, 24).map((d) => (
                <li key={`${d.house}-${d.start_jd_ut}`}>House {d.house}: {jdToDate(d.start_jd_ut)} to {jdToDate(d.end_jd_ut)}</li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

export function KpPanel({ request }: { request: BirthRequest }) {
  const body = { birth: request.birth, preset: "kp" as const };
  const { data, error, loading } = useLoad(JSON.stringify(body), () => api.POST("/v1/charts/kp", { body }));
  return (
    <div className="grid gap-4">
      <p className="text-sm text-zinc-600 dark:text-zinc-400">KP uses the Krishnamurti ayanamsa and Placidus cusps.</p>
      <Status loading={loading} error={error} />
      {data && (
        <>
          <p className="text-sm">
            <span className="font-semibold">Ruling planets:</span> {data.ruling_planets.map(title).join(", ")}
          </p>
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="KP cusps table">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <caption className="mb-1 text-left font-semibold">Cusps</caption>
              <thead className="text-xs uppercase text-zinc-500"><tr><th>House</th><th>Cusp</th><th>Sign</th><th>Star</th><th>Sub</th><th>Sub-sub</th></tr></thead>
              <tbody>
                {data.cusps.map((c) => (
                  <tr key={c.house} className="border-t border-zinc-100 dark:border-zinc-800">
                    <th scope="row" className="font-medium">{c.house}</th>
                    <td className="font-mono tabular-nums">{formatLongitude(c.longitude)}</td>
                    <td>{title(c.lords.sign_lord)}</td><td>{title(c.lords.star_lord)}</td><td>{title(c.lords.sub_lord)}</td><td>{title(c.lords.sub_sub_lord)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="KP significators table">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <caption className="mb-1 text-left font-semibold">Planets as significators (levels 1 to 4)</caption>
              <thead className="text-xs uppercase text-zinc-500"><tr><th>Planet</th><th>Bhava</th><th>Star / sub</th><th>Houses signified</th></tr></thead>
              <tbody>
                {data.planets.map((p) => (
                  <tr key={p.body} className="border-t border-zinc-100 dark:border-zinc-800">
                    <th scope="row" className="font-medium">{title(p.body)}</th>
                    <td>{p.house}</td>
                    <td>{title(p.lords.star_lord)} / {title(p.lords.sub_lord)}</td>
                    <td>{p.signifies.map((level) => level.join(" ") || "–").join(" | ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

interface Factor {
  name: string;
  value: string;
  minutes_before: number | null;
  minutes_after: number | null;
  fragile: boolean;
}

export function SensitivityPanel({ request }: { request: BirthRequest }) {
  const { data, error, loading } = useLoad<{ uncertainty_minutes: number; factors: Factor[] }>(
    JSON.stringify(request),
    () => api.POST("/v1/charts/sensitivity", { body: request }),
  );
  const minutes = (m: number | null) => (m === null ? "hours" : `${m.toFixed(1)} min`);
  return (
    <section aria-labelledby="sensitivity-heading" className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
      <h3 id="sensitivity-heading" className="mb-2 font-semibold">Birth-time sensitivity</h3>
      <Status loading={loading} error={error} />
      {data && (
        <ul className="grid gap-1 text-sm">
          {data.factors.map((f) => (
            <li key={f.name} className={f.fragile ? "text-amber-800 dark:text-amber-300" : ""}>
              <span className="font-medium">{f.name}</span> ({f.value}): held {minutes(f.minutes_before)} before, holds{" "}
              {minutes(f.minutes_after)} after
              {f.fragile ? `: changes within the ±${data.uncertainty_minutes} min uncertainty` : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
