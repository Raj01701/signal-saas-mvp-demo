"use client";

import { type FormEvent, useId, useState, useSyncExternalStore } from "react";

import { PresetField } from "@/components/BirthFields";
import { Status, title } from "@/components/common";
import { input, NEW_DELHI, PlaceField } from "@/components/PlaceField";
import { api, type Preset, type Schemas } from "@/lib/api/client";
import { clock, longDate, offsetLabel } from "@/lib/format";
import { type Lang, useI18n } from "@/lib/i18n";
import { nakshatraName, planetName, tithiName as tithiLabel, varaName } from "@/lib/names";
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

const HINDI: Record<string, string> = {
  Vara: "वार",
  Tithi: "तिथि",
  Nakshatra: "नक्षत्र",
  Yoga: "योग",
  Karana: "करण",
  Choghadiyas: "चौघड़िया",
  Horas: "होरा",
  "Month (amanta)": "मास (अमांत)",
  "Month (purnimanta)": "मास (पूर्णिमांत)",
  Paksha: "पक्ष",
  Samvatsara: "संवत्सर",
  Years: "वर्ष",
  Ritu: "ऋतु",
  Ayana: "अयन",
  "Tamil date": "तमिल तिथि",
  "Kshaya tithi": "क्षय तिथि",
  "Vriddhi tithi": "वृद्धि तिथि",
};
/** A fixed label in the interface language. */
const label = (english: string, lang: Lang) => (lang === "hi" ? (HINDI[english] ?? english) : english);

const subscribeNever = () => () => {};

/** Today's date in the browser's time zone, YYYY-MM-DD. */
function localToday(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

/** Today's panchanga for a place, or any date's: limbs with end times, the calendar and muhurtas. */
export function PanchangaView() {
  const id = useId();
  const { t } = useI18n();
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
        <h2 id="panchanga-form" className="mb-3 text-lg font-semibold">{t.panchanga.form}</h2>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label={t.panchanga.form}>
          <label className="grid gap-1 text-sm font-medium sm:col-span-2" htmlFor={`${id}-date`}>
            {t.panchanga.date}
            <input
              id={`${id}-date`}
              type="date"
              required
              value={date ?? today}
              onChange={(e) => setDate(e.target.value)}
              className={`${input} sm:w-1/2`}
            />
          </label>
          <PlaceField label={t.panchanga.place} value={location} onChange={setLocation} />
          <PresetField value={preset} onChange={setPreset} />
          <div className="sm:col-span-2">
            <button type="submit" className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800">
              {t.panchanga.show}
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
  const { t, lang } = useI18n();
  if (!data) return <Status loading={loading} error={error} />;
  const p = t.panchanga;
  const hindi = lang === "hi";
  const at = (iso: string) => clock(iso, data.utc_offset_seconds, data.civil_date);
  const span = (period: Period) =>
    hindi ? `${at(period.start)} से ${at(period.end)} तक` : `${at(period.start)} to ${at(period.end)}`;
  const until = (iso: string) => (hindi ? `${at(iso)} ${p.until}` : `${p.until} ${at(iso)}`);
  const limbName = (key: string, s: Schemas["LimbSpanOut"]) =>
    key === "tithis" ? tithiLabel(s.number, s.name, lang) : key === "nakshatras" ? nakshatraName(s.number, s.name, lang) : s.name;
  const paksha = (value: string) =>
    hindi ? ` (${value === "krishna" ? "कृष्ण" : "शुक्ल"} पक्ष)` : ` (${value} paksha)`;
  return (
    <div className="grid gap-8">
      <section aria-labelledby="day-heading" className="grid gap-3">
        <h2 id="day-heading" className="text-xl font-semibold">
          {varaName(data.vara, lang)}, {longDate(data.civil_date, hindi ? "hi-IN" : "en-GB")}
        </h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {data.place.name} ({data.place.latitude.toFixed(4)}, {data.place.longitude.toFixed(4)}).{" "}
          {p.times(offsetLabel(data.utc_offset_seconds), data.zone ? ` (${data.zone})` : "")}
        </p>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-5">
          {[
            [p.sunrise, data.sunrise],
            [p.sunset, data.sunset],
            [p.moonrise, data.moonrise],
            [p.moonset, data.moonset],
            [p.nextSunrise, data.next_sunrise],
          ].map(([name, iso]) => (
            <div key={name}>
              <dt className="text-zinc-500">{name}</dt>
              <dd className="font-medium">{iso ? at(iso) : p.none}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="limbs-heading">
        <h2 id="limbs-heading" className="mb-2 text-lg font-semibold">{p.limbs}</h2>
        <dl className="grid gap-2 text-sm">
          <div className="grid gap-1 sm:grid-cols-[8rem_1fr]">
            <dt className="font-semibold">{label("Vara", lang)}</dt>
            <dd>
              {varaName(data.vara, lang)} ({hindi ? "स्वामी" : "lord"} {planetName(data.vara_lord, lang)})
            </dd>
          </div>
          {LIMBS.map(([name, key]) => (
            <div key={key} className="grid gap-1 sm:grid-cols-[8rem_1fr]">
              <dt className="font-semibold">{label(name, lang)}</dt>
              <dd>
                <ul>
                  {data[key].map((s) => (
                    <li key={`${s.number}-${s.start}`}>
                      {limbName(key, s)}
                      {s.paksha ? paksha(s.paksha) : ""} <span className="text-zinc-500">{until(s.end)}</span>
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <CalendarSection data={data} lang={lang} heading={p.calendar} />

      <section aria-labelledby="muhurta-heading" className="grid gap-3 text-sm">
        <h2 id="muhurta-heading" className="text-lg font-semibold">{p.muhurtas}</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <h3 className="font-semibold">{p.favourable}</h3>
            <ul>
              {[data.brahma_muhurta, data.abhijit].map((p) => (
                <li key={p.name}>
                  {p.name}: {span(p)}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-semibold">{p.avoided}</h3>
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
          <PeriodTable caption={label("Choghadiyas", lang)} periods={data.choghadiyas} span={span} quality />
          <PeriodTable caption={label("Horas", lang)} periods={data.horas} span={span} />
        </div>
      </section>
    </div>
  );
}

function CalendarSection({ data, lang, heading }: { data: Panchanga; lang: Lang; heading: string }) {
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
      <h2 id="calendar-heading" className="mb-2 text-lg font-semibold">{heading}</h2>
      <dl className="grid gap-2 text-sm">
        {rows.map(([name, value]) => (
          <div key={name} className="grid gap-1 sm:grid-cols-[10rem_1fr]">
            <dt className="font-semibold">{label(name, lang)}</dt>
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
