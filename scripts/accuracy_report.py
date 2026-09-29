"""Regenerate docs/ACCURACY.md from the golden fixtures.

Runs the engine over every reference case and records maximum and median
differences per quantity. Uses only the product environment: it reads the numeric
fixtures and never imports the AGPL oracle tools.

    uv run python scripts/accuracy_report.py
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jyotish_engine import ENGINE_VERSION
from jyotish_engine.astro.ayanamsa import EPOCH_SYSTEMS, STAR_SYSTEMS, true_ayanamsa
from jyotish_engine.astro.bodies import EPHEMERIS_BODIES
from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.houses import HouseSystem, chart_angles, quadrant_cusps
from jyotish_engine.astro.positions import (
    angular_distance,
    mean_node_position,
    tropical_positions,
    true_node_position,
)
from jyotish_engine.astro.riseset import SunriseDefinition, next_sunrise, next_sunset
from jyotish_engine.astro.time import Instant

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "engine" / "tests" / "fixtures" / "astro_swisseph.json"
OUT = ROOT / "docs" / "ACCURACY.md"


def _row(name: str, values: list[float], unit: str, target: str) -> str:
    return (
        f"| {name} | {len(values)} | {max(values):.4f}{unit} | "
        f"{statistics.median(values):.4f}{unit} | {target} |"
    )


def main() -> None:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = data["cases"]
    errors: dict[str, list[float]] = defaultdict(list)

    for case in cases:
        instant = Instant(jd_ut=case["jd_ut"], jd_tt=case["jd_tt"])
        ref = case["positions_tropical"]
        for body, pos in tropical_positions(instant, EPHEMERIS_BODIES).items():
            errors[body.value].append(angular_distance(pos.longitude, ref[body.value][0]) * 3600)
        errors["mean_node"].append(
            angular_distance(mean_node_position(instant).longitude, ref["mean_node"][0]) * 3600
        )
        errors["true_node"].append(
            angular_distance(true_node_position(instant).longitude, ref["true_node"][0]) * 3600
        )
        for system in (*EPOCH_SYSTEMS, *STAR_SYSTEMS):
            key = system.value.replace("chitra", "citra")
            errors[f"ayanamsa:{system.value}"].append(
                abs(true_ayanamsa(instant, system) - case["ayanamsa_true"][key]) * 3600
            )
        angles = chart_angles(Instant.from_jd_ut(case["jd_ut"]), case["lat"], case["lon"])
        errors["ascendant"].append(
            angular_distance(angles.ascendant, case["houses"]["ascendant"]) * 3600
        )
        errors["midheaven"].append(angular_distance(angles.mc, case["houses"]["mc"]) * 3600)
        for name in ("placidus", "porphyry", "equal", "sripati"):
            reference = case["houses"][name]
            if not reference["ok"]:
                continue
            cusps = quadrant_cusps(HouseSystem(name), angles).cusps
            errors[f"houses:{name}"].append(
                max(angular_distance(a, b) for a, b in zip(cusps, reference["cusps"], strict=True))
                * 3600
            )
        if case["jd_ut"] <= 2460000.0:
            ours = Instant.from_jd_ut(case["jd_ut"]).delta_t_seconds
            errors["delta_t"].append(abs(ours - case["delta_t_s"]))

    for case in cases[::2]:
        if abs(case["lat"]) >= 60.0:
            continue
        start = Instant.from_jd_ut(case["jd_ut"] - 0.5)
        for definition in SunriseDefinition:
            args = (start, case["lat"], case["lon"], case["alt_m"], definition)
            for event, ours in (("rise", next_sunrise(*args)), ("set", next_sunset(*args))):
                theirs = case["sun_rise_set"][f"{definition.value}_{event}"]
                if ours is not None and theirs is not None:
                    errors[f"sun_{event}:{definition.value}"].append(
                        abs(ours.jd_ut - theirs) * 86400
                    )

    eph = get_ephemeris().info
    lines = [
        "# Accuracy report",
        "",
        f"*Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/accuracy_report.py`, engine "
        f"{ENGINE_VERSION}, ephemeris {eph.name}.* Reference: {data['reference']}; "
        f"{len(cases)} cases (1900–2050, latitudes −60° to +78°, seed {data['seed']}).",
        "",
        "The engine and the reference are given identical TT/UT1 instants, so these "
        "numbers measure the astronomy itself. Delta T is compared separately.",
        "",
        "## Positions (tropical, apparent, true equinox of date)",
        "",
        "| Quantity | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
    ]
    for body in EPHEMERIS_BODIES:
        lines.append(_row(body.value.title(), errors[body.value], '"', '≤ 1"'))
    lines.append(_row("Rahu (mean node)", errors["mean_node"], '"', '≤ 1"'))
    lines.append(_row("Rahu (true node)", errors["true_node"], '"', '≤ 5"'))
    lines += [
        "",
        "## Ayanamsa (true, including nutation)",
        "",
        "| System | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
    ]
    for system in (*EPOCH_SYSTEMS, *STAR_SYSTEMS):
        lines.append(_row(system.value, errors[f"ayanamsa:{system.value}"], '"', '≤ 0.5"'))
    lines += [
        "",
        "## Angles and houses (tropical)",
        "",
        "| Quantity | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
        _row("Ascendant", errors["ascendant"], '"', '≤ 2"'),
        _row("Midheaven", errors["midheaven"], '"', '≤ 2"'),
    ]
    for name in ("placidus", "porphyry", "equal", "sripati"):
        label = f"{name.title()} cusps (worst of 12)"
        lines.append(_row(label, errors[f"houses:{name}"], '"', '≤ 2"'))
    lines += [
        "",
        "Placidus is undefined inside the polar circles; there the engine falls back to "
        "Porphyry and flags it, as the reference does.",
        "",
        "## Sunrise and sunset (|latitude| < 60°)",
        "",
        "| Event | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
    ]
    for definition in SunriseDefinition:
        for event in ("rise", "set"):
            key = f"sun_{event}:{definition.value}"
            lines.append(_row(f"Sun{event} ({definition.value})", errors[key], " s", "≤ 2 s"))
    lines += [
        "",
        "Above about 60° the reference's own sunset times depend on where its search "
        "starts (one case at 62° N moved by 6 minutes); restarted near the event it "
        "agrees with the engine to 0.05 s.",
        "",
        "## Delta T (TT − UT1), dates up to 2023",
        "",
        "| Quantity | Cases | Max | Median | Note |",
        "|---|---|---|---|---|",
        _row("Delta T", errors["delta_t"], " s", "both follow IERS values"),
        "",
        "Future Delta T is a prediction in every tool; by 2050 models differ by seconds, "
        "which moves the Moon by about 0.5″ per second of difference.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
