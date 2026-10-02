"""Top-level entry point: birth data in, fully described chart out.

``compute_chart`` resolves the birth time, computes positions and angles, then
derives everything classical Jyotish needs from them: nakshatras, KP lords,
dignities and states, all divisional charts, chara karakas, arudhas, special lagnas,
upagrahas, planetary wars, the Vimshottari dasha table and which conditional
dashas apply. Every result carries the engine version and a hash of the settings
used.
"""

from __future__ import annotations

from jyotish_engine import ENGINE_VERSION
from jyotish_engine.astro.ayanamsa import label as ayanamsa_label
from jyotish_engine.astro.ayanamsa import mean_ayanamsa, true_ayanamsa
from jyotish_engine.astro.bodies import GRAHAS, OUTER_PLANETS, Body
from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.houses import chart_angles, quadrant_cusps
from jyotish_engine.astro.positions import EclipticPosition, tropical_positions
from jyotish_engine.astro.time import Instant
from jyotish_engine.astro.vedic_day import VedicDay, vedic_day
from jyotish_engine.core.dignity import DIGNITY_RULES, dignity
from jyotish_engine.core.states import (
    baladi_avastha,
    is_combust,
    is_gandanta,
    jagradadi_avastha,
    planetary_wars,
)
from jyotish_engine.core.varga import VARGAS, varga_longitude
from jyotish_engine.core.zodiac import Sign
from jyotish_engine.dasha.conditions import applicability
from jyotish_engine.dasha.nakshatra import NakshatraDasha
from jyotish_engine.dasha.tables import nakshatra_dasha_table
from jyotish_engine.dasha.years import dasha_year_days
from jyotish_engine.models import (
    RODDEN_RATING,
    AyanamsaOut,
    BirthInput,
    ChartResult,
    DashaApplicabilityOut,
    DashasOut,
    DayOut,
    EphemerisOut,
    GrahaOut,
    HousesOut,
    PlaceInput,
    PlanetaryWarOut,
    PointOut,
    SpecialPointsOut,
    TimeInterpretationOut,
    TimeOut,
    VargaChartOut,
    VargaPlacement,
)
from jyotish_engine.place.timezone import TimeStandard, resolve_local_time
from jyotish_engine.settings import Settings
from jyotish_engine.special import lagnas
from jyotish_engine.special.arudha import bhava_arudhas
from jyotish_engine.special.karakas import chara_karakas
from jyotish_engine.special.upagraha import (
    PVR_BOOK_POSITIONS,
    sun_based_upagrahas,
    time_based_upagrahas,
)

# Re-exported for callers that import models from here.
__all__ = ["BirthInput", "ChartResult", "compute_chart", "compute_chart_at"]


def _sidereal_ascendant(
    instant: Instant, latitude: float, longitude: float, settings: Settings
) -> float:
    ayan = true_ayanamsa(instant, settings.ayanamsa, settings.user_ayanamsa_j2000)
    return (chart_angles(instant, latitude, longitude).ascendant - ayan) % 360.0


