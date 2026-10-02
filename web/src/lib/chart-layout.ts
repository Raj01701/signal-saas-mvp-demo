/**
 * Geometry of the three Indian chart styles in a 100 x 100 box, and grouping of
 * planets by sign. Signs are numbered 0 (Aries) to 11 (Pisces).
 *
 * - North Indian: houses are fixed (the lagna at the top), signs rotate.
 * - South Indian: signs are fixed in a ring of twelve cells, Pisces top-left.
 * - East Indian: signs are fixed, Aries at the top middle and running
 *   anticlockwise; corner squares hold two signs each.
 */

export type ChartStyle = "north" | "south" | "east";
export type Point = readonly [number, number];

export interface Cell {
  /** Sign in this cell (0 = Aries). */
  sign: number;
  /** House counted from the lagna (1-12). */
  house: number;
  points: Point[];
  /** Where to centre the cell's text. */
  anchor: Point;
}

const T = 100 / 3;

/** Centroid of a polygon (area-weighted). */
export function centroid(points: readonly Point[]): Point {
  let area = 0;
  let x = 0;
  let y = 0;
  points.forEach(([x0, y0], i) => {
    const [x1, y1] = points[(i + 1) % points.length];
    const cross = x0 * y1 - x1 * y0;
    area += cross;
    x += (x0 + x1) * cross;
    y += (y0 + y1) * cross;
  });
  return [x / (3 * area), y / (3 * area)];
}

export function polygonArea(points: readonly Point[]): number {
  let twice = 0;
  points.forEach(([x0, y0], i) => {
    const [x1, y1] = points[(i + 1) % points.length];
    twice += x0 * y1 - x1 * y0;
  });
  return Math.abs(twice) / 2;
}

/** North Indian houses 1-12, anticlockwise from the top diamond. */
const NORTH: Point[][] = [
  [[50, 0], [75, 25], [50, 50], [25, 25]],
  [[0, 0], [50, 0], [25, 25]],
  [[0, 0], [25, 25], [0, 50]],
  [[0, 50], [25, 25], [50, 50], [25, 75]],
  [[0, 50], [25, 75], [0, 100]],
  [[0, 100], [25, 75], [50, 100]],
  [[50, 100], [25, 75], [50, 50], [75, 75]],
  [[50, 100], [75, 75], [100, 100]],
  [[100, 100], [75, 75], [100, 50]],
  [[100, 50], [75, 75], [50, 50], [75, 25]],
  [[100, 50], [75, 25], [100, 0]],
  [[100, 0], [75, 25], [50, 0]],
];

const rect = (x: number, y: number, w: number, h: number): Point[] => [
  [x, y], [x + w, y], [x + w, y + h], [x, y + h],
]; // prettier-ignore

/** South Indian cells by sign. */
const SOUTH: Point[][] = [
  rect(25, 0, 25, 25), rect(50, 0, 25, 25), rect(75, 0, 25, 25), rect(75, 25, 25, 25),
  rect(75, 50, 25, 25), rect(75, 75, 25, 25), rect(50, 75, 25, 25), rect(25, 75, 25, 25),
  rect(0, 75, 25, 25), rect(0, 50, 25, 25), rect(0, 25, 25, 25), rect(0, 0, 25, 25),
]; // prettier-ignore

/** East Indian cells by sign. */
const EAST: Point[][] = [
  rect(T, 0, T, T),
  [[0, 0], [T, 0], [T, T]],
  [[0, 0], [T, T], [0, T]],
  rect(0, T, T, T),
  [[0, 2 * T], [T, 2 * T], [0, 100]],
  [[T, 2 * T], [T, 100], [0, 100]],
  rect(T, 2 * T, T, 100 - 2 * T),
  [[2 * T, 2 * T], [2 * T, 100], [100, 100]],
  [[2 * T, 2 * T], [100, 2 * T], [100, 100]],
  rect(2 * T, T, 100 - 2 * T, T),
  [[2 * T, T], [100, T], [100, 0]],
  [[2 * T, 0], [100, 0], [2 * T, T]],
]; // prettier-ignore

/** The twelve cells of a chart style for a lagna in ``ascendantSign``. */
export function chartCells(style: ChartStyle, ascendantSign: number): Cell[] {
  return Array.from({ length: 12 }, (_, i) => {
    const sign = style === "north" ? (ascendantSign + i) % 12 : i;
    const house = ((sign - ascendantSign + 12) % 12) + 1;
    const points = style === "north" ? NORTH[i] : style === "south" ? SOUTH[i] : EAST[i];
    return { sign, house, points, anchor: centroid(points) };
  });
}

export const PLANET_ABBREVIATIONS: Record<string, string> = {
  sun: "Su", moon: "Mo", mars: "Ma", mercury: "Me", jupiter: "Ju", venus: "Ve",
  saturn: "Sa", rahu: "Ra", ketu: "Ke", uranus: "Ur", neptune: "Ne", pluto: "Pl",
}; // prettier-ignore

export interface Placement {
  body: string;
  sign: number;
  retrograde?: boolean;
}

/** Planet labels by sign, in the order given, with "(R)" for retrograde ones. */
export function labelsBySign(placements: readonly Placement[]): Map<number, string[]> {
  const bySign = new Map<number, string[]>();
  for (const p of placements) {
    const label = (PLANET_ABBREVIATIONS[p.body] ?? p.body) + (p.retrograde ? "(R)" : "");
    bySign.set(p.sign, [...(bySign.get(p.sign) ?? []), label]);
  }
  return bySign;
}
