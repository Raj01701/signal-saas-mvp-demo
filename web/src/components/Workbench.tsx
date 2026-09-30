"use client";

import { useState } from "react";

import { BirthForm, type BirthRequest } from "@/components/BirthForm";
import { ChartDiagram } from "@/components/ChartDiagram";
import { DashaTable } from "@/components/DashaTable";
import { KpPanel, SensitivityPanel, StrengthsPanel, TransitsPanel, YogasPanel } from "@/components/Panels";
import { PlanetTable } from "@/components/PlanetTable";
import { ReadingsPanel, TimelinePanel } from "@/components/Predictions";
import { ReportPanel } from "@/components/ReportPanel";
import { api, type Chart, errorMessage } from "@/lib/api/client";
import type { ChartStyle, Placement } from "@/lib/chart-layout";

const STYLES: { value: ChartStyle; label: string }[] = [
  { value: "north", label: "North Indian" },
  { value: "south", label: "South Indian" },
  { value: "east", label: "East Indian" },
];
const TABS = ["Chart", "Dashas", "Yogas", "Readings", "Timeline", "Report", "Strengths", "Transits", "KP"] as const;
type Tab = (typeof TABS)[number];

const select = "rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900";

function vargaPlacements(chart: Chart, division: number): { ascendant: number; placements: Placement[]; name: string } {
  const varga = chart.vargas.find((v) => v.division === division);
  if (division === 1 || !varga) {
    return {
      name: "Rasi (D1)",
      ascendant: chart.ascendant.sign,
      placements: chart.grahas.map((g) => ({ body: g.body, sign: g.sign, retrograde: g.retrograde })),
    };
  }
  return {
    name: `${varga.name} (D${division})`,
    ascendant: varga.ascendant.sign,
    placements: Object.entries(varga.grahas).map(([body, p]) => ({ body, sign: p.sign })),
  };
}

/** The astrologer workbench: birth data in; charts, dashas, yogas, readings, timeline, strengths, transits and KP out. */
export function Workbench() {
  const [chart, setChart] = useState<Chart | null>(null);
  const [request, setRequest] = useState<BirthRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [style, setStyle] = useState<ChartStyle>("north");
  const [division, setDivision] = useState(9);
  const [tab, setTab] = useState<Tab>("Chart");

  const calculate = async (next: BirthRequest) => {
    setBusy(true);
    setError(null);
    const { data, error: failure } = await api.POST("/v1/charts", { body: next });
    setBusy(false);
    if (data) {
      setChart(data);
      setRequest(next);
    } else setError(errorMessage(failure));
  };

  return (
    <div className="grid gap-8">
      <section aria-labelledby="birth-heading" className="rounded-lg border border-zinc-200 p-4 print:hidden dark:border-zinc-800">
        <h2 id="birth-heading" className="mb-3 text-lg font-semibold">Birth data</h2>
        <BirthForm onSubmit={calculate} busy={busy} />
        <p role="status" aria-live="polite" className="mt-3 text-sm text-red-700 dark:text-red-400">{error}</p>
      </section>

      {chart && request && (
        <>
          {chart.time.warnings.length > 0 && (
            <aside className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-700 dark:bg-amber-950" aria-label="Birth time warnings">
              <p className="font-semibold">Check the birth time</p>
              <ul className="list-disc pl-5">{chart.time.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </aside>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2 print:hidden">
            <div role="tablist" aria-label="Workbench views" className="flex flex-wrap gap-1">
              {TABS.map((t) => (
                <button
                  key={t}
                  role="tab"
                  type="button"
                  id={`tab-${t}`}
                  aria-selected={tab === t}
                  aria-controls={tab === t ? `panel-${t}` : undefined}
                  tabIndex={tab === t ? 0 : -1}
                  onKeyDown={(e) => {
                    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
                    if (!step) return;
                    const next = TABS[(TABS.indexOf(t) + step + TABS.length) % TABS.length];
                    setTab(next);
                    document.getElementById(`tab-${next}`)?.focus();
                  }}
                  onClick={() => setTab(t)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${tab === t ? "bg-amber-700 text-white" : "bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700"}`}
                >
                  {t}
                </button>
              ))}
            </div>
            <button type="button" onClick={() => window.print()} className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700">
              Print or save as PDF
            </button>
          </div>

          <section role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="grid gap-6">
            {tab === "Chart" && (
              <>
                <div className="flex flex-wrap items-end gap-3 text-sm print:hidden">
                  <div className="grid gap-1">
                    <label htmlFor="chart-style">Chart style</label>
                    <select id="chart-style" value={style} onChange={(e) => setStyle(e.target.value as ChartStyle)} className={select}>
                      {STYLES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </div>
                  <div className="grid gap-1">
                    <label htmlFor="chart-division">Divisional chart</label>
                    <select id="chart-division" value={division} onChange={(e) => setDivision(Number(e.target.value))} className={select}>
                      {chart.vargas.map((v) => <option key={v.division} value={v.division}>D{v.division} {v.name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid justify-items-center gap-6 sm:grid-cols-2">
                  {[1, division].map((d) => {
                    const { ascendant, placements, name } = vargaPlacements(chart, d);
                    return <ChartDiagram key={d} style={style} ascendantSign={ascendant} placements={placements} title={name} />;
                  })}
                </div>
                <SensitivityPanel request={request} />
                <PlanetTable chart={chart} />
                <p className="text-xs text-zinc-500">
                  {chart.ayanamsa.label} ayanamsa {chart.ayanamsa.true.toFixed(4)}°; engine {chart.engine_version}; settings {chart.settings_hash.slice(0, 12)}.
                </p>
              </>
            )}
            {tab === "Dashas" && <DashaTable table={chart.dashas.vimshottari} now={new Date().toISOString()} />}
            {tab === "Yogas" && <YogasPanel request={request} />}
            {tab === "Readings" && <ReadingsPanel request={request} />}
            {tab === "Timeline" && <TimelinePanel request={request} />}
            {tab === "Report" && <ReportPanel request={request} />}
            {tab === "Strengths" && <StrengthsPanel request={request} ascendantSign={chart.ascendant.sign} />}
            {tab === "Transits" && <TransitsPanel request={request} />}
            {tab === "KP" && <KpPanel request={request} />}
          </section>
        </>
      )}
    </div>
  );
}
