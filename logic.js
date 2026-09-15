// Pure, DOM-free core logic for Signal. Imported by app.html and by logic.test.mjs.
export const STATUSES = { open: "Open", prog: "In progress", shipped: "Shipped", closed: "Closed" };
export const ORDER = ["open", "prog", "shipped", "closed"];
export const ROLES = ["Owner", "Admin", "Member", "Viewer"];

export function nextStatus(status) {
  const i = ORDER.indexOf(status);
  return ORDER[(i + 1) % ORDER.length];
}
export function advance(subs, id) {
  return subs.map(s => (s.id === id ? { ...s, status: nextStatus(s.status) } : s));
}
export function upvote(subs, id) {
  return subs.map(s => (s.id === id ? { ...s, votes: s.votes + 1 } : s));
}
export function remove(subs, id) {
  return subs.filter(s => s.id !== id);
}
export function addSubmission(subs, { title, by, id, now }) {
  const clean = String(title || "").trim();
  if (!clean) return subs;
  return [{
    id: id ?? now, title: clean,
    by: (String(by || "").trim()) || "You",
    votes: 1, status: "open", createdAt: new Date(now).toISOString(),
  }, ...subs];
}
export function counts(subs) {
  const c = { open: 0, prog: 0, shipped: 0, closed: 0 };
  for (const s of subs) if (c[s.status] != null) c[s.status]++;
  return { ...c, total: subs.length };
}

// Search + sort for the submissions table.
export function searchSort(subs, { q = "", sort = "votes" } = {}) {
  const needle = q.trim().toLowerCase();
  let out = subs.filter(s =>
    !needle ||
    s.title.toLowerCase().includes(needle) ||
    String(s.by).toLowerCase().includes(needle));
  const byNew = (a, b) => new Date(b.createdAt) - new Date(a.createdAt);
  if (sort === "votes") out = [...out].sort((a, b) => b.votes - a.votes || byNew(a, b));
  else if (sort === "new") out = [...out].sort(byNew);
  else if (sort === "status") out = [...out].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || b.votes - a.votes);
  return out;
}
export function topVoted(subs, n = 5) {
  return [...subs].sort((a, b) => b.votes - a.votes).slice(0, n);
}

// Submissions created per week bucket, oldest→newest, for the trend chart.
export function weeklyTrend(subs, nowMs, weeks = 8) {
  const WEEK = 7 * 86_400_000;
  const buckets = new Array(weeks).fill(0);
  for (const s of subs) {
    const t = new Date(s.createdAt).getTime();
    if (Number.isNaN(t)) continue;
    const ago = nowMs - t;
    if (ago < 0) { buckets[weeks - 1]++; continue; }
    const idx = weeks - 1 - Math.floor(ago / WEEK);
    if (idx >= 0 && idx < weeks) buckets[idx]++;
  }
  return buckets;
}

export function toggleUser(users, id) {
  return users.map(u => (u.id === id ? { ...u, active: !u.active } : u));
}
export function changeRole(users, id, role) {
  if (!ROLES.includes(role)) return users;
  return users.map(u => (u.id === id ? { ...u, role } : u));
}
export function addUser(users, { name, email, role = "Member", id, now }) {
  const nm = String(name || "").trim();
  const em = String(email || "").trim();
  if (!nm || !em) return users;
  return [...users, { id: id ?? now, name: nm, email: em, role: ROLES.includes(role) ? role : "Member", active: true }];
}

// Relative time — guarded against negative/zero edge cases.
export function relativeTime(fromISO, nowMs) {
  const then = new Date(fromISO).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Math.max(0, nowMs - then);
  const s = Math.floor(diff / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24); if (d < 7) return `${d}d ago`;
  return `${Math.floor(d / 7)}w ago`;
}
