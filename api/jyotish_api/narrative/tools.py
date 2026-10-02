"""Chat lookup tools: the chart lookups a language model may call while it answers.

Each tool runs one ``ChartLookup`` method and returns the engine's result as JSON with
an ``evidence_id``; the same result becomes an evidence item the answer may cite. An
id the model cites without having called the tool is resolved by running the lookup
it names, so every cited id is checked against the engine.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from jyotish_api.narrative.evidence import EvidenceItem
from jyotish_engine.ask import ChartLookup
from jyotish_engine.astro.bodies import GRAHAS
from jyotish_engine.predict.domains import DOMAIN_SPECS

#: Ranges of periods and transits are limited to keep results small.
MAX_SPAN_DAYS = 30 * 366
#: Years asked about must fall within this many years of the birth.
MAX_AGE_YEARS = 110

DATE = {"type": "string", "format": "date", "description": "A date, YYYY-MM-DD."}
AREAS = [spec.domain.value for spec in DOMAIN_SPECS]


def _tool(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


LOOKUP_TOOLS: list[dict[str, Any]] = [
    _tool(
        "planet",
        "One graha in the birth chart: sign, house, nakshatra, dignity, the houses it rules "
        "and aspects, the planets with it, its sign in the divisional charts (D9 marriage, "
        "D10 career, D7 children ...), its chara karaka role and its Shadbala. Call it for "
        "any question about a planet.",
        {"name": {"type": "string", "enum": [b.value for b in GRAHAS]}},
    ),
    _tool(
        "house",
        "One house (bhava) counted from the lagna: its sign and meaning, its lord and where "
        "the lord sits, the planets in and aspecting it, its Ashtakavarga bindus and Bhava "
        "Bala. Call it for any question about a house or the matters it rules.",
        {"number": {"type": "integer", "enum": list(range(1, 13))}},
    ),
    _tool(
        "period_at",
        "On one date: the running Vimshottari mahadasha, antardasha and pratyantardasha, "
        "every graha's transit counted from the lagna and the Moon, and the dasha and "
        "transit rules that hold. Call it for any question about a particular date or month.",
        {"date": DATE},
    ),
    _tool(
        "periods",
        "The Vimshottari periods between two dates: pratyantardashas for ranges up to three "
        "years, antardashas for longer ones (at most 30 years). Call it to see how the "
        "periods unfold over a stretch of time.",
        {"start": DATE, "end": DATE},
    ),
    _tool(
        "transits",
        "Saturn, Jupiter, Rahu and Ketu between two dates (at most 30 years): each stay in a "
        "sign with its dates and its house from the Moon and the lagna, with Sade Sati and "
        "other notes. Call it for questions about the slow planets over time.",
        {"start": DATE, "end": DATE},
    ),
    _tool(
        "life_area",
        "A life area's natal promise (0 to 1; 0.5 is average) with its reasons, and every "
        "window across the life when the prediction timeline emphasises it, with dates, "
        "tone, agreement and reasons. Call it for 'when' questions about an area of life. "
        "Health returns tendencies only.",
        {"area": {"type": "string", "enum": AREAS}},
    ),
    _tool(
        "year",
        "One calendar year: the annual chart (Varshaphal: Muntha's house and the lord of the "
        "year), the antardashas and pratyantardashas, the slow transits and the windows of "
        "every life area. Call it for any question about a particular year.",
        {"year": {"type": "integer"}},
    ),
]


def _item(
    item_id: str, title: str, text: str, domains: list[str] | None = None, period: str = ""
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        kind="lookup",
        title=title,
        text=text,
        domains=domains or [],
        period=period or None,
    )


def _range(lookup: ChartLookup, args: dict[str, Any]) -> tuple[date, date]:
    start, end = date.fromisoformat(str(args["start"])), date.fromisoformat(str(args["end"]))
    if end <= start:
        raise ValueError("the end date must come after the start date")
    if (end - start).days > MAX_SPAN_DAYS:
        raise ValueError("ask for at most 30 years at a time")
    if end <= lookup.born:
        raise ValueError(f"the range must end after the birth on {lookup.born}")
    return start, end


def run_tool(
    lookup: ChartLookup, name: str, args: dict[str, Any]
) -> tuple[EvidenceItem, dict[str, Any]]:
    """Run one lookup: the evidence item and the JSON the model reads. Raises
    ``LookupError`` or ``ValueError`` for an unknown tool or an argument out of range."""
    if name == "planet":
        planet = lookup.planet(str(args["name"]))
        item = _item(f"planet:{planet.planet.lower()}", f"{planet.planet}", planet.summary())
        return item, {"evidence_id": item.id, **planet.model_dump(mode="json")}
    if name == "house":
        house = lookup.house(int(args["number"]))
        item = _item(f"house:{house.house}", f"House {house.house}", house.summary())
        return item, {"evidence_id": item.id, **house.model_dump(mode="json")}
    if name == "period_at":
        day = date.fromisoformat(str(args["date"]))
        if day < lookup.born or day > lookup.last:
            raise ValueError(f"dates run from the birth on {lookup.born} to {lookup.last}")
        moment = lookup.moment(day)
        item = _item(f"at:{day}", f"Periods on {day}", moment.summary(), period=str(day))
        return item, {"evidence_id": item.id, **moment.model_dump(mode="json")}
    if name == "periods":
        start, end = _range(lookup, args)
        rows = lookup.periods(start, end)
        text = "; ".join(p.summary() for p in rows)
        item = _item(
            f"periods:{start}:{end}", f"Periods {start} to {end}", text, period=f"{start} to {end}"
        )
        return item, {"evidence_id": item.id, "periods": [p.model_dump(mode="json") for p in rows]}
    if name == "transits":
        start, end = _range(lookup, args)
        stays = lookup.transits(start, end)
        text = "; ".join(t.summary() for t in stays) or "beyond the ephemeris"
        item = _item(
            f"transits:{start}:{end}",
            f"Slow transits {start} to {end}",
            text,
            period=f"{start} to {end}",
        )
        return item, {
            "evidence_id": item.id,
            "transits": [t.model_dump(mode="json") for t in stays],
        }
    if name == "life_area":
        area = lookup.area(str(args["area"]))
        item = _item(
            f"area:{area.area}", f"{area.area.title()} over the life", area.summary(), [area.area]
        )
        return item, {"evidence_id": item.id, **area.model_dump(mode="json")}
    if name == "year":
        year = int(args["year"])
        if not lookup.born.year <= year <= lookup.born.year + MAX_AGE_YEARS:
            raise ValueError(
                f"years run from {lookup.born.year} to {lookup.born.year + MAX_AGE_YEARS}"
            )
        facts = lookup.year(year)
        item = _item(
            f"year:{year}", f"The year {year}", facts.summary(), list(facts.windows), str(year)
        )
        return item, {"evidence_id": item.id, **facts.model_dump(mode="json")}
    raise LookupError(f"unknown tool {name!r}")


def resolve_id(lookup: ChartLookup, item_id: str) -> EvidenceItem | None:
    """The evidence item a lookup id names (``year:2027``, ``house:7`` ...), by running the
    lookup; ``None`` when the id names no lookup or the lookup fails."""
    kind, _, rest = item_id.partition(":")
    parts = rest.split(":")
    calls: dict[str, tuple[str, dict[str, Any]]] = {
        "planet": ("planet", {"name": rest}),
        "house": ("house", {"number": rest}),
        "at": ("period_at", {"date": rest}),
        "area": ("life_area", {"area": rest}),
        "year": ("year", {"year": rest}),
    }
    if kind in ("periods", "transits") and len(parts) == 2:
        calls[kind] = (kind, {"start": parts[0], "end": parts[1]})
    if kind not in calls or not rest:
        return None
    name, args = calls[kind]
    try:
        item, _ = run_tool(lookup, name, args)
    except (LookupError, ValueError, KeyError, TypeError):
        return None
    return item if item.id == item_id else None
