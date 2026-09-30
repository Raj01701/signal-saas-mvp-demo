"use client";

import { type FormEvent, useId, useState } from "react";

import { BirthFields, birthValue, PresetField, toBirthInput } from "@/components/BirthFields";
import { Citation, Status, title } from "@/components/common";
import { input } from "@/components/PlaceField";
import { api, type Preset, type Schemas } from "@/lib/api/client";
import { kujaText, points } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

type MatchRequest = Schemas["MatchRequest"];
type Profile = Schemas["KootaProfile"];

const PROFILES: { value: Profile; label: string }[] = [
  { value: "popular", label: "Popular tables (most Indian software)" },
  { value: "maitreya", label: "Maitreya tables" },
];
const cell = "py-1.5 pr-3 align-top";

/** Horoscope matching: Ashtakoota with its doshas, Raman's ten kutas and Kuja dosha. */
export function MatchView() {
  const id = useId();
  const [groom, setGroom] = useState(() => birthValue("1990-05-17", "12:00:00"));
  const [bride, setBride] = useState(() => birthValue("1993-11-02", "06:30:00"));
  const [preset, setPreset] = useState<Preset>("classic_parashari");
  const [profile, setProfile] = useState<Profile>("popular");
  const [request, setRequest] = useState<MatchRequest | null>(null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setRequest({ groom: toBirthInput(groom), bride: toBirthInput(bride), preset, profile });
  };

  return (
    <div className="grid gap-8">
      <form onSubmit={submit} className="grid gap-6 print:hidden" aria-label="Birth data of both partners">
        <div className="grid gap-6 lg:grid-cols-2">
          {(
            [
              ["Groom", groom, setGroom],
              ["Bride", bride, setBride],
            ] as const
          ).map(([name, value, set]) => (
            <fieldset key={name} className="grid gap-4 rounded-lg border border-zinc-200 p-4 sm:grid-cols-2 dark:border-zinc-800">
              <legend className="px-1 text-lg font-semibold">{name}</legend>
              <BirthFields value={value} onChange={set} />
            </fieldset>
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <PresetField value={preset} onChange={setPreset} />
          <label className="grid gap-1 text-sm font-medium sm:col-span-2" htmlFor={`${id}-profile`}>
            Koota tables
            <select id={`${id}-profile`} value={profile} onChange={(e) => setProfile(e.target.value as Profile)} className={input}>
              {PROFILES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <div>
            <button type="submit" className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800">
              Match charts
            </button>
          </div>
        </div>
      </form>
      {request && <MatchResult request={request} />}
    </div>
  );
}

function MatchResult({ request }: { request: MatchRequest }) {
  const { data, error, loading } = useLoad(JSON.stringify(request), () => api.POST("/v1/match", { body: request }));
  if (!data) return <Status loading={loading} error={error} />;
  const citations = [...data.ashtakoota.flatMap((k) => k.sources), ...data.doshas.flatMap((d) => d.sources), ...data.sources];
  const unique = [...new Map(citations.map((c) => [JSON.stringify(c), c])).values()];
  return (
    <div className="grid gap-8">
      <section aria-labelledby="ashtakoota-heading">
        <h2 id="ashtakoota-heading" className="mb-2 text-lg font-semibold">
          Ashtakoota: {points(data.ashtakoota_total)} of 36
        </h2>
        <div role="region" tabIndex={0} aria-label="Ashtakoota points" className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-zinc-500">
              <tr>
                <th scope="col" className={`${cell} font-normal`}>Koota</th>
                <th scope="col" className={`${cell} font-normal`}>Groom</th>
                <th scope="col" className={`${cell} font-normal`}>Bride</th>
                <th scope="col" className={`${cell} font-normal`}>Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.ashtakoota.map((k) => (
                <tr key={k.name}>
                  <th scope="row" className={`${cell} font-medium`}>
                    {title(k.name)}
                    <p className="text-xs font-normal text-zinc-500">{k.detail}</p>
                  </th>
                  <td className={cell}>{k.groom}</td>
                  <td className={cell}>{k.bride}</td>
                  <td className={`${cell} whitespace-nowrap`}>
                    {points(k.points)} / {points(k.maximum)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="doshas-heading">
        <h2 id="doshas-heading" className="mb-2 text-lg font-semibold">Doshas</h2>
        <ul className="grid gap-1 text-sm">
          {data.doshas.map((d) => (
            <li key={d.name}>
              <span className="font-medium">{title(d.name)} dosha</span>:{" "}
              {d.cancelled ? "present, cancelled by an exception" : d.present ? "present" : "not present"}
              {d.exceptions.length > 0 && <ul className="ml-5 list-disc text-zinc-600 dark:text-zinc-400">{d.exceptions.map((e) => <li key={e}>{e}</li>)}</ul>}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="kutas-heading">
        <h2 id="kutas-heading" className="mb-2 text-lg font-semibold">
          Ten kutas (South Indian): {data.dashakoota_agreements} of 10 agree
        </h2>
        <div role="region" tabIndex={0} aria-label="Ten kutas" className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-zinc-500">
              <tr>
                <th scope="col" className={`${cell} font-normal`}>Kuta</th>
                <th scope="col" className={`${cell} font-normal`}>Agrees</th>
                <th scope="col" className={`${cell} font-normal`}>Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.dashakoota.map((p) => (
                <tr key={p.name}>
                  <th scope="row" className={`${cell} font-medium`}>{title(p.name)}</th>
                  <td className={cell}>{p.agrees ? "Yes" : "No"}</td>
                  <td className={cell}>
                    {p.detail}
                    {p.relieved_by && <span className="text-zinc-500"> (relieved: {p.relieved_by})</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="kuja-heading" className="text-sm">
        <h2 id="kuja-heading" className="mb-2 text-lg font-semibold">Kuja dosha</h2>
        <ul className="grid gap-1">
          <li>Groom: {kujaText(data.groom_kuja)}</li>
          <li>Bride: {kujaText(data.bride_kuja)}</li>
        </ul>
        <p className="mt-1">
          {data.kuja_balanced ? "Balanced: both charts have the same Kuja status." : "Not balanced: only one chart is manglik."}
        </p>
      </section>

      <section aria-labelledby="match-sources" className="text-sm">
        <h2 id="match-sources" className="mb-2 text-lg font-semibold">Sources</h2>
        <p className="mb-1 text-zinc-600 dark:text-zinc-400">
          Koota tables differ between sources; this result uses the {data.profile} profile.
        </p>
        <ul className="list-disc pl-5">{unique.map((c) => <Citation key={JSON.stringify(c)} c={c} />)}</ul>
      </section>
    </div>
  );
}
