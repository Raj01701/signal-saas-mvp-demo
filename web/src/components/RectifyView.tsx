"use client";

import { type FormEvent, useId, useState } from "react";

import { BirthFields, birthValue, PresetField, toBirthInput } from "@/components/BirthFields";
import { Status, title } from "@/components/common";
import { input } from "@/components/PlaceField";
import { SIGNS } from "@/lib/angles";
import { api, type Preset, type Schemas } from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";

type EventKind = Schemas["EventKind"];
type RectifyRequest = Schemas["RectifyRequest"];
type Prior = NonNullable<RectifyRequest["priors"]>[number];

const KINDS: { value: EventKind; label: string }[] = [
  { value: "marriage", label: "Marriage" },
  { value: "child_birth", label: "Birth of a child" },
  { value: "education", label: "Education (start or degree)" },
  { value: "job", label: "New job" },
  { value: "promotion", label: "Promotion" },
  { value: "job_loss", label: "Loss of job" },
  { value: "business", label: "Business started" },
  { value: "relocation", label: "Change of residence" },
  { value: "foreign_travel", label: "Travel or move abroad" },
  { value: "property", label: "Property bought" },
  { value: "divorce", label: "Divorce or separation" },
  { value: "illness", label: "Illness" },
  { value: "surgery", label: "Surgery" },
  { value: "accident", label: "Accident" },
  { value: "parent_death", label: "Death of a parent" },
  { value: "spouse_death", label: "Death of the spouse" },
];
const PRIORS: { value: Prior; label: string }[] = [
  { value: "kunda", label: "Kunda (lagna × 81 in the Moon's nakshatra group)" },
  { value: "pranapada", label: "Pranapada in a trine from the lagna" },
  { value: "navamsa_gender", label: "Navamsa lagna matches gender" },
];
const WINDOWS = [15, 30, 60, 120];

interface EventRow {
  id: number;
  kind: EventKind;
  date: string;
}

