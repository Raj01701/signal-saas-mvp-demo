/** Formatting helpers for ecliptic longitudes shown in the workbench. */

export const SIGNS = [
  "Aries",
  "Taurus",
  "Gemini",
  "Cancer",
  "Leo",
  "Virgo",
  "Libra",
  "Scorpio",
  "Sagittarius",
  "Capricorn",
  "Aquarius",
  "Pisces",
] as const;

export type SignName = (typeof SIGNS)[number];

/** Normalise any angle in degrees to the range [0, 360). */
export function normalizeDegrees(degrees: number): number {
  const wrapped = degrees % 360;
  return wrapped < 0 ? wrapped + 360 : wrapped;
}

/**
 * Split a longitude into whole degrees, arcminutes and arcseconds, rounding to
 * the nearest arcsecond and carrying overflow (e.g. 29°59′59.6″ → 30°00′00″).
 */
export function toDms(degrees: number): { deg: number; min: number; sec: number } {
  const totalSeconds = Math.round(Math.abs(degrees) * 3600);
  return {
    deg: Math.floor(totalSeconds / 3600),
    min: Math.floor((totalSeconds % 3600) / 60),
    sec: totalSeconds % 60,
  };
}

/** Format a sidereal longitude as sign plus degrees within the sign, e.g. `Leo 12°03′07″`. */
export function formatLongitude(longitude: number): string {
  const totalSeconds = Math.round(normalizeDegrees(longitude) * 3600) % (360 * 3600);
  const signIndex = Math.floor(totalSeconds / (30 * 3600));
  const { deg, min, sec } = toDms((totalSeconds - signIndex * 30 * 3600) / 3600);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${SIGNS[signIndex]} ${pad(deg)}°${pad(min)}′${pad(sec)}″`;
}
