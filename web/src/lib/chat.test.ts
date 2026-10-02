import { describe, expect, it } from "vitest";

import { chatKey, MAX_CHARS, MAX_KEPT, MAX_SENT, outgoing, parseTurns, type Turn } from "./chat";

const turn = (role: Turn["role"], content: string): Turn => ({ role, content });

describe("chat conversation", () => {
  it("sends the latest turns, starting with the person's own message", () => {
    const turns = Array.from({ length: 25 }, (_, i) => turn(i % 2 ? "assistant" : "user", `m${i}`));
    const sent = outgoing(turns);
    expect(sent.length).toBeLessThanOrEqual(MAX_SENT);
    expect(sent[0].role).toBe("user");
    expect(sent.at(-1)).toEqual({ role: "user", content: "m24" });
    expect(outgoing([turn("user", "x".repeat(MAX_CHARS + 10))])[0].content).toHaveLength(MAX_CHARS);
  });

  it("keys each chart's conversation without revealing the birth details", () => {
    const birth = { local_datetime: "1990-05-17T12:00:00", place: { name: "New Delhi" } };
    const key = chatKey(birth);
    expect(key).toMatch(/^jyotish\.chat\.[0-9a-z]+$/);
    expect(key).not.toContain("1990");
    expect(chatKey({ ...birth })).toBe(key);
    expect(chatKey({ ...birth, local_datetime: "1990-05-17T12:01:00" })).not.toBe(key);
  });

  it("restores only well-formed turns", () => {
    expect(parseTurns(null)).toEqual([]);
    expect(parseTurns("not json")).toEqual([]);
    expect(parseTurns('{"role":"user"}')).toEqual([]);
    const raw = JSON.stringify([turn("user", "hi"), { role: "system", content: "x" }, turn("assistant", " "), 3]);
    expect(parseTurns(raw)).toEqual([turn("user", "hi")]);
    const many = JSON.stringify(Array.from({ length: 50 }, (_, i) => turn("user", `q${i}`)));
    expect(parseTurns(many)).toHaveLength(MAX_KEPT);
  });
});
