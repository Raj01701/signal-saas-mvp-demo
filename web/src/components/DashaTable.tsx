import type { Schemas } from "@/lib/api/client";

type Period = Schemas["DashaPeriodOut"];

const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const day = (iso: string) => iso.slice(0, 10);

/** Mahadashas with their antardashas; the running periods are highlighted. */
export function DashaTable({ table, now }: { table: Schemas["DashaTableOut"]; now: string }) {
  const mahadashas = table.periods.filter((p) => p.lords.length === 1);
  const subs = (lord: Period) =>
    table.periods.filter((p) => p.lords.length === 2 && p.lords[0] === lord.lords[0] && p.start >= lord.start && p.end <= lord.end);
  const running = (p: Period) => p.start <= now && now < p.end;
  return (
    <div>
      <p className="mb-2 text-sm text-zinc-600 dark:text-zinc-400">
        {table.label}: born in the {title(table.birth_lord)} mahadasha with {table.balance_years.toFixed(2)} years to run.
      </p>
      <ul className="divide-y divide-zinc-100 text-sm dark:divide-zinc-800">
        {mahadashas.map((maha) => (
          <li key={maha.start}>
            <details open={running(maha)}>
              <summary className={`cursor-pointer py-1.5 ${running(maha) ? "font-semibold text-amber-700 dark:text-amber-400" : ""}`}>
                {title(maha.lords[0])} <span className="text-zinc-500">{day(maha.start)} to {day(maha.end)}</span>
              </summary>
              <ul className="mb-2 ml-5 grid gap-0.5 sm:grid-cols-2">
                {subs(maha).map((sub) => (
                  <li key={sub.start} className={running(sub) ? "font-semibold text-amber-700 dark:text-amber-400" : ""}>
                    {title(sub.lords[1])} <span className="text-zinc-500">{day(sub.start)} to {day(sub.end)}</span>
                  </li>
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
