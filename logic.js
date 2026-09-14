// Pure, DOM-free core logic for Signal. Imported by app.html and by logic.test.mjs.
export const STATUSES = { open: "Open", prog: "In progress", shipped: "Shipped", closed: "Closed" };
export const ORDER = ["open", "prog", "shipped", "closed"];

export function nextStatus(status) {
  const i = ORDER.indexOf(status);
  return ORDER[(i + 1) % ORDER.length];
}

export function advance(subs, id) {
  return subs.map(s => (s.id === id ? { ...s, status: nextStatus(s.status) } : s));
}

export function remove(subs, id) {
  return subs.filter(s => s.id !== id);
}

export function addSubmission(subs, { title, by, id, now }) {
  const clean = String(title || "").trim();
  if (!clean) return subs; // guard: never add empty
  const item = {
    id: id ?? now,
    title: clean,
    by: (String(by || "").trim()) || "You",
    votes: 1,
    status: "open",
    createdAt: new Date(now).toISOString(),
  };
  return [item, ...subs];
}

export function counts(subs) {
  const c = { open: 0, prog: 0, shipped: 0, closed: 0 };
  for (const s of subs) if (c[s.status] != null) c[s.status]++;
  return { ...c, total: subs.length };
}

export function toggleUser(users, id) {
  return users.map(u => (u.id === id ? { ...u, active: !u.active } : u));
}

// Relative time — a classic source of off-by-one / negative-value bugs. Guarded + tested.
export function relativeTime(fromISO, nowMs) {
  const then = new Date(fromISO).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Math.max(0, nowMs - then);            // never show negative ("in -1s")
  const s = Math.floor(diff / 1000);
  if (s < 60) return "just now";                     // avoid "0m ago"
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  const w = Math.floor(d / 7);
  return `${w}w ago`;
}
