import { describe, expect, it } from "vitest";

import { formatLongitude, normalizeDegrees, toDms } from "./angles";

describe("normalizeDegrees", () => {
  it("wraps negative and large angles into [0, 360)", () => {
    expect(normalizeDegrees(-30)).toBe(330);
    expect(normalizeDegrees(725)).toBe(5);
    expect(normalizeDegrees(360)).toBe(0);
  });
});

describe("toDms", () => {
  it("rounds to the nearest arcsecond", () => {
    expect(toDms(12.051944)).toEqual({ deg: 12, min: 3, sec: 7 });
  });
});

describe("formatLongitude", () => {
  it("names the sign and the position within it", () => {
    expect(formatLongitude(132.051944)).toBe("Leo 12°03′07″");
  });

  it("carries rounding across a sign boundary instead of printing 30°", () => {
    expect(formatLongitude(29.99999)).toBe("Taurus 00°00′00″");
  });

  it("wraps 360° back to Aries", () => {
    expect(formatLongitude(359.99999)).toBe("Aries 00°00′00″");
  });
});
