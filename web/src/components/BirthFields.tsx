"use client";

import { useId } from "react";

import { input, NEW_DELHI, PlaceField, type PlaceValue } from "@/components/PlaceField";
import type { Preset, Schemas } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n";

/** Birth date and local time as the form holds them, plus the place. */
export interface BirthValue {
  date: string;
  time: string;
  location: PlaceValue;
}

export const PRESETS: { value: Preset; label: string }[] = [
  { value: "classic_parashari", label: "Classic Parashari (Lahiri, true nodes)" },
  { value: "drik_compatible", label: "Drik Panchang compatible" },
  { value: "kp", label: "KP (Krishnamurti, Placidus)" },
  { value: "pvr_jhora_style", label: "PVR / JHora style (True Pushya)" },
];

export function birthValue(date: string, time: string, location: PlaceValue = NEW_DELHI): BirthValue {
  return { date, time, location };
}

/** The API's birth input for a form value; times without seconds get ":00". */
export function toBirthInput({ date, time, location }: BirthValue): Schemas["BirthInput"] {
  const seconds = time.length === 5 ? `${time}:00` : time;
  return { local_datetime: `${date}T${seconds}`, place: location.place, zone: location.zone };
}

/** Date, local time and place of birth: five cells of a two-column grid. */
export function BirthFields({ value, onChange }: { value: BirthValue; onChange: (value: BirthValue) => void }) {
  const id = useId();
  const { t } = useI18n();
  return (
    <>
      <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-date`}>
        {t.fields.date}
        <input
          id={`${id}-date`}
          type="date"
          required
          value={value.date}
          onChange={(e) => onChange({ ...value, date: e.target.value })}
          className={input}
        />
      </label>
      <label className="grid gap-1 text-sm font-medium" htmlFor={`${id}-time`}>
        {t.fields.time}
        <input
          id={`${id}-time`}
          type="time"
          step="1"
          required
          value={value.time}
          onChange={(e) => onChange({ ...value, time: e.target.value })}
          className={input}
        />
      </label>
      <PlaceField label={t.fields.place} value={value.location} onChange={(location) => onChange({ ...value, location })} />
    </>
  );
}

/** The calculation-settings preset select. */
export function PresetField({ value, onChange }: { value: Preset; onChange: (value: Preset) => void }) {
  const id = useId();
  const { t } = useI18n();
  return (
    <label className="grid gap-1 text-sm font-medium sm:col-span-2" htmlFor={`${id}-preset`}>
      {t.fields.settings}
      <select id={`${id}-preset`} value={value} onChange={(e) => onChange(e.target.value as Preset)} className={input}>
        {PRESETS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>
    </label>
  );
}
