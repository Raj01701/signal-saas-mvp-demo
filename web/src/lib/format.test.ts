import { describe, expect, it } from "vitest";

import { toBirthInput } from "@/components/BirthFields";
import { NEW_DELHI } from "@/components/PlaceField";

import { clock, kujaText, longDate, offsetLabel, points, toneOf, yearly } from "./format";

describe("panchanga formatting", () => {
  it("labels UTC offsets", () => {
    expect(offsetLabel(19800)).toBe("UTC+05:30");
    expect(offsetLabel(-12600)).toBe("UTC−03:30");
    expect(offsetLabel(0)).toBe("UTC+00:00");
  });

  it("rounds to the local minute and names another day", () => {
    expect(clock("2026-09-30T09:25:50.593Z", 19800, "2026-09-30")).toBe("14:56");
    expect(clock("2026-09-30T09:25:29Z", 19800, "2026-09-30")).toBe("14:55");
    expect(clock("2026-09-30T19:00:00Z", 19800, "2026-09-30")).toBe("00:30, 1 Oct");
    expect(longDate("2026-09-30")).toBe("30 September 2026");
  });
});

describe("matching formatting", () => {
  it("shows half points only when present", () => {
    expect(points(20)).toBe("20");
    expect(points(27.5)).toBe("27.5");
  });

  it("describes Kuja dosha", () => {
    expect(kujaText({ manglik: false, present: [], cancelled: [] })).toBe("Not manglik");
    expect(kujaText({ manglik: true, present: ["dosha.kuja_moon"], cancelled: ["dosha.kuja_lagna"] })).toBe(
      "Manglik (dosha from the Moon; from the lagna the dosha is cancelled by an exception)",
    );
    expect(
      kujaText({ manglik: false, present: [], cancelled: ["dosha.kuja_lagna", "dosha.kuja_moon", "dosha.kuja_venus"] }),
    ).toBe("Not manglik (from the lagna, the Moon and Venus the dosha is cancelled by an exception)");
  });
});

describe("birth input", () => {
  it("adds seconds to times without them", () => {
    expect(toBirthInput({ date: "1990-05-17", time: "12:00", location: NEW_DELHI })).toEqual({
      local_datetime: "1990-05-17T12:00:00",
      place: NEW_DELHI.place,
      zone: null,
    });
  });
});

describe("prediction timeline", () => {
  it("keeps each year's strongest month", () => {
    const months = ["2020-01-01", "2020-02-01", "2021-01-01"];
    const years = yearly(months, { scores: [0.2, 0.5, 0.1], tones: [0.3, -0.4, 0] });
    expect(years.get(2020)).toEqual({ score: 0.5, tone: -0.4 });
    expect(years.get(2021)).toEqual({ score: 0.1, tone: 0 });
  });

  it("names tones", () => {
    expect([toneOf(0.5), toneOf(0), toneOf(-0.5)]).toEqual(["favourable", "mixed", "challenging"]);
  });
});
