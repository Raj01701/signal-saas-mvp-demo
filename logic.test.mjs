import { test } from "node:test";
import assert from "node:assert/strict";
import {
  nextStatus, advance, remove, addSubmission, counts, toggleUser, relativeTime, ORDER,
} from "./logic.js";

const sample = () => ([
  { id: 1, title: "A", by: "x", votes: 3, status: "open" },
  { id: 2, title: "B", by: "y", votes: 1, status: "prog" },
  { id: 3, title: "C", by: "z", votes: 2, status: "shipped" },
]);

test("nextStatus cycles through all statuses and wraps", () => {
  assert.equal(nextStatus("open"), "prog");
  assert.equal(nextStatus("prog"), "shipped");
  assert.equal(nextStatus("shipped"), "closed");
  assert.equal(nextStatus("closed"), "open"); // wrap
});

test("advance only changes the targeted item", () => {
  const out = advance(sample(), 1);
  assert.equal(out.find(s => s.id === 1).status, "prog");
  assert.equal(out.find(s => s.id === 2).status, "prog"); // untouched
  assert.equal(out.find(s => s.id === 3).status, "shipped");
});

test("counts are correct and total matches length", () => {
  const c = counts(sample());
  assert.equal(c.open, 1);
  assert.equal(c.prog, 1);
  assert.equal(c.shipped, 1);
  assert.equal(c.closed, 0);
  assert.equal(c.total, 3);
});

test("addSubmission prepends an open item with a date, defaults requester, ignores empty", () => {
  const now = Date.UTC(2026, 0, 1, 12, 0, 0);
  const out = addSubmission(sample(), { title: "  New idea  ", by: "", id: 99, now });
  assert.equal(out.length, 4);
  assert.equal(out[0].title, "New idea"); // trimmed
  assert.equal(out[0].by, "You");         // default
  assert.equal(out[0].status, "open");
  assert.equal(out[0].votes, 1);
  assert.ok(out[0].createdAt);            // has a date
  // empty title is a no-op
  assert.equal(addSubmission(sample(), { title: "   ", now }).length, 3);
});

test("remove deletes only the targeted item", () => {
  const out = remove(sample(), 2);
  assert.equal(out.length, 2);
  assert.equal(out.find(s => s.id === 2), undefined);
});

test("toggleUser flips only the targeted user", () => {
  const users = [{ id: 1, active: true }, { id: 2, active: false }];
  const out = toggleUser(users, 2);
  assert.equal(out.find(u => u.id === 2).active, true);
  assert.equal(out.find(u => u.id === 1).active, true);
});

test("relativeTime never goes negative and reads naturally", () => {
  const now = 1_000_000_000_000;
  assert.equal(relativeTime(new Date(now).toISOString(), now), "just now");
  assert.equal(relativeTime(new Date(now - 5 * 60_000).toISOString(), now), "5m ago");
  assert.equal(relativeTime(new Date(now - 3 * 3_600_000).toISOString(), now), "3h ago");
  assert.equal(relativeTime(new Date(now - 2 * 86_400_000).toISOString(), now), "2d ago");
  // future date must not render "in -1s"
  assert.equal(relativeTime(new Date(now + 99_999).toISOString(), now), "just now");
  assert.equal(relativeTime("not-a-date", now), "");
});

test("ORDER has the four expected statuses", () => {
  assert.deepEqual(ORDER, ["open", "prog", "shipped", "closed"]);
});
