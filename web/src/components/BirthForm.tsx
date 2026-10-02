"use client";

import { type FormEvent, useState } from "react";

import { BirthFields, birthValue, PresetField, toBirthInput } from "@/components/BirthFields";
import type { Preset, Schemas } from "@/lib/api/client";

export interface BirthRequest {
  birth: Schemas["BirthInput"];
  preset: Preset;
}

/** Birth date, time and place, with place search and a manual-coordinates fallback. */
export function BirthForm({ onSubmit, busy }: { onSubmit: (request: BirthRequest) => void; busy: boolean }) {
  const [birth, setBirth] = useState(() => birthValue("1990-05-17", "12:00:00"));
  const [preset, setPreset] = useState<Preset>("classic_parashari");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({ birth: toBirthInput(birth), preset });
  };

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label="Birth data">
      <BirthFields value={birth} onChange={setBirth} />
      <PresetField value={preset} onChange={setPreset} />
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
