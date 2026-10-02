"use client";

import { type FormEvent, useId, useState } from "react";

import { input, NEW_DELHI, PlaceField } from "@/components/PlaceField";
import { formatDate, useI18n } from "@/lib/i18n";
import { type Profile, type TimeSource } from "@/lib/profile";

const SOURCES: TimeSource[] = ["birth_certificate", "family_record", "memory", "estimate", "unknown"];
const EXACTNESS = [5, 15, 60, 120] as const;
const STEPS = 4;

/** Guided entry of the birth details, asking how the time is known and how exact it is. */
export function Onboarding({ initial, onDone }: { initial?: Profile | null; onDone: (profile: Profile) => void }) {
  const id = useId();
  const { t, lang } = useI18n();
  const o = t.onboarding;
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState<Profile>(
    initial ?? { name: "", date: "", time: "", location: NEW_DELHI, source: "birth_certificate", uncertainty: 5 },
  );
  const set = (change: Partial<Profile>) => setProfile({ ...profile, ...change });

  const next = (event: FormEvent) => {
    event.preventDefault();
    if (step < STEPS) setStep(step + 1);
    else onDone({ ...profile, time: profile.source === "unknown" ? "12:00" : profile.time });
  };

  const radio = "flex items-start gap-2 text-sm";
  return (
    <section aria-labelledby={`${id}-title`} className="grid gap-4 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div>
        <h2 id={`${id}-title`} className="text-xl font-semibold">{o.title}</h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{o.intro}</p>
        <p className="mt-1 text-xs font-medium text-amber-800 dark:text-amber-400" aria-live="polite">
          {o.step(step, STEPS)}
        </p>
      </div>
      <form onSubmit={next} className="grid gap-4 sm:grid-cols-2" aria-label={o.title}>
        {step === 1 && (
          <>
            <label className="grid gap-1 text-sm font-medium sm:col-span-2" htmlFor={`${id}-name`}>
              {o.name}
              <input id={`${id}-name`} value={profile.name} onChange={(e) => set({ name: e.target.value })} className={input} autoComplete="given-name" />
            </label>
            <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-date`}>
              {t.fields.date}
              <input id={`${id}-date`} type="date" required value={profile.date} onChange={(e) => set({ date: e.target.value })} className={input} />
            </label>
          </>
        )}
        {step === 2 && (
          <>
            <fieldset className="grid gap-2 sm:col-span-2">
              <legend className="mb-1 text-sm font-medium">{o.source}</legend>
              {SOURCES.map((source) => (
                <label key={source} className={radio} htmlFor={`${id}-source-${source}`}>
                  <input
                    id={`${id}-source-${source}`}
                    type="radio"
                    name={`${id}-source`}
                    checked={profile.source === source}
                    onChange={() => set({ source, uncertainty: source === "unknown" ? 120 : profile.uncertainty })}
                  />
                  {o.sources[source]}
                </label>
              ))}
            </fieldset>
            {profile.source !== "unknown" && (
              <>
                <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-time`}>
                  {t.fields.time}
                  <input id={`${id}-time`} type="time" step="60" required value={profile.time} onChange={(e) => set({ time: e.target.value })} className={input} />
                </label>
                <fieldset className="grid gap-2">
                  <legend className="mb-1 text-sm font-medium">{o.exact}</legend>
                  {EXACTNESS.map((minutes) => (
                    <label key={minutes} className={radio} htmlFor={`${id}-exact-${minutes}`}>
                      <input
                        id={`${id}-exact-${minutes}`}
                        type="radio"
                        name={`${id}-exact`}
                        checked={profile.uncertainty === minutes}
                        onChange={() => set({ uncertainty: minutes })}
                      />
                      {o.exactness[minutes]}
                    </label>
                  ))}
                </fieldset>
              </>
            )}
          </>
        )}
        {step === 3 && <PlaceField label={t.fields.place} value={profile.location} onChange={(location) => set({ location })} />}
        {step === 4 && (
          <div className="grid gap-1 text-sm sm:col-span-2">
            <h3 className="font-semibold">{o.review}</h3>
            <p>{profile.name}</p>
            <p>
              {profile.date ? formatDate(profile.date, lang) : ""}
              {profile.source !== "unknown" ? `, ${profile.time}` : ""} · {profile.location.place.name ?? ""}
            </p>
            <p>{o.sources[profile.source]}{profile.source !== "unknown" ? ` · ${o.exactness[profile.uncertainty as (typeof EXACTNESS)[number]]}` : ""}</p>
            <p className="text-xs text-zinc-500">{o.stored}</p>
          </div>
        )}
        <div className="flex gap-2 sm:col-span-2">
          {step > 1 && (
            <button type="button" onClick={() => setStep(step - 1)} className="rounded-md border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700">
              {o.back}
            </button>
          )}
          <button type="submit" className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800">
            {step < STEPS ? o.next : o.save}
          </button>
        </div>
      </form>
    </section>
  );
}
