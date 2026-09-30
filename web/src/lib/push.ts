/**
 * Reminder notifications through Web Push. The browser subscribes with the API's VAPID
 * key and hands over the reminders it computed itself (a moment and a short text each);
 * no birth details leave the device. See `jyotish_api/push.py` for the server side.
 */

import { api } from "@/lib/api/client";

export interface PushReminder {
  /** ISO instant (UTC). */
  at: string;
  title: string;
  body: string;
}

export type PushState = "unsupported" | "off" | "on" | "denied";

export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window
  );
}

/** Base64url (as the API serves the key) to the bytes `applicationServerKey` takes. */
export function base64UrlToBytes(text: string): Uint8Array<ArrayBuffer> {
  const base64 = text.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(text.length / 4) * 4, "=");
  return Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
}

/** When a reminder for a calendar day (YYYY-MM-DD) is shown: 08:00 in the browser's zone. */
export function reminderMoment(day: string): string {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(year, month - 1, date, 8, 0, 0).toISOString();
}

async function subscription(): Promise<PushSubscription | null> {
  const registration = await navigator.serviceWorker.getRegistration("/");
  return registration ? registration.pushManager.getSubscription() : null;
}

function subscriptionBody(sub: PushSubscription) {
  const json = sub.toJSON();
  return { endpoint: json.endpoint ?? "", keys: { p256dh: json.keys?.p256dh ?? "", auth: json.keys?.auth ?? "" } };
}

async function save(sub: PushSubscription, reminders: PushReminder[]): Promise<void> {
  const { error } = await api.PUT("/v1/push/subscription", {
    body: { subscription: subscriptionBody(sub), reminders: reminders.slice(0, 60) },
  });
  if (error) throw new Error("the reminders could not be saved");
}

/** Whether this browser can get reminders (the API has push turned on) and has them on. */
export async function pushState(): Promise<PushState> {
  if (!pushSupported()) return "unsupported";
  const { data } = await api.GET("/v1/push/key");
  if (!data) return "unsupported";
  if (Notification.permission === "denied") return "denied";
  return Notification.permission === "granted" && (await subscription()) ? "on" : "off";
}

/** Ask for permission, subscribe this browser and save its reminders. */
export async function enablePush(reminders: PushReminder[]): Promise<PushState> {
  const { data } = await api.GET("/v1/push/key");
  if (!pushSupported() || !data) return "unsupported";
  if ((await Notification.requestPermission()) !== "granted") return "denied";
  await navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" });
  const registration = await navigator.serviceWorker.ready;
  const sub =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64UrlToBytes(data.public_key),
    }));
  await save(sub, reminders);
  return "on";
}

/** Replace the saved reminders with the current ones (when reminders are on). */
export async function refreshPush(reminders: PushReminder[]): Promise<void> {
  const sub = await subscription();
  if (sub) await save(sub, reminders);
}

/** Forget this browser's subscription on the server, then unsubscribe it. */
export async function disablePush(): Promise<PushState> {
  const sub = await subscription();
  if (sub) {
    const { endpoint, keys } = subscriptionBody(sub);
    await api.POST("/v1/push/unsubscribe", { body: { endpoint, auth: keys.auth } });
    await sub.unsubscribe();
  }
  return "off";
}
