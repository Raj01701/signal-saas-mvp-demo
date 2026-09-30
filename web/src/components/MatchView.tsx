"use client";

import { type FormEvent, useId, useState } from "react";

import { BirthFields, birthValue, PresetField, toBirthInput } from "@/components/BirthFields";
import { Citation, Status, title } from "@/components/common";
import { input } from "@/components/PlaceField";
import { api, type Preset, type Schemas } from "@/lib/api/client";
import { kujaText, points } from "@/lib/format";
import { type Lang, useI18n } from "@/lib/i18n";
import { useLoad } from "@/lib/use-load";

const HINDI: Record<string, string> = {
  varna: "वर्ण",
  vashya: "वश्य",
  vasya: "वश्य",
  tara: "तारा",
  yoni: "योनि",
  graha_maitri: "ग्रह मैत्री",
  gana: "गण",
  bhakoot: "भकूट",
  nadi: "नाड़ी",
  dina: "दिन",
  mahendra: "माहेंद्र",
  stree_deergha: "स्त्री दीर्घ",
  rasi: "राशि",
  rasyadhipati: "राश्यधिपति",
  rajju: "रज्जु",
  vedha: "वेध",
};
const kootaName = (name: string, lang: Lang) => (lang === "hi" ? (HINDI[name] ?? title(name)) : title(name));

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
  const { t } = useI18n();
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
              [t.match.groom, groom, setGroom],
              [t.match.bride, bride, setBride],
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
            {t.match.tables}
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
              {t.match.submit}
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
  const { t, lang } = useI18n();
  if (!data) return <Status loading={loading} error={error} />;
  const m = t.match;
  const hindi = lang === "hi";
  const status = (d: Schemas["MatchDoshaOut"]) =>
    hindi
      ? d.cancelled ? "उपस्थित, अपवाद से निरस्त" : d.present ? "उपस्थित" : "अनुपस्थित"
      : d.cancelled ? "present, cancelled by an exception" : d.present ? "present" : "not present";
  const citations = [...data.ashtakoota.flatMap((k) => k.sources), ...data.doshas.flatMap((d) => d.sources), ...data.sources];
  const unique = [...new Map(citations.map((c) => [JSON.stringify(c), c])).values()];
  return (
    <div className="grid gap-8">
      <section aria-labelledby="ashtakoota-heading">
        <h2 id="ashtakoota-heading" className="mb-2 text-lg font-semibold">
          {m.total(points(data.ashtakoota_total))}
        </h2>
        <div role="region" tabIndex={0} aria-label={m.total(points(data.ashtakoota_total))} className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-zinc-500">
              <tr>
                <th scope="col" className={`${cell} font-normal`}>{m.koota}</th>
                <th scope="col" className={`${cell} font-normal`}>{m.groom}</th>
                <th scope="col" className={`${cell} font-normal`}>{m.bride}</th>
                <th scope="col" className={`${cell} font-normal`}>{m.points}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.ashtakoota.map((k) => (
                <tr key={k.name}>
                  <th scope="row" className={`${cell} font-medium`}>
                    {kootaName(k.name, lang)}
                    <p className="text-xs font-normal text-zinc-500" lang="en">{k.detail}</p>
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
        <h2 id="doshas-heading" className="mb-2 text-lg font-semibold">{m.doshas}</h2>
        <ul className="grid gap-1 text-sm">
          {data.doshas.map((d) => (
            <li key={d.name}>
              <span className="font-medium">
                {kootaName(d.name, lang)} {hindi ? "दोष" : "dosha"}
              </span>
              :{" "}
              {status(d)}
              {d.exceptions.length > 0 && <ul className="ml-5 list-disc text-zinc-600 dark:text-zinc-400">{d.exceptions.map((e) => <li key={e}>{e}</li>)}</ul>}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="kutas-heading">
        <h2 id="kutas-heading" className="mb-2 text-lg font-semibold">
          {m.kutas(data.dashakoota_agreements)}
        </h2>
        <div role="region" tabIndex={0} aria-label={m.kutas(data.dashakoota_agreements)} className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-zinc-500">
              <tr>
                <th scope="col" className={`${cell} font-normal`}>{m.kuta}</th>
                <th scope="col" className={`${cell} font-normal`}>{m.agrees}</th>
                <th scope="col" className={`${cell} font-normal`}>{m.detail}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.dashakoota.map((p) => (
                <tr key={p.name}>
                  <th scope="row" className={`${cell} font-medium`}>{kootaName(p.name, lang)}</th>
                  <td className={cell}>{p.agrees ? m.yes : m.no}</td>
                  <td className={cell} lang="en">
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
        <h2 id="kuja-heading" className="mb-2 text-lg font-semibold">{m.kuja}</h2>
        <ul className="grid gap-1">
          <li>{m.groom}: {kujaText(data.groom_kuja)}</li>
          <li>{m.bride}: {kujaText(data.bride_kuja)}</li>
        </ul>
        <p className="mt-1">
          {hindi
            ? data.kuja_balanced ? "संतुलित: दोनों कुंडलियों में कुज दोष की स्थिति समान है।" : "असंतुलित: केवल एक कुंडली मांगलिक है।"
            : data.kuja_balanced ? "Balanced: both charts have the same Kuja status." : "Not balanced: only one chart is manglik."}
        </p>
      </section>

      <section aria-labelledby="match-sources" className="text-sm">
        <h2 id="match-sources" className="mb-2 text-lg font-semibold">{m.sources}</h2>
        <p className="mb-1 text-zinc-600 dark:text-zinc-400">
          {hindi
            ? `कूट तालिकाएँ स्रोतों में भिन्न हैं; यह परिणाम ${data.profile} प्रोफ़ाइल पर आधारित है।`
            : `Koota tables differ between sources; this result uses the ${data.profile} profile.`}
        </p>
        <ul className="list-disc pl-5">{unique.map((c) => <Citation key={JSON.stringify(c)} c={c} />)}</ul>
      </section>
    </div>
  );
}
