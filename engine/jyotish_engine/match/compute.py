"""Match two charts: Ashtakoota, the ten South Indian kutas, Kuja dosha and papasamya.

Kuja dosha comes from the knowledge base (``dosha.kuja_*`` rules, from the lagna,
the Moon and Venus, with their exceptions). A partner is manglik when any of the
three is present and not cancelled. By the usual rule, the dosha is balanced when
both partners are manglik or neither is.
"""

from __future__ import annotations

from jyotish_engine.astro.bodies import Body
from jyotish_engine.match.ashtakoota import MoonPlacement, ashtakoota
from jyotish_engine.match.compatibility import papasamya
from jyotish_engine.match.dashakoota import dashakoota
from jyotish_engine.match.tables import KootaProfile
from jyotish_engine.models import (
    ChartResult,
    CitationOut,
    KootaOut,
    KujaOut,
    MatchDoshaOut,
    MatchOut,
    PoruthamOut,
)
from jyotish_engine.rules.catalogue import Catalogue, default_catalogue
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import Citation

KUJA_RULES = ("dosha.kuja_lagna", "dosha.kuja_moon", "dosha.kuja_venus")


def _citations(sources: tuple[Citation, ...]) -> list[CitationOut]:
    return [
        CitationOut(
            text=c.text,
            edition=c.edition,
            chapter=c.chapter,
            verses=c.verses,
            locator=c.locator,
            verified=c.verified,
        )
        for c in sources
    ]


def kuja_status(facts: ChartFacts, catalogue: Catalogue | None = None) -> KujaOut:
    rules = catalogue or default_catalogue()
    results = [rules.evaluate_rule(rules[rule_id], facts) for rule_id in KUJA_RULES]
    return KujaOut(
        manglik=any(r.present for r in results),
        present=[r.rule.id for r in results if r.present],
        cancelled=[r.rule.id for r in results if r.cancelled],
    )


def moon_of(chart: ChartResult) -> MoonPlacement:
    moon = next(g for g in chart.grahas if g.body is Body.MOON)
    return MoonPlacement(moon.sidereal_longitude)


def match_moons(
    groom: MoonPlacement, bride: MoonPlacement, profile: KootaProfile = KootaProfile.POPULAR
) -> tuple[list[KootaOut], list[MatchDoshaOut], list[PoruthamOut]]:
    kootas = ashtakoota(groom, bride, profile)
    return (
        [
            KootaOut(
                name=k.name,
                points=k.points,
                maximum=k.maximum,
                groom=k.groom,
                bride=k.bride,
                detail=k.detail,
                sources=_citations(k.sources),
            )
            for k in kootas.kootas
        ],
        [
            MatchDoshaOut(
                name=d.name,
                present=d.present,
                cancelled=d.cancelled,
                exceptions=list(d.exceptions),
                sources=_citations(d.sources),
            )
            for d in kootas.doshas
        ],
        [
            PoruthamOut(name=p.name, agrees=p.agrees, detail=p.detail, relieved_by=p.relieved_by)
            for p in dashakoota(groom, bride)
        ],
    )


def compute_match(
    groom: ChartResult, bride: ChartResult, profile: KootaProfile = KootaProfile.POPULAR
) -> MatchOut:
    kootas, doshas, poruthams = match_moons(moon_of(groom), moon_of(bride), profile)
    groom_kuja = kuja_status(ChartFacts.from_chart(groom, gender="male"))
    bride_kuja = kuja_status(ChartFacts.from_chart(bride, gender="female"))
    groom_papa, bride_papa = papasamya(groom), papasamya(bride)
    return MatchOut(
        profile=profile.value,
        ashtakoota=kootas,
        ashtakoota_total=sum(k.points for k in kootas),
        doshas=doshas,
        dashakoota=poruthams,
        dashakoota_agreements=sum(p.agrees for p in poruthams),
        groom_kuja=groom_kuja,
        bride_kuja=bride_kuja,
        kuja_balanced=groom_kuja.manglik == bride_kuja.manglik,
        groom_papa=groom_papa,
        bride_papa=bride_papa,
        papasamya_balanced=bride_papa.points <= groom_papa.points,
        sources=_citations(
            (
                Citation(text="raman_muhurtha", locator="Kuja dosha in marriage"),
                Citation(text="popular_practice", locator="Papasamya"),
            )
        ),
    )
