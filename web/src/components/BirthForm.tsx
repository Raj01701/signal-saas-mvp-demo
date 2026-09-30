"use client";

import { type FormEvent, useEffect, useId, useState } from "react";

import { api, type Preset, type Schemas } from "@/lib/api/client";

type Place = Schemas["PlaceInput"];

export interface BirthRequest {
  birth: Schemas["BirthInput"];
  preset: Preset;
}

const PRESETS: { value: Preset; label: string }[] = [
  { value: "classic_parashari", label: "Classic Parashari (Lahiri, true nodes)" },
  { value: "drik_compatible", label: "Drik Panchang compatible" },
  { value: "kp", label: "KP (Krishnamurti, Placidus)" },
  { value: "pvr_jhora_style", label: "PVR / JHora style (True Pushya)" },
];

const input =
  "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900";

/** Birth date, time and place, with place search and a manual-coordinates fallback. */
export function BirthForm({ onSubmit, busy }: { onSubmit: (request: BirthRequest) => void; busy: boolean }) {
  const id = useId();
  const [date, setDate] = useState("1990-05-17");
  const [time, setTime] = useState("12:00:00");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Schemas["Place"][]>([]);
  const [place, setPlace] = useState<Place>({ name: "New Delhi", latitude: 28.6139, longitude: 77.209 });
  const [zone, setZone] = useState<string | null>(null);
  const [preset, setPreset] = useState<Preset>("classic_parashari");

  useEffect(() => {
    if (query.trim().length < 2) return;
    const timer = setTimeout(async () => {
      const { data } = await api.GET("/v1/geo/search", { params: { query: { q: query, limit: 8 } } });
      setResults(data ?? []);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const seconds = time.length === 5 ? `${time}:00` : time;
    onSubmit({ birth: { local_datetime: `${date}T${seconds}`, place, zone }, preset });
  };

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label="Birth data">
      <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-date`}>
        Date of birth
        <input id={`${id}-date`} type="date" required value={date} onChange={(e) => setDate(e.target.value)} className={input} />
      </label>
      <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-time`}>
        Time of birth (local)
        <input id={`${id}-time`} type="time" step="1" required value={time} onChange={(e) => setTime(e.target.value)} className={input} />
      </label>
      <div className="grid gap-1 text-sm font-medium sm:col-span-2">
        <label htmlFor={`${id}-place`}>Place of birth</label>
        <input
          id={`${id}-place`}
          type="search"
          placeholder={`${place.name} (type to search)`}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value.trim().length < 2) setResults([]);
          }}
          className={input}
          aria-controls={results.length > 0 ? `${id}-results` : undefined}
          autoComplete="off"
        />
        {results.length > 0 && (
          <ul id={`${id}-results`} className="rounded-md border border-zinc-200 dark:border-zinc-700" aria-label="Matching places">
            {results.map((r) => (
              <li key={r.geonames_id}>
                <button
                  type="button"
                  className="w-full px-3 py-1.5 text-left font-normal hover:bg-amber-50 focus:bg-amber-50 dark:hover:bg-zinc-800 dark:focus:bg-zinc-800"
                  onClick={() => {
                    setPlace({ name: r.name, latitude: r.latitude, longitude: r.longitude });
                    setZone(r.timezone);
                    setResults([]);
                    setQuery("");
                  }}
                >
                  {r.name}, {r.admin1_code}, {r.country_code}
                  <span className="ml-2 text-xs text-zinc-500">
                    {r.latitude.toFixed(3)}, {r.longitude.toFixed(3)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-lat`}>
        Latitude
        <input
          id={`${id}-lat`}
          type="number"
          step="0.0001"
          min={-90}
          max={90}
          required
          value={place.latitude}
          onChange={(e) => {
            setPlace({ ...place, name: "Custom place", latitude: Number(e.target.value) });
            setZone(null);
          }}
          className={input}
        />
      </label>
      <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-lon`}>
        Longitude
        <input
          id={`${id}-lon`}
          type="number"
          step="0.0001"
          min={-180}
          max={180}
          required
          value={place.longitude}
          onChange={(e) => {
            setPlace({ ...place, name: "Custom place", longitude: Number(e.target.value) });
            setZone(null);
          }}
          className={input}
        />
      </label>
      <label className="grid gap-1 text-sm font-medium sm:col-span-2" htmlFor={`${id}-preset`}>
        Calculation settings
        <select id={`${id}-preset`} value={preset} onChange={(e) => setPreset(e.target.value as Preset)} className={input}>
          {PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-60"
        >
          {busy ? "Calculating…" : "Calculate chart"}
        </button>
      </div>
    </form>
  );
}