/** Birth-time rectification: dated life events in, ranked candidate birth times out. */
export function RectifyView() {
  const id = useId();
  const [birth, setBirth] = useState(() => birthValue("1990-05-17", "12:00:00"));
  const [preset, setPreset] = useState<Preset>("classic_parashari");
  const [window, setWindow] = useState(60);
  const [gender, setGender] = useState<"" | "male" | "female">("");
  const [priors, setPriors] = useState<Prior[]>([]);
  const [events, setEvents] = useState<EventRow[]>([
    { id: 1, kind: "job", date: "2013-07-01" },
    { id: 2, kind: "marriage", date: "2016-02-10" },
  ]);
  const [request, setRequest] = useState<RectifyRequest | null>(null);

  const update = (row: number, change: Partial<EventRow>) =>
    setEvents(events.map((e) => (e.id === row ? { ...e, ...change } : e)));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setRequest({
      birth: toBirthInput(birth),
      preset,
      uncertainty_minutes: window,
      step_seconds: window > 60 ? 60 : 30,
      gender: gender || null,
      priors,
      events: events.map(({ kind, date }) => ({ kind, date })),
    });
  };

  return (
    <div className="grid gap-8">
      <form onSubmit={submit} className="grid gap-6 print:hidden" aria-label="Rectification data">
        <fieldset className="grid gap-4 rounded-lg border border-zinc-200 p-4 sm:grid-cols-2 dark:border-zinc-800">
          <legend className="px-1 text-lg font-semibold">Recorded birth</legend>
          <BirthFields value={birth} onChange={setBirth} />
          <div className="grid gap-1 text-sm font-medium">
            <label htmlFor={`${id}-window`}>Search either side of the recorded time</label>
            <select id={`${id}-window`} value={window} onChange={(e) => setWindow(Number(e.target.value))} className={input}>
              {WINDOWS.map((w) => <option key={w} value={w}>{w} minutes</option>)}
            </select>
          </div>
          <div className="grid gap-1 text-sm font-medium">
            <label htmlFor={`${id}-gender`}>Gender (optional)</label>
            <select id={`${id}-gender`} value={gender} onChange={(e) => setGender(e.target.value as typeof gender)} className={input}>
              <option value="">Not given</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </div>
          <PresetField value={preset} onChange={setPreset} />
        </fieldset>

        <fieldset className="grid gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <legend className="px-1 text-lg font-semibold">Life events</legend>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Four to ten events you are sure of give the best result; dates to the day.
          </p>
          <ul className="grid gap-2" aria-label="Events">
            {events.map((e, index) => (
              <li key={e.id} className="grid grid-cols-[1fr_auto] items-end gap-2 sm:grid-cols-[1fr_12rem_auto]">
                <div className="grid gap-1 text-sm">
                  <label htmlFor={`${id}-kind-${e.id}`}>Event {index + 1}</label>
                  <select id={`${id}-kind-${e.id}`} value={e.kind} onChange={(v) => update(e.id, { kind: v.target.value as EventKind })} className={input}>
                    {KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
                  </select>
                </div>
                <label className="col-start-1 grid gap-1 text-sm sm:col-start-auto" htmlFor={`${id}-date-${e.id}`}>
                  Date of event {index + 1}
                  <input id={`${id}-date-${e.id}`} type="date" required value={e.date} onChange={(v) => update(e.id, { date: v.target.value })} className={input} />
                </label>
                <button
                  type="button"
                  onClick={() => setEvents(events.filter((x) => x.id !== e.id))}
                  disabled={events.length <= 2}
                  className="row-start-1 rounded-md border border-zinc-300 px-2 py-2 text-sm disabled:opacity-50 sm:row-start-auto dark:border-zinc-700"
                >
                  Remove<span className="sr-only"> event {index + 1}</span>
                </button>
              </li>
            ))}
          </ul>
          <div>
            <button
              type="button"
              onClick={() => setEvents([...events, { id: Math.max(0, ...events.map((e) => e.id)) + 1, kind: "relocation", date: "2020-01-01" }])}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700"
            >
              Add event
            </button>
          </div>
        </fieldset>

        <fieldset className="grid gap-2 rounded-lg border border-zinc-200 p-4 text-sm dark:border-zinc-800">
          <legend className="px-1 text-lg font-semibold">Traditional checks (optional)</legend>
          {PRIORS.map((p) => (
            <label key={p.value} className="flex items-center gap-2" htmlFor={`${id}-${p.value}`}>
              <input
                id={`${id}-${p.value}`}
                type="checkbox"
                checked={priors.includes(p.value)}
                onChange={(e) => setPriors(e.target.checked ? [...priors, p.value] : priors.filter((x) => x !== p.value))}
              />
              {p.label}
            </label>
          ))}
        </fieldset>

        <div>
          <button type="submit" className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800">
            Rectify birth time
          </button>
        </div>
      </form>
      {request && <RectifyResult request={request} />}
    </div>
  );
}

