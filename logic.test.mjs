import { test } from "node:test";
import assert from "node:assert/strict";
import {
  nextStatus, advance, upvote, remove, addSubmission, counts,
  searchSort, topVoted, weeklyTrend, toggleUser, changeRole, addUser,
  relativeTime, ORDER, ROLES,
} from "./logic.js";

const now = Date.UTC(2026, 0, 30, 12, 0, 0), DAY = 86_400_000;
const sample = () => ([
  { id: 1, title: "Slack alerts", by: "Priya", votes: 42, status: "prog", createdAt: new Date(now - 1 * DAY).toISOString() },
  { id: 2, title: "CSV export", by: "Daniel", votes: 28, status: "open", createdAt: new Date(now - 8 * DAY).toISOString() },
  { id: 3, title: "Dark mode", by: "Lucia", votes: 19, status: "shipped", createdAt: new Date(now - 20 * DAY).toISOString() },
]);

test("nextStatus cycles and wraps", () => {
  assert.equal(nextStatus("open"), "prog");
  assert.equal(nextStatus("closed"), "open");
});
test("advance only touches the target", () => {
  const o = advance(sample(), 1);
  assert.equal(o.find(s => s.id === 1).status, "shipped"); // prog -> shipped
  assert.equal(o.find(s => s.id === 2).status, "open");
});
test("upvote increments only the target", () => {
  const o = upvote(sample(), 2);
  assert.equal(o.find(s => s.id === 2).votes, 29);
  assert.equal(o.find(s => s.id === 1).votes, 42);
});
test("counts + total", () => {
  const c = counts(sample());
  assert.equal(c.open, 1); assert.equal(c.prog, 1); assert.equal(c.shipped, 1); assert.equal(c.total, 3);
});
test("addSubmission trims, defaults, ignores empty", () => {
  const o = addSubmission(sample(), { title: "  New  ", by: "", id: 99, now });
  assert.equal(o[0].title, "New"); assert.equal(o[0].by, "You"); assert.equal(o[0].status, "open");
  assert.equal(addSubmission(sample(), { title: "  ", now }).length, 3);
});
test("searchSort filters by title/requester and sorts", () => {
  assert.equal(searchSort(sample(), { q: "csv" }).length, 1);
  assert.equal(searchSort(sample(), { q: "priya" })[0].id, 1);
  assert.equal(searchSort(sample(), { sort: "votes" })[0].id, 1);   // 42 highest
  assert.equal(searchSort(sample(), { sort: "new" })[0].id, 1);     // most recent
  assert.equal(searchSort(sample(), { sort: "status" })[0].status, "open"); // ORDER first
});
test("topVoted returns n highest", () => {
  const t = topVoted(sample(), 2);
  assert.equal(t.length, 2); assert.equal(t[0].id, 1); assert.equal(t[1].id, 2);
});
test("weeklyTrend buckets oldest->newest, length weeks", () => {
  const b = weeklyTrend(sample(), now, 4);
  assert.equal(b.length, 4);
  assert.equal(b.reduce((a, x) => a + x, 0), 3); // all three counted within 4 weeks
  assert.ok(b[3] >= 1); // the 1-day-old item lands in the newest bucket
});
test("changeRole validates role", () => {
  const users = [{ id: 1, role: "Member" }];
  assert.equal(changeRole(users, 1, "Admin")[0].role, "Admin");
  assert.equal(changeRole(users, 1, "Wizard")[0].role, "Member"); // rejected
});
test("addUser requires name+email, defaults role", () => {
  const users = [];
  assert.equal(addUser(users, { name: "Sam", email: "s@x.co", id: 5 }).length, 1);
  assert.equal(addUser(users, { name: "Sam", email: "s@x.co", id: 5 })[0].role, "Member");
  assert.equal(addUser(users, { name: "", email: "s@x.co" }).length, 0);
});
test("toggleUser flips target only", () => {
  const u = toggleUser([{ id: 1, active: true }, { id: 2, active: false }], 2);
  assert.equal(u.find(x => x.id === 2).active, true);
});
test("relativeTime guards negatives + bad input", () => {
  assert.equal(relativeTime(new Date(now).toISOString(), now), "just now");
  assert.equal(relativeTime(new Date(now - 5 * 60_000).toISOString(), now), "5m ago");
  assert.equal(relativeTime(new Date(now + 99_999).toISOString(), now), "just now");
  assert.equal(relativeTime("nope", now), "");
});
test("constants intact", () => {
  assert.deepEqual(ORDER, ["open", "prog", "shipped", "closed"]);
  assert.deepEqual(ROLES, ["Owner", "Admin", "Member", "Viewer"]);
});
