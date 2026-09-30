"use client";

import { type FormEvent, useId, useState, useSyncExternalStore } from "react";

import { PresetField } from "@/components/BirthFields";
import { Status, title } from "@/components/common";
import { input, NEW_DELHI, PlaceField } from "@/components/PlaceField";
import { api, type Preset, type Schemas } from "@/lib/api/client";
import { clock, longDate, offsetLabel } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

type Panchanga = Schemas["PanchangaOut"];
type PanchangaRequest = Schemas["PanchangaRequest"];
type Period = Schemas["PeriodOut"];

const LIMBS = [
  ["Tithi", "tithis"],
  ["Nakshatra", "nakshatras"],
  ["Yoga", "yogas"],
  ["Karana", "karanas"],
] as const;

const subscribeNever = () => () => {};

/** Today's date in the browser's time zone, YYYY-MM-DD. */
function localToday(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

/** Today's panchanga for a place, or any date's: limbs with end times, the calendar and muhurtas. */
export function PanchangaView() {
  const id = useId();
  const today = useSyncExternalStore(subscribeNever, localToday, () => "");
  const [date, setDate] = useState<string | null>(null);
  const [location, setLocation] = useState(NEW_DELHI);
  const [preset, setPreset] = useState<Preset>("drik_compatible");
  const [request, setRequest] = useState<PanchangaRequest | null>(null);
  const shown = request ?? (today ? { date: today, place: NEW_DELHI.place, zone: null, preset: "drik_compatible" as const } : null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setRequest({ date: date ?? today, place: location.place, zone: location.zone, preset });
  };

  return (
    <div className="grid gap-8">
      <section aria-labelledby="panchanga-form" className="rounded-lg border border-zinc-200 p-4 print:hidden dark:border-zinc-800">
        <h2 id="panchanga-form" className="mb-3 text-lg font-semibold">Date and place</h2>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label="Date and place">
          <label className="grid gap-1 text-sm font-medium sm:col-span-2" htmlFor={`${id}-date`}>
            Date
            <input
              id={`${id}-date`}
              type="date"
              required
              value={date ?? today}
              onChange={(e) => setDate(e.target.value)}
              className={`${input} sm:w-1/2`}
            />
          </label>
          <PlaceField label="Place" value={location} onChange={setLocation} />
          <PresetField value={preset} onChange={setPreset} />
          <div className="sm:col-span-2">
            <button type="submit" className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800">
              Show panchanga
            </button>
          </div>
        </form>
      </section>
      {shown && <PanchangaResult request={shown} />}
    </div>
  );
}

function PanchangaResult({ request }: { request: PanchangaRequest }) {
  const { data, error, loading } = useLoad(JSON.stringify(request), () => api.POST("/v1/panchanga", { body: request }));
  if (!data) return <Status loading={loading} error={error} />;
  const at = (iso: string) => clock(iso, data.utc_offset_seconds, data.civil_date);
  const span = (p: Period) => `${at(p.start)} to ${at(p.end)}`;
  return (
    <div className="grid gap-8">
      <section aria-labelledby="day-heading" className="grid gap-3">
        <h2 id="day-heading" className="text-xl font-semibold">
          {data.vara}, {longDate(data.civil_date)}
        </h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {data.place.name} ({data.place.latitude.toFixed(4)}, {data.place.longitude.toFixed(4)}). Times are local,{" "}
          {offsetLabel(data.utc_offset_seconds)}
          {data.zone ? ` (${data.zone})` : ""}; the Hindu day runs from sunrise to the next sunrise.
        </p>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-5">
          {[
            ["Sunrise", data.sunrise],
            ["Sunset", data.sunset],
            ["Moonrise", data.moonrise],
            ["Moonset", data.moonset],
            ["Next sunrise", data.next_sunrise],
          ].map(([name, iso]) => (
            <div key={name}>
              <dt className="text-zinc-500">{name}</dt>
              <dd className="font-medium">{iso ? at(iso) : "none this day"}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="limbs-heading">
        <h2 id="limbs-heading" className="mb-2 text-lg font-semibold">The five limbs</h2>
        <dl className="grid gap-2 text-sm">
          <div className="grid gap-1 sm:grid-cols-[8rem_1fr]">
            <dt className="font-semibold">Vara</dt>
            <dd>
              {data.vara} (lord {title(data.vara_lord)})
            </dd>
          </div>
          {LIMBS.map(([name, key]) => (
            <div key={key} className="grid gap-1 sm:grid-cols-[8rem_1fr]">
              <dt className="font-semibold">{name}</dt>
              <dd>
                <ul>
                  {data[key].map((s) => (
                    <li key={`${s.number}-${s.start}`}>
                      {s.name}
                      {s.paksha ? ` (${s.paksha} paksha)` : ""} <span className="text-zinc-500">until {at(s.end)}</span>
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <CalendarSection data={data} />

      <section aria-labelledby="muhurta-heading" className="grid gap-3 text-sm">
        <h2 id="muhurta-heading" className="text-lg font-semibold">Muhurtas</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <h3 className="font-semibold">Favourable</h3>
            <ul>
              {[data.brahma_muhurta, data.abhijit].map((p) => (
                <li key={p.name}>
                  {p.name}: {span(p)}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-semibold">Avoided</h3>
            <ul>
              {[...data.kalams, ...data.durmuhurtas].map((p) => (
                <li key={`${p.name}-${p.start}`}>
                  {p.name}: {span(p)}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <PeriodTable caption="Choghadiyas" periods={data.choghadiyas} span={span} quality />
          <PeriodTable caption="Horas" periods={data.horas} span={span} />
        </div>
      </section>
    </div>
  );
}

function CalendarSection({ data }: { data: Panchanga }) {
  const c = data.calendar;
  const month = c.amanta.name + (c.amanta.adhika ? " (adhika)" : c.amanta.nija ? " (nija)" : "");
  const tithiName = (n: number) => data.tithis.find((t) => t.number === n)?.name ?? `tithi ${n}`;
  const rows: [string, string][] = [
    ["Month (amanta)", month + (c.amanta.kshaya_name ? `; ${c.amanta.kshaya_name} is kshaya this year` : "")],
    ["Month (purnimanta)", c.purnimanta_name + (c.purnimanta_adhika ? " (adhika)" : "")],
    ["Paksha", `${title(c.paksha)} paksha, day ${c.paksha_day}`],
    ["Samvatsara", `${c.samvatsara} (${c.samvatsara_number} of 60)`],
    ["Years", `Shaka ${c.shaka_year}; Vikram ${c.vikram_year} (Chaitradi), ${c.vikram_year_kartikadi} (Kartikadi); Kali ${c.kali_year}`],
    ["Ritu", c.ritu],
    ["Ayana", `${title(c.ayana_sidereal)} (sidereal), ${title(c.ayana_tropical)} (tropical)`],
    ["Tamil date", `${c.tamil_day} ${c.tamil_month}, ${c.tamil_samvatsara}`],
  ];
  if (c.kshaya_tithis.length > 0) rows.push(["Kshaya tithi", c.kshaya_tithis.map(tithiName).join(", ")]);
  if (c.vriddhi_tithi) rows.push(["Vriddhi tithi", "the sunrise tithi also holds at the next sunrise"]);
  return (
    <section aria-labelledby="calendar-heading">
      <h2 id="calendar-heading" className="mb-2 text-lg font-semibold">Calendar</h2>
      <dl className="grid gap-2 text-sm">
        {rows.map(([name, value]) => (
          <div key={name} className="grid gap-1 sm:grid-cols-[10rem_1fr]">
            <dt className="font-semibold">{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function PeriodTable({
  caption,
  periods,
  span,
  quality,
}: {
  caption: string;
  periods: Period[];
  span: (p: Period) => string;
  quality?: boolean;
}) {
  return (
    <div role="region" tabIndex={0} aria-label={caption} className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="mb-1 text-left font-semibold">{caption}</caption>
        <thead className="text-zinc-500">
          <tr>
            <th scope="col" className="py-1 pr-3 font-normal">Name</th>
            {quality && <th scope="col" className="py-1 pr-3 font-normal">Quality</th>}
            <th scope="col" className="py-1 font-normal">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {periods.map((p) => (
            <tr key={`${p.name}-${p.start}`}>
              <th scope="row" className="py-1 pr-3 font-normal">{p.name}</th>
              {quality && <td className="py-1 pr-3">{p.quality ?? ""}</td>}
              <td className="py-1 whitespace-nowrap">{span(p)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
