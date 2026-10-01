"""Compare the engine's chart for one birth with reference values from
``oracle/reference_chart.py`` (Swiss Ephemeris and PyJHora).

    uv run python scripts/compare_with_reference.py 1987-10-09T17:35 29.53489 75.02898 \\
        /tmp/reference.json

Prints each planet's difference in arcseconds (Rahu against both the true and the mean
node), the ascendant's, the ayanamsa's and the birth nakshatra. A difference of a few
arcseconds in the ascendant is expected: the engine turns civil time into Earth-rotation
time (UT1), which most astrology software skips.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.settings import Settings


def arcsec(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0


def main(argv: list[str]) -> int:
    when, lat, lon = datetime.fromisoformat(argv[1]), float(argv[2]), float(argv[3])
    with open(argv[4], encoding="utf-8") as handle:
        lines = [line for line in handle if line.startswith("{")]
    ref = json.loads(lines[-1])
    place = PlaceInput(name="birth", latitude=lat, longitude=lon)
    chart = compute_chart(BirthInput(local_datetime=when, place=place), Settings())
    ours = {g.body.value: g.sidereal_longitude for g in chart.grahas}
    print(f'ayanamsa {arcsec(chart.ayanamsa.true, ref["ayanamsa"]):+8.3f}"')
    for name in ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"):
        print(f'{name:9s}{arcsec(ours[name], ref["positions"][name]):+8.3f}"')
    print(f'rahu     {arcsec(ours["rahu"], ref["positions"]["rahu_true"]):+8.3f}" (true node)')
    mean = Settings(node_type="mean")
    rahu_mean = next(
        g.sidereal_longitude
        for g in compute_chart(BirthInput(local_datetime=when, place=place), mean).grahas
        if g.body.value == "rahu"
    )
    print(f'rahu     {arcsec(rahu_mean, ref["positions"]["rahu_mean"]):+8.3f}" (mean node)')
    lagna = arcsec(chart.ascendant.sidereal_longitude, ref["positions"]["ascendant"])
    print(f'lagna    {lagna:+8.3f}"')
    moon = next(g for g in chart.grahas if g.body.value == "moon")
    print(
        f"nakshatra engine {moon.nakshatra.index + 1} pada {moon.nakshatra.pada}; "
        f"PyJHora {ref['panchanga']['nakshatra']} pada {ref['panchanga']['pada']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
