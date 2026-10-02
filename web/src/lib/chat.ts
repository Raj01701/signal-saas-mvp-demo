/** The chat's conversation: what is sent to the API and what is kept on this device. */

import type { Schemas } from "@/lib/api/client";

export type Evidence = Schemas["EvidenceItem"];

export interface Turn {
  role: "user" | "assistant";
  content: string;
  /** For answers: the engine findings the answer rests on, and who wrote it. */
  evidence?: Evidence[];
  narrator?: string;
}

/** The API takes at most 20 messages of at most 4000 characters each. */
export const MAX_SENT = 20;
export const MAX_CHARS = 4000;
/** Turns kept on the device per chart. */
export const MAX_KEPT = 40;

/** The messages to send: the latest turns, starting with one of the person's own. */
export function outgoing(turns: Turn[]): Schemas["ChatMessage"][] {
  const recent = turns.slice(-MAX_SENT);
  const first = recent.findIndex((t) => t.role === "user");
  return recent
    .slice(Math.max(first, 0))
    .map(({ role, content }) => ({ role, content: content.slice(0, MAX_CHARS) }));
}

/** A storage key for one chart's conversation that does not reveal the birth details. */
export function chatKey(birth: unknown): string {
  const text = JSON.stringify(birth);
  let hash = 5381;
  for (let i = 0; i < text.length; i += 1) hash = ((hash * 33) ^ text.charCodeAt(i)) >>> 0;
  return `jyotish.chat.${hash.toString(36)}`;
}

/** A saved conversation, keeping only well-formed turns. */
export function parseTurns(raw: string | null): Turn[] {
  if (!raw) return [];
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (t): t is Turn =>
        !!t &&
        typeof t === "object" &&
        (t.role === "user" || t.role === "assistant") &&
        typeof t.content === "string" &&
        t.content.trim() !== "",
    )
    .slice(-MAX_KEPT);
}

export function loadTurns(key: string): Turn[] {
  try {
    return parseTurns(localStorage.getItem(key));
  } catch {
    return [];
  }
}

export function saveTurns(key: string, turns: Turn[]): void {
  try {
    if (turns.length) localStorage.setItem(key, JSON.stringify(turns.slice(-MAX_KEPT)));
    else localStorage.removeItem(key);
  } catch {
    // Without storage the conversation lasts for this page only.
  }
}
