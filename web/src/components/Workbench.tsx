"use client";

import { useState } from "react";

import { BirthForm, type BirthRequest } from "@/components/BirthForm";
import { ChartDiagram } from "@/components/ChartDiagram";
import { DashaTable } from "@/components/DashaTable";
import { PlanetTable } from "@/components/PlanetTable";
import { api, type Chart, errorMessage } from "@/lib/api/client";
import type { ChartStyle, Placement } from "@/lib/chart-layout";

const STYLES: { value: ChartStyle; label: string }[] = [
  { value: "north", label: "North Indian" },
  { value: "south", label: "South Indian" },
  { value: "east", label: "East Indian" },
];

function vargaPlacements(chart: Chart, division: number): { ascendant: number; placements: Placement[]; name: string } {
  if (division === 1) {
    return {
      name: "Rasi (D1)",
      ascendant: chart.ascendant.sign,
      placements: chart.grahas.map((g) => ({ body: g.body, sign: g.sign, retrograde: g.retrograde })),
    };
  }
  const varga = chart.vargas.find((v) => v.division === division);
  if (!varga) return vargaPlacements(chart, 1);
  return {
    name: `${varga.name} (D${division})`,
    ascendant: varga.ascendant.sign,
    placements: Object.entries(varga.grahas).map(([body, p]) => ({ body, sign: p.sign })),
  };
}

/** The astrologer workbench: birth data in, chart, planets and dashas out. */
export function Workbench() {
  const [chart, setChart] = useState<Chart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [style, setStyle] = useState<ChartStyle>("north");
  const [division, setDivision] = useState(9);

  const calculate = async (request: BirthRequest) => {
    setBusy(true);
    setError(null);
    const { data, error: failure } = await api.POST("/v1/charts", { body: request });
    setBusy(false);
    if (data) setChart(data);
    else setError(errorMessage(failure));
  };

  return (
    <div className="grid gap-8">
      <section aria-labelledby="birth-heading" className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <h2 id="birth-heading" className="mb-3 text-lg font-semibold">Birth data</h2>
        <BirthForm onSubmit={calculate} busy={busy} />
        <p role="status" aria-live="polite" className="mt-3 text-sm text-red-700 dark:text-red-400">{error}</p>
      </section>

      {chart && (
        <>
          {chart.time.warnings.length > 0 && (
            <aside className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-700 dark:bg-amber-950" aria-label="Birth time warnings">
              <p className="font-semibold">Check the birth time</p>
              <ul className="list-disc pl-5">
                {chart.time.warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </aside>
          )}
          <section aria-labelledby="chart-heading" className="grid gap-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h2 id="chart-heading" className="text-lg font-semibold">Charts</h2>
              <div className="flex flex-wrap gap-3 text-sm">
                <div className="grid gap-1">
                  <label htmlFor="chart-style">Chart style</label>
                  <select id="chart-style" value={style} onChange={(e) => setStyle(e.target.value as ChartStyle)} className="rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900">
                    {STYLES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
                <div className="grid gap-1">
                  <label htmlFor="chart-division">Divisional chart</label>
                  <select id="chart-division" value={division} onChange={(e) => setDivision(Number(e.target.value))} className="rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900">
                    {chart.vargas.map((v) => <option key={v.division} value={v.division}>D{v.division} {v.name}</option>)}
                  </select>
                </div>
              </div>
            </div>
            <div className="grid justify-items-center gap-6 sm:grid-cols-2">
              {[1, division].map((d) => {
                const { ascendant, placements, name } = vargaPlacements(chart, d);
                return <ChartDiagram key={d} style={style} ascendantSign={ascendant} placements={placements} title={name} />;
              })}
            </div>
            <p className="text-xs text-zinc-500">
              {chart.ayanamsa.label} ayanamsa {chart.ayanamsa.true.toFixed(4)}°; engine {chart.engine_version}; settings {chart.settings_hash.slice(0, 12)}.
            </p>
          </section>
          <section aria-labelledby="planets-heading">
            <h2 id="planets-heading" className="mb-2 text-lg font-semibold">Planets</h2>
            <PlanetTable chart={chart} />
          </section>
          <section aria-labelledby="dasha-heading">
            <h2 id="dasha-heading" className="mb-2 text-lg font-semibold">Vimshottari dasha</h2>
            <DashaTable table={chart.dashas.vimshottari} now={new Date().toISOString()} />
          </section>
        </>
      )}
    </div>
  );
}
