import { describe, expect, it } from "vitest";

import { chartCells, centroid, labelsBySign, polygonArea } from "./chart-layout";

describe("chart layouts", () => {
  it.each(["north", "south", "east"] as const)("%s cells do not overlap and name each sign once", (style) => {
    const cells = chartCells(style, 4);
    expect(new Set(cells.map((c) => c.sign)).size).toBe(12);
    expect(new Set(cells.map((c) => c.house)).size).toBe(12);
    const area = cells.reduce((sum, c) => sum + polygonArea(c.points), 0);
    // North and East fill the square; South leaves its 50 x 50 centre empty.
    expect(area).toBeCloseTo(style === "south" ? 7500 : style === "north" ? 10000 : 10000 - 10000 / 9, 6);
  });

  it("puts the lagna at the top in the North Indian style", () => {
    const [first] = chartCells("north", 7);
    expect(first.sign).toBe(7);
    expect(first.house).toBe(1);
    expect(first.anchor[0]).toBeCloseTo(50);
    expect(first.anchor[1]).toBeLessThan(50);
  });

  it("fixes the signs in the South and East Indian styles", () => {
    const south = chartCells("south", 3);
    expect(south[0].points[0]).toEqual([25, 0]); // Aries, top row
    expect(south[11].points[0]).toEqual([0, 0]); // Pisces, top-left
    expect(south[3].house).toBe(1); // Cancer holds the lagna
    const east = chartCells("east", 0);
    expect(east[0].anchor[0]).toBeCloseTo(50); // Aries at the top middle
    expect(east[3].anchor[0]).toBeLessThan(20); // Cancer on the left
    expect(east[9].anchor[0]).toBeGreaterThan(80); // Capricorn on the right
  });

  it("computes centroids and groups labels", () => {
    expect(centroid([[0, 0], [10, 0], [10, 10], [0, 10]])).toEqual([5, 5]);
    const labels = labelsBySign([
      { body: "sun", sign: 1 },
      { body: "saturn", sign: 1, retrograde: true },
      { body: "moon", sign: 5 },
    ]);
    expect(labels.get(1)).toEqual(["Su", "Sa(R)"]);
    expect(labels.get(5)).toEqual(["Mo"]);
  });
});
