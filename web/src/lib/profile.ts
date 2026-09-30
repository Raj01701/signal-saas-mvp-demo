"use client";

import { useSyncExternalStore } from "react";

import type { PlaceValue } from "@/components/PlaceField";
import type { Schemas } from "@/lib/api/client";

export type TimeSource = "birth_certificate" | "family_record" | "memory" | "estimate" | "unknown";

/** The consumer's own birth details, kept only in this browser. */
export interface Profile {
  name: string;
  date: string;
  time: string;
  location: PlaceValue;
  source: TimeSource;
  /** Plus or minus minutes. */
  uncertainty: number;
}

const KEY = "jyotish.profile";
const EVENT = "jyotish:profile";
let cache: { raw: string | null; value: Profile | null } = { raw: null, value: null };

function read(): Profile | null {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    raw = null;
  }
  if (raw !== cache.raw) {
    let value: Profile | null = null;
    try {
      value = raw ? (JSON.parse(raw) as Profile) : null;
    } catch {
      value = null;
    }
    cache = { raw, value };
  }
  return cache.value;
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** The saved profile: ``undefined`` while not yet known (server render), ``null`` if none. */
export function useProfile(): Profile | null | undefined {
  return useSyncExternalStore(subscribe, read, () => undefined);
}

export function saveProfile(profile: Profile | null): void {
  try {
    if (profile) localStorage.setItem(KEY, JSON.stringify(profile));
    else localStorage.removeItem(KEY);
  } catch {
    // Without storage the profile lasts for this page only.
  }
  window.dispatchEvent(new Event(EVENT));
}

/** The API's birth input for a profile. */
export function birthOf(profile: Profile): Schemas["BirthInput"] {
  const seconds = profile.time.length === 5 ? `${profile.time}:00` : profile.time;
  return {
    local_datetime: `${profile.date}T${seconds}`,
    place: profile.location.place,
    zone: profile.location.zone,
    time_source: profile.source,
    uncertainty_minutes: profile.uncertainty,
  };
}
