"""The evidence bundle: everything a narrative may say, each item with a stable ID.

The narrator (template or language model) receives only this bundle and must cite
the IDs of the items behind every paragraph; the server rejects any other ID. The
engine computes; the narrator only words the results.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel

from jyotish_engine.models import ChartResult, CitationOut, YogaOut
from jyotish_engine.predict import compute_predictions
from jyotish_engine.rules.periods import compute_period_readings
from jyotish_engine.rules.readings import compute_readings
from jyotish_engine.rules.yogas import compute_yogas

Kind = Literal["yoga", "reading", "promise", "window", "dasha", "transit", "lookup"]
STRENGTH_ORDER = {"major": 0, "moderate": 1, "minor": 2}
MAX_YOGAS = 25
WINDOWS_PER_DOMAIN = 3


class EvidenceItem(BaseModel):
    id: str
    kind: Kind
    title: str
    text: str
    domains: list[str] = []
    polarity: str | None = None
    #: For windows and periods: "2026-03 to 2026-09".
    period: str | None = None
    sources: list[str] = []


class EvidenceBundle(BaseModel):
    subject: str
    today: date
    items: list[EvidenceItem]

    def ids(self) -> set[str]:
        return {item.id for item in self.items}

    def get(self, item_id: str) -> EvidenceItem | None:
        return next((i for i in self.items if i.id == item_id), None)


def _cite(c: CitationOut) -> str:
    where = f" ch. {c.chapter}" if c.chapter is not None else ""
    return f"{c.text}{where}" + (f" ({c.locator})" if c.locator else "")


def _rule_item(rule: YogaOut, kind: Kind, prefix: str = "rule") -> EvidenceItem:
    return EvidenceItem(
        id=f"{prefix}:{rule.id}",
        kind=kind,
        title=rule.name,
        text=rule.summary,
        domains=[d.value for d in rule.domains],
        polarity=rule.polarity.value,
        sources=[_cite(c) for c in rule.sources],
    )


def build_bundle(
    chart: ChartResult,
    *,
    today: date | None = None,
    gender: str | None = None,
    include_sensitive: bool = False,
    horizon_years: int = 5,
) -> EvidenceBundle:
    """Evidence for a reading of ``chart`` as of ``today``: natal and for the coming years."""
    today = today or datetime.now(UTC).date()
    items: list[EvidenceItem] = []
    readings = compute_readings(chart, include_sensitive=include_sensitive).readings
    items += [_rule_item(r, "reading") for r in readings]
    yogas = compute_yogas(chart, gender=gender, include_sensitive=include_sensitive).present
    yogas = sorted(yogas, key=lambda y: STRENGTH_ORDER[y.strength.value])[:MAX_YOGAS]
    items += [_rule_item(y, "yoga") for y in yogas]

    start = date(today.year - 1, today.month, 1)
    end = date(today.year + horizon_years, today.month, 1)
    predictions = compute_predictions(chart, start, end, gender=gender)
    for domain in predictions.domains:
        name = domain.domain.value
        top = sorted(domain.promise.factors, key=lambda f: -abs(f.score) * f.weight)[:4]
        items.append(
            EvidenceItem(
                id=f"promise:{name}",
                kind="promise",
                title=f"Natal promise of {name}",
                text=f"Promise {domain.promise.score:.2f} (0.5 is neutral). "
                + "; ".join(f"{f.label} ({f.score:+.2f})" for f in top),
                domains=[name],
                polarity="positive"
                if domain.promise.score >= 0.55
                else "negative"
                if domain.promise.score <= 0.45
                else "mixed",
            )
        )
        upcoming = [w for w in domain.windows if w.end > today]
        for window in sorted(upcoming, key=lambda w: -w.score)[:WINDOWS_PER_DOMAIN]:
            tone = (
                "favourable"
                if window.tone > 0.15
                else "challenging"
                if window.tone < -0.15
                else "mixed"
            )
            lords = " / ".join(b.value.title() for b in window.dasha)
            reasons = "; ".join(f.label for f in window.factors[:4])
            items.append(
                EvidenceItem(
                    id=f"window:{name}:{window.start.isoformat()[:7]}",
                    kind="window",
                    title=f"{name.title()} window",
                    text=f"{window.confidence} emphasis, {tone}, during {lords}: {reasons}.",
                    domains=[name],
                    polarity=tone,
                    period=f"{window.start.isoformat()[:7]} to {window.end.isoformat()[:7]}",
                    sources=[r.id for r in window.rules],
                )
            )

    now = compute_period_readings(
        chart,
        datetime(today.year, today.month, today.day, 12, tzinfo=UTC),
        include_sensitive=include_sensitive,
    )
    levels = ("Mahadasha", "Antardasha", "Pratyantardasha")
    items.append(
        EvidenceItem(
            id="now:dasha",
            kind="dasha",
            title="Running periods",
            text="; ".join(
                f"{level} of {p.lords[-1].value.title()} until {p.end.date().isoformat()}"
                for level, p in zip(levels, now.dasha, strict=False)
            ),
            period=f"{now.dasha[-1].start.date()} to {now.dasha[-1].end.date()}",
        )
    )
    items += [_rule_item(r, "dasha", "now") for r in now.dasha_readings]
    items += [_rule_item(r, "transit", "now") for r in now.transit_readings]
    place = chart.birth.place.name or "the birth place"
    local = chart.time.local
    subject = f"Birth on {local.date()} at {local.strftime('%H:%M')} in {place}"
    return EvidenceBundle(subject=subject, today=today, items=items)
