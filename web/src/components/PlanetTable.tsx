import type { Chart } from "@/lib/api/client";
import { formatLongitude } from "@/lib/angles";

const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replaceAll("_", " ");

/** Planets to the arcsecond with nakshatra, dignity, state and KP lords. */
export function PlanetTable({ chart }: { chart: Chart }) {
  const rows = [
    { key: "lagna", name: "Lagna", point: chart.ascendant, extra: null },
    ...chart.grahas.map((g) => ({ key: g.body, name: title(g.body), point: g, extra: g })),
  ];
  return (
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Planet positions">
      <table className="w-full min-w-[40rem] text-left text-sm">
        <caption className="sr-only">Planet positions</caption>
        <thead className="border-b border-zinc-300 text-xs uppercase text-zinc-500 dark:border-zinc-700">
          <tr>
            <th className="py-2 pr-3">Graha</th>
            <th className="py-2 pr-3">Longitude</th>
            <th className="py-2 pr-3">Nakshatra</th>
            <th className="py-2 pr-3">House</th>
            <th className="py-2 pr-3">Dignity</th>
            <th className="py-2 pr-3">State</th>
            <th className="py-2">KP star / sub</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ key, name, point, extra }) => (
            <tr key={key} className="border-b border-zinc-100 dark:border-zinc-800">
              <th scope="row" className="py-1.5 pr-3 font-medium">{name}</th>
              <td className="py-1.5 pr-3 font-mono tabular-nums">{formatLongitude(point.sidereal_longitude)}</td>
              <td className="py-1.5 pr-3">{point.nakshatra.name} {point.nakshatra.pada}</td>
              <td className="py-1.5 pr-3 tabular-nums">{extra ? extra.house : 1}</td>
              <td className="py-1.5 pr-3">{extra?.dignity ? title(extra.dignity) : "—"}</td>
              <td className="py-1.5 pr-3">
                {[extra?.retrograde && "Retrograde", extra?.combust && "Combust", extra?.gandanta && "Gandanta"]
                  .filter(Boolean)
                  .join(", ") || "—"}
              </td>
              <td className="py-1.5">
                {title(point.kp.star_lord)} / {title(point.kp.sub_lord)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
