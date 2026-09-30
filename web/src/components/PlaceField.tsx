"use client";

import { useEffect, useId, useState } from "react";

import { api, type Schemas } from "@/lib/api/client";

/** A place and, when it came from the gazetteer, its IANA time zone. */
export interface PlaceValue {
  place: Schemas["PlaceInput"];
  zone: string | null;
}

export const NEW_DELHI: PlaceValue = { place: { name: "New Delhi", latitude: 28.6139, longitude: 77.209 }, zone: null };

export const input =
  "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900";

/**
 * Place search with a manual latitude and longitude fallback. Renders three
 * cells of a two-column grid: the search box across both columns, then the
 * coordinates.
 */
export function PlaceField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: PlaceValue;
  onChange: (value: PlaceValue) => void;
}) {
  const id = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Schemas["Place"][]>([]);
  const { place } = value;

  useEffect(() => {
    if (query.trim().length < 2) return;
    const timer = setTimeout(async () => {
      const { data } = await api.GET("/v1/geo/search", { params: { query: { q: query, limit: 8 } } });
      setResults(data ?? []);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const coordinate = (key: "latitude" | "longitude", text: string) =>
    onChange({ place: { ...place, name: "Custom place", [key]: Number(text) }, zone: null });

  return (
    <>
      <div className="grid gap-1 text-sm font-medium sm:col-span-2">
        <label htmlFor={`${id}-place`}>{label}</label>
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
                    onChange({ place: { name: r.name, latitude: r.latitude, longitude: r.longitude }, zone: r.timezone });
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
          onChange={(e) => coordinate("latitude", e.target.value)}
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
          onChange={(e) => coordinate("longitude", e.target.value)}
          className={input}
        />
      </label>
    </>
  );
}
