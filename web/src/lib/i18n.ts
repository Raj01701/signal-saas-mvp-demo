"use client";

import { useSyncExternalStore } from "react";

import { type Dictionary, en, hi } from "@/lib/dictionaries";

export type Lang = "en" | "hi";

const KEY = "jyotish.lang";
const EVENT = "jyotish:lang";
const DICTIONARIES: Record<Lang, Dictionary> = { en, hi };

function read(): Lang {
  try {
    return localStorage.getItem(KEY) === "hi" ? "hi" : "en";
  } catch {
    return "en";
  }
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** Choose the interface language; remembered on this device. */
export function setLang(lang: Lang): void {
  try {
    localStorage.setItem(KEY, lang);
  } catch {
    // Storage may be unavailable (private mode); the choice then lasts for this page only.
  }
  document.documentElement.lang = lang;
  window.dispatchEvent(new Event(EVENT));
}

/** The current language and its dictionary. The server always renders English. */
export function useI18n(): { lang: Lang; t: Dictionary } {
  const lang = useSyncExternalStore(subscribe, read, () => "en" as Lang);
  return { lang, t: DICTIONARIES[lang] };
}

/** A date as "10 Oct 2026" or "10 अक्टू॰ 2026". */
export function formatDate(iso: string, lang: Lang, withYear = true): string {
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  return date.toLocaleDateString(lang === "hi" ? "hi-IN" : "en-GB", {
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
    timeZone: "UTC",
  });
}

/** A month as "Oct 2026" or "अक्टू॰ 2026". */
export function formatMonth(iso: string, lang: Lang): string {
  const date = new Date(`${iso.slice(0, 7)}-01T00:00:00Z`);
  return date.toLocaleDateString(lang === "hi" ? "hi-IN" : "en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
}