def _grahas(
    positions: dict[Body, EclipticPosition],
    bodies: list[Body],
    ayan_true: float,
    ascendant_sign: int,
) -> list[GrahaOut]:
    sidereal = {b: (p.longitude - ayan_true) % 360.0 for b, p in positions.items()}
    signs = {b: int(sidereal[b] // 30.0) for b in bodies}
    sun = sidereal[Body.SUN]
    out = []
    for body in bodies:
        pos = positions[body]
        point = PointOut.of(pos.longitude, ayan_true)
        classical = body in DIGNITY_RULES
        graha_dignity = (
            dignity(body, point.sign, point.degrees_in_sign, signs) if classical else None
        )
        is_node = body in (Body.RAHU, Body.KETU)
        out.append(
            GrahaOut(
                **point.model_dump(),
                body=body,
                latitude=pos.latitude,
                speed=pos.speed,
                retrograde=True if is_node else pos.retrograde,
                distance_au=pos.distance_au,
                house=(signs[body] - ascendant_sign) % 12 + 1,
                dignity=graha_dignity,
                combust=is_combust(body, sidereal[body], sun, pos.retrograde),
                baladi_avastha=baladi_avastha(sidereal[body]),
                jagradadi_avastha=(
                    jagradadi_avastha(graha_dignity) if graha_dignity is not None else None
                ),
                gandanta=is_gandanta(sidereal[body]),
            )
        )
    return out


def _vargas(
    sidereal: dict[Body, float], ascendant: float, settings: Settings
) -> list[VargaChartOut]:
    charts = []
    for division, spec in VARGAS.items():
        method = settings.varga_method(division)

        def place(longitude: float, division: int = division) -> VargaPlacement:
            value = varga_longitude(longitude, division, settings.varga_method(division))
            return VargaPlacement(sign=Sign(int(value // 30.0)), longitude=value)

        charts.append(
            VargaChartOut(
                division=division,
                name=spec.name,
                method=method,
                ascendant=place(ascendant),
                grahas={body: place(lon) for body, lon in sidereal.items()},
            )
        )
    return charts


def _special(
    instant: Instant,
    day: VedicDay | None,
    birth: BirthInput,
    settings: Settings,
    sidereal: dict[Body, float],
    latitudes: dict[Body, float],
    ascendant: float,
    ayan_true: float,
) -> SpecialPointsOut:
    place = birth.place
    time_lagnas: dict[str, PointOut | None] = dict.fromkeys(
        ("bhava_lagna", "hora_lagna", "ghati_lagna", "pranapada")
    )
    upagrahas = {
        u: PointOut.from_sidereal(v, ayan_true)
        for u, v in sun_based_upagrahas(sidereal[Body.SUN]).items()
    }
    if day is not None:
        sun_rise = tropical_positions(
            day.sunrise, [Body.SUN], settings.node_type, settings.position_type
        )[Body.SUN]
        ayan_rise = true_ayanamsa(day.sunrise, settings.ayanamsa, settings.user_ayanamsa_j2000)
        sun_at_sunrise = (sun_rise.longitude - ayan_rise) % 360.0
        minutes = day.minutes_since_sunrise(instant)
        time_lagnas = {
            "bhava_lagna": PointOut.from_sidereal(
                lagnas.bhava_lagna(sun_at_sunrise, minutes), ayan_true
            ),
            "hora_lagna": PointOut.from_sidereal(
                lagnas.hora_lagna(sun_at_sunrise, minutes), ayan_true
            ),
            "ghati_lagna": PointOut.from_sidereal(
                lagnas.ghati_lagna(sun_at_sunrise, minutes), ayan_true
            ),
            "pranapada": PointOut.from_sidereal(
                lagnas.pranapada(sidereal[Body.SUN], minutes), ayan_true
            ),
        }

        def ascendant_at(jd_ut: float) -> float:
            return _sidereal_ascendant(
                Instant.from_jd_ut(jd_ut), place.latitude, place.longitude, settings
            )

        positions = PVR_BOOK_POSITIONS if settings.gulika_convention == "pvr_book" else None
        for u, v in time_based_upagrahas(
            day.frame(), instant.jd_ut, ascendant_at, positions
        ).items():
            upagrahas[u] = PointOut.from_sidereal(v, ayan_true)

    wars = planetary_wars(sidereal, latitudes)
    return SpecialPointsOut(
        **time_lagnas,
        indu_lagna=PointOut.from_sidereal(
            lagnas.indu_lagna(ascendant, sidereal[Body.MOON]), ayan_true
        ),
        sree_lagna=PointOut.from_sidereal(
            lagnas.sree_lagna(ascendant, sidereal[Body.MOON]), ayan_true
        ),
        upagrahas=upagrahas,
        arudhas=[Sign(s) for s in bhava_arudhas(int(ascendant // 30.0), sidereal)],
        karakas=chara_karakas(sidereal, include_rahu=settings.karaka_scheme == 8),
        planetary_wars=[
            PlanetaryWarOut(
                planets=list(w.planets), separation_deg=w.separation_deg, winner=w.winner
            )
            for w in wars
        ],
    )


def _dashas(
    instant: Instant,
    settings: Settings,
    sidereal: dict[Body, float],
    ascendant: float,
    born_during_day: bool | None,
) -> DashasOut:
    year_days = dasha_year_days(settings, instant.jd_ut)
    return DashasOut(
        year=settings.dasha_year,
        year_days=year_days,
        vimshottari=nakshatra_dasha_table(
            NakshatraDasha.VIMSHOTTARI, instant.jd_ut, sidereal[Body.MOON], year_days
        ),
        applicability=[
            DashaApplicabilityOut(system=a.system.value, applicable=a.applicable, rule=a.rule)
            for a in applicability(ascendant, sidereal, born_during_day)
        ],
    )


def compute_chart(birth: BirthInput, settings: Settings | None = None) -> ChartResult:
    """Compute a complete sidereal chart for a birth record."""
    settings = settings or Settings()
    place = birth.place
    resolution = resolve_local_time(
        birth.local_datetime.replace(tzinfo=None),
        place.latitude,
        place.longitude,
        standard=birth.time_standard,
        utc_offset_seconds=birth.utc_offset_seconds,
        zone=birth.zone,
    )
    instant = Instant.from_utc(resolution.chosen.utc)
    eph = get_ephemeris()
    eph.check_range(instant.jd_tt)

    ayan_true = true_ayanamsa(instant, settings.ayanamsa, settings.user_ayanamsa_j2000)
    ayan_mean = mean_ayanamsa(instant, settings.ayanamsa, settings.user_ayanamsa_j2000)

    bodies = list(GRAHAS) + (list(OUTER_PLANETS) if settings.include_outer_planets else [])
    positions = tropical_positions(instant, bodies, settings.node_type, settings.position_type)
    classical = {b: positions[b] for b in GRAHAS}
    sidereal = {b: (p.longitude - ayan_true) % 360.0 for b, p in classical.items()}

    angles = chart_angles(instant, place.latitude, place.longitude)
    ascendant = PointOut.of(angles.ascendant, ayan_true)
    cusps = quadrant_cusps(settings.bhava_system, angles)
    day = vedic_day(instant, place.latitude, place.longitude, place.elevation_m, settings.sunrise)
    born_during_day = day.is_day(instant) if day else None

    return ChartResult(
        engine_version=ENGINE_VERSION,
        ephemeris=EphemerisOut(
            name=eph.info.name, jd_start=eph.info.jd_start, jd_end=eph.info.jd_end
        ),
        settings=settings,
        settings_hash=settings.fingerprint(),
        birth=birth,
        rodden_rating=RODDEN_RATING[birth.time_source],
        time=TimeOut(
            local=resolution.local,
            zone=resolution.zone,
            interpretation=TimeInterpretationOut.of(resolution.chosen),
            alternatives=[TimeInterpretationOut.of(a) for a in resolution.alternatives],
            ambiguous=resolution.ambiguous,
            confidence=resolution.confidence,
            warnings=list(resolution.warnings),
            jd_ut=instant.jd_ut,
            jd_tt=instant.jd_tt,
            delta_t_seconds=instant.delta_t_seconds,
        ),
        ayanamsa=AyanamsaOut(
            system=settings.ayanamsa.value,
            label=ayanamsa_label(settings.ayanamsa),
            mean=ayan_mean,
            true=ayan_true,
        ),
        ascendant=ascendant,
        midheaven=PointOut.of(angles.mc, ayan_true),
        grahas=_grahas(positions, bodies, ayan_true, ascendant.sign),
        houses=HousesOut(
            system=cusps.system,
            fallback=cusps.fallback,
            cusps=[(c - ayan_true) % 360.0 for c in cusps.cusps],
            whole_sign=[Sign((ascendant.sign + i) % 12) for i in range(12)],
        ),
        vargas=_vargas(sidereal, ascendant.sidereal_longitude, settings),
        special=_special(
            instant,
            day,
            birth,
            settings,
            sidereal,
            {b: p.latitude for b, p in classical.items()},
            ascendant.sidereal_longitude,
            ayan_true,
        ),
        day=DayOut(
            sunrise=day.sunrise.utc_datetime() if day else None,
            sunset=day.sunset.utc_datetime() if day else None,
            next_sunrise=day.next_sunrise.utc_datetime() if day else None,
            weekday=day.weekday if day else None,
            born_during_day=born_during_day,
        ),
        dashas=_dashas(instant, settings, sidereal, ascendant.sidereal_longitude, born_during_day),
    )


def compute_chart_at(
    jd_ut: float, place: PlaceInput, settings: Settings | None = None
) -> ChartResult:
    """Chart for an exact moment (UT Julian day), such as an annual return."""
    moment = Instant.from_jd_ut(jd_ut).utc_datetime()
    birth = BirthInput(
        local_datetime=moment.replace(tzinfo=None),
        place=place,
        time_standard=TimeStandard.FIXED_OFFSET,
        utc_offset_seconds=0.0,
    )
    return compute_chart(birth, settings)
