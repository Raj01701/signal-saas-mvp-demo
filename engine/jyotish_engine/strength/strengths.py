"""All planetary and house strengths of a chart in one call."""

from __future__ import annotations

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.models import (
    AshtakavargaOut,
    BhavaBalaOut,
    ChartResult,
    ShadbalaOut,
    StrengthsOut,
)
from jyotish_engine.strength.ashtakavarga import SEVEN, ashtakavarga, pindas
from jyotish_engine.strength.bhava import bhava_bala, ishta_kashta
from jyotish_engine.strength.shadbala import REQUIRED_RUPAS, benefics, compute_shadbala
from jyotish_engine.strength.vimshopaka import VargaScheme, vimshopaka


def compute_strengths(chart: ChartResult) -> StrengthsOut:
    sidereal = {g.body: g.sidereal_longitude for g in chart.grahas if g.body in GRAHAS}
    signs = {b: int(lon // 30.0) % 12 for b, lon in sidereal.items()}
    shadbala = compute_shadbala(chart)

    shadbala_out = []
    for body in SEVEN:
        s = shadbala[body]
        ishta, kashta = ishta_kashta(body, s)
        shadbala_out.append(
            ShadbalaOut(
                body=body,
                uchcha=s.uchcha,
                saptavargaja=s.saptavargaja,
                ojayugma=s.ojayugma,
                kendradi=s.kendradi,
                drekkana=s.drekkana,
                sthana=s.sthana,
                dig=s.dig,
                nathonnata=s.nathonnata,
                paksha=s.paksha,
                tribhaga=s.tribhaga,
                abda=s.abda,
                masa=s.masa,
                vara=s.vara,
                hora=s.hora,
                ayana=s.ayana,
                yuddha=s.yuddha,
                kala=s.kala,
                cheshta=s.cheshta,
                naisargika=s.naisargika,
                drik=s.drik,
                total=s.total,
                rupas=s.rupas,
                required_rupas=REQUIRED_RUPAS[body],
                ratio=s.rupas / REQUIRED_RUPAS[body],
                ishta_phala=ishta,
                kashta_phala=kashta,
            )
        )

    houses = bhava_bala(
        chart.ascendant.sidereal_longitude,
        chart.midheaven.sidereal_longitude,
        sidereal,
        benefics(sidereal),
        shadbala,
    )

    av = ashtakavarga(chart.ascendant.sign, signs, chart.settings.ashtakavarga_moon)
    occupied = set(signs.values()) | {chart.ascendant.sign}
    reductions = {b.value: pindas(av.bav[b.value], signs, occupied) for b in SEVEN}

    return StrengthsOut(
        shadbala=shadbala_out,
        bhava_bala=[
            BhavaBalaOut(
                house=h.house,
                madhya=h.madhya,
                lord=h.lord,
                adhipati=h.adhipati,
                dig=h.dig,
                drishti=h.drishti,
                total=h.total,
                rupas=h.rupas,
            )
            for h in houses
        ],
        ashtakavarga=AshtakavargaOut(
            moon_table=chart.settings.ashtakavarga_moon.value,
            bav={name: list(values) for name, values in av.bav.items()},
            sav=list(av.sav),
            reduced={name: list(r.reduced) for name, r in reductions.items()},
            rasi_pinda={name: r.rasi_pinda for name, r in reductions.items()},
            graha_pinda={name: r.graha_pinda for name, r in reductions.items()},
            shodhya_pinda={name: r.shodhya_pinda for name, r in reductions.items()},
        ),
        vimshopaka={
            scheme.value: {b: v for b, v in vimshopaka(sidereal, scheme).items()}
            for scheme in VargaScheme
        },
    )


__all__ = ["Body", "compute_strengths"]