function ScanPlot({ scan, marks }: { scan: Schemas["ScanPointOut"][]; marks: number[] }) {
  const width = 600;
  const height = 120;
  const xs = scan.map((p) => p.offset_minutes);
  const ys = scan.map((p) => p.log_likelihood);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const x = (v: number) => ((v - x0) / (x1 - x0 || 1)) * width;
  const y = (v: number) => height - ((v - y0) / (y1 - y0 || 1)) * (height - 8) - 4;
  const points = scan.map((p) => `${x(p.offset_minutes).toFixed(1)},${y(p.log_likelihood).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-32 w-full" role="img" aria-label={`Score of each candidate time from ${x0} to ${x1} minutes; candidates at ${marks.join(", ")} minutes`}>
      <line x1={x(0)} x2={x(0)} y1={0} y2={height} className="stroke-zinc-300" strokeDasharray="4 4" />
      <polyline points={points} fill="none" className="stroke-amber-700" strokeWidth={2} />
      {marks.map((m) => <circle key={m} cx={x(m)} cy={y(scan.reduce((best, p) => (Math.abs(p.offset_minutes - m) < Math.abs(best.offset_minutes - m) ? p : best)).log_likelihood)} r={4} className="fill-amber-700" />)}
    </svg>
  );
}

function RectifyResult({ request }: { request: RectifyRequest }) {
  const { data, error, loading } = useLoad(JSON.stringify(request), () => api.POST("/v1/rectify", { body: request }));
  if (!data) return <Status loading={loading} error={error} />;
  const cell = "py-1.5 pr-3 align-top";
  return (
    <div className="grid gap-6">
      <section aria-labelledby="scan-heading" className="grid gap-2">
        <h2 id="scan-heading" className="text-lg font-semibold">Scan of the window</h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Log-likelihood of each candidate time (minutes from the recorded time; the dashed line is the recorded time).
        </p>
        <ScanPlot scan={data.scan} marks={data.candidates.map((c) => c.offset_minutes)} />
      </section>

      <section aria-labelledby="candidates-heading" className="grid gap-2">
        <h2 id="candidates-heading" className="text-lg font-semibold">Candidate birth times</h2>
        <div role="region" tabIndex={0} aria-label="Candidate birth times" className="relative overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-zinc-500">
              <tr>
                {["Time", "Offset", "Share", "Lagna", "Navamsa lagna", "Moon", ...(request.priors?.length ? ["Checks"] : [])].map((h) => (
                  <th key={h} scope="col" className={`${cell} font-normal`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.candidates.map((c) => (
                <tr key={c.offset_minutes}>
                  <th scope="row" className={`${cell} font-medium whitespace-nowrap`}>{c.local_time.slice(11, 19)}</th>
                  <td className={cell}>{c.offset_minutes > 0 ? "+" : ""}{c.offset_minutes.toFixed(1)} min</td>
                  <td className={cell}>{(c.share * 100).toFixed(0)}%</td>
                  <td className={`${cell} whitespace-nowrap`}>{SIGNS[c.lagna]} {c.lagna_degrees.toFixed(1)}°</td>
                  <td className={cell}>{SIGNS[c.navamsa_lagna]}</td>
                  <td className={cell}>{c.moon_nakshatra} {c.moon_pada}</td>
                  {request.priors?.length ? (
                    <td className={cell}>{Object.entries(c.priors).map(([k, ok]) => `${title(k)} ${ok ? "yes" : "no"}`).join(", ")}</td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul className="grid gap-2 text-sm" aria-label="Event evidence by candidate">
          {data.candidates.map((c) => (
            <li key={c.offset_minutes}>
              <details>
                <summary className="cursor-pointer">Events at {c.local_time.slice(11, 19)}</summary>
                <ul className="mt-1 grid gap-1 pl-4">
                  {c.events.map((e) => (
                    <li key={`${e.kind}-${e.date}`}>
                      <span className="font-medium">{title(e.kind)} {e.date}</span>: {e.dasha.map(title).join(" / ")} (fit {e.score.toFixed(2)})
                      {e.reasons.length > 0 && <span className="text-zinc-600 dark:text-zinc-400"> — {e.reasons.join("; ")}</span>}
                    </li>
                  ))}
                </ul>
              </details>
            </li>
          ))}
        </ul>
      </section>

      {data.differences.length > 0 && (
        <section aria-labelledby="differences-heading" className="grid gap-1 text-sm">
          <h2 id="differences-heading" className="text-lg font-semibold">What changes between candidates</h2>
          <ul className="list-disc pl-5">{data.differences.map((d) => <li key={d}>{d}</li>)}</ul>
        </section>
      )}
      <p className="text-xs text-zinc-500">{data.notes.join(" ")}</p>
    </div>
  );
}
