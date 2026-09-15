import { test } from "node:test";
import assert from "node:assert/strict";
import {
  nextStatus, advance, upvote, counts, searchSort, topVoted, weeklyTrend,
  toggleUser, changeRole, relativeTime, permissions, parseSubmission, parseInvite,
  memberChangeError, ORDER, ROLES,
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
test("parseSubmission trims, defaults requester, rejects empty/too long", () => {
  assert.deepEqual(parseSubmission({ title: "  New  ", by: "" }), { value: { title: "New", requester: "You" } });
  assert.ok(parseSubmission({ title: "   " }).error);
  assert.ok(parseSubmission({ title: "x".repeat(201) }).error);
  assert.ok(parseSubmission({ title: "ok", by: "y".repeat(81) }).error);
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
test("parseInvite requires name + valid email, normalises, refuses Owner", () => {
  assert.deepEqual(parseInvite({ name: " Sam ", email: " Sam@X.co " }), { value: { name: "Sam", email: "sam@x.co", role: "Member" } });
  assert.ok(parseInvite({ name: "", email: "s@x.co" }).error);
  assert.ok(parseInvite({ name: "Sam", email: "not-an-email" }).error);
  assert.ok(parseInvite({ name: "Sam", email: "s@x.co", role: "Owner" }).error);
  assert.equal(parseInvite({ name: "Sam", email: "s@x.co", role: "Viewer" }).value.role, "Viewer");
});
test("permissions per role", () => {
  assert.deepEqual(permissions("Owner"), { write: true, manage: true });
  assert.deepEqual(permissions("Admin"), { write: true, manage: true });
  assert.deepEqual(permissions("Member"), { write: true, manage: false });
  assert.deepEqual(permissions("Viewer"), { write: false, manage: false });
  assert.deepEqual(permissions("Wizard"), { write: false, manage: false });
});
test("memberChangeError guards owner, self, admins and bad input", () => {
  const owner = { id: 1, role: "Owner" }, admin = { id: 2, role: "Admin" };
  const member = { id: 3, role: "Member" }, admin2 = { id: 4, role: "Admin" };
  assert.equal(memberChangeError(owner, member, { op: "role", role: "Admin" }), null);
  assert.equal(memberChangeError(admin, member, { op: "toggle" }), null);
  assert.equal(memberChangeError(owner, admin, { op: "toggle" }), null);
  assert.ok(memberChangeError(member, admin, { op: "toggle" }));               // members can't manage
  assert.ok(memberChangeError(admin, admin, { op: "toggle" }));                // not yourself
  assert.ok(memberChangeError(admin, owner, { op: "role", role: "Viewer" }));  // owner is fixed
  assert.ok(memberChangeError(admin, admin2, { op: "toggle" }));               // only owner changes admins
  assert.ok(memberChangeError(owner, member, { op: "role", role: "Owner" }));  // no ownership transfer
  assert.ok(memberChangeError(owner, member, { op: "role", role: "Wizard" }));
  assert.ok(memberChangeError(owner, member, { op: "delete" }));
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
