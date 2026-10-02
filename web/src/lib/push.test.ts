import { describe, expect, it } from "vitest";

import { base64UrlToBytes, reminderMoment } from "./push";

describe("push helpers", () => {
  it("decodes base64url keys without padding", () => {
    expect(Array.from(base64UrlToBytes("AQID"))).toEqual([1, 2, 3]);
    expect(Array.from(base64UrlToBytes("-_8"))).toEqual([251, 255]);
    // An application server key is a 65-byte uncompressed P-256 point.
    const key = "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8";
    const bytes = base64UrlToBytes(key);
    expect(bytes.length).toBe(65);
    expect(bytes[0]).toBe(4);
  });

  it("shows a day's reminder at 08:00 local time", () => {
    const moment = new Date(reminderMoment("2027-03-05"));
    expect([moment.getFullYear(), moment.getMonth(), moment.getDate(), moment.getHours()]).toEqual([2027, 2, 5, 8]);
  });
});
