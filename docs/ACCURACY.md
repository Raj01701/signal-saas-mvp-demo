# Accuracy report

*Generated 2026-09-30 by `scripts/accuracy_report.py`, engine 0.1.0, ephemeris DE421.* Reference: Swiss Ephemeris 2.10.03 (pyswisseph), files sepl_18/semo_18; 412 cases (1900–2050, latitudes −60° to +78°, seed 20260929).

The engine and the reference are given identical TT/UT1 instants, so these numbers measure the astronomy itself. Delta T is compared separately.

## Positions (tropical, apparent, true equinox of date)

| Quantity | Cases | Max | Median | Target |
|---|---|---|---|---|
| Sun | 412 | 0.0041" | 0.0009" | ≤ 1" |
| Moon | 412 | 0.0098" | 0.0024" | ≤ 1" |
| Mars | 412 | 0.0272" | 0.0009" | ≤ 1" |
| Mercury | 412 | 0.0047" | 0.0010" | ≤ 1" |
| Jupiter | 412 | 0.0025" | 0.0007" | ≤ 1" |
| Venus | 412 | 0.0052" | 0.0010" | ≤ 1" |
| Saturn | 412 | 0.0022" | 0.0005" | ≤ 1" |
| Uranus | 412 | 0.2969" | 0.1205" | ≤ 1" |
| Neptune | 412 | 0.1810" | 0.0303" | ≤ 1" |
| Pluto | 412 | 0.2630" | 0.0683" | ≤ 1" |
| Rahu (mean node) | 412 | 0.1084" | 0.0506" | ≤ 1" |
| Rahu (true node) | 412 | 0.0361" | 0.0041" | ≤ 5" |

## Ayanamsa (true, including nutation)

| System | Cases | Max | Median | Target |
|---|---|---|---|---|
| lahiri | 412 | 0.0023" | 0.0007" | ≤ 0.5" |
| lahiri_icrc | 412 | 0.0023" | 0.0007" | ≤ 0.5" |
| lahiri_1940 | 412 | 0.0027" | 0.0009" | ≤ 0.5" |
| lahiri_vp285 | 412 | 0.0165" | 0.0073" | ≤ 0.5" |
| raman | 412 | 0.0027" | 0.0009" | ≤ 0.5" |
| krishnamurti | 412 | 0.0027" | 0.0009" | ≤ 0.5" |
| krishnamurti_vp291 | 412 | 0.0163" | 0.0073" | ≤ 0.5" |
| yukteshwar | 412 | 0.0027" | 0.0009" | ≤ 0.5" |
| jn_bhasin | 412 | 0.0027" | 0.0009" | ≤ 0.5" |
| fagan_bradley | 412 | 0.0023" | 0.0007" | ≤ 0.5" |
| true_chitra | 412 | 0.0235" | 0.0099" | ≤ 0.5" |
| true_revati | 412 | 0.2867" | 0.1216" | ≤ 0.5" |
| true_pushya | 412 | 0.0309" | 0.0132" | ≤ 0.5" |

## Angles and houses (tropical)

| Quantity | Cases | Max | Median | Target |
|---|---|---|---|---|
| Ascendant | 412 | 0.0062" | 0.0004" | ≤ 2" |
| Midheaven | 412 | 0.0016" | 0.0004" | ≤ 2" |
| Placidus cusps (worst of 12) | 410 | 0.0062" | 0.0005" | ≤ 2" |
| Porphyry cusps (worst of 12) | 412 | 0.0062" | 0.0005" | ≤ 2" |
| Equal cusps (worst of 12) | 412 | 0.0062" | 0.0004" | ≤ 2" |
| Sripati cusps (worst of 12) | 412 | 0.0053" | 0.0004" | ≤ 2" |

Placidus is undefined inside the polar circles; there the engine falls back to Porphyry and flags it, as the reference does.

## Sunrise and sunset (|latitude| < 60°)

| Event | Cases | Max | Median | Target |
|---|---|---|---|---|
| Sunrise (hindu) | 193 | 0.1005 s | 0.0150 s | ≤ 2 s |
| Sunset (hindu) | 193 | 0.1160 s | 0.0161 s | ≤ 2 s |
| Sunrise (upper_limb_refraction) | 193 | 0.1186 s | 0.0023 s | ≤ 2 s |
| Sunset (upper_limb_refraction) | 193 | 0.0787 s | 0.0016 s | ≤ 2 s |
| Sunrise (disc_centre_refraction) | 193 | 0.0533 s | 0.0013 s | ≤ 2 s |
| Sunset (disc_centre_refraction) | 193 | 0.0318 s | 0.0010 s | ≤ 2 s |

Above about 60° the reference's own sunset times depend on where its search starts (one case at 62° N moved by 6 minutes); restarted near the event it agrees with the engine to 0.05 s.

## Delta T (TT − UT1), dates up to 2023

| Quantity | Cases | Max | Median | Note |
|---|---|---|---|---|
| Delta T | 339 | 0.6631 s | 0.0122 s | both follow IERS values |

Future Delta T is a prediction in every tool; by 2050 models differ by seconds, which moves the Moon by about 0.5″ per second of difference.

## Jyotish layer (M2) versus PyJHora 4.8.7

* Divisional charts: 80 of 80 reference tables (23 divisions with their Parashara, parivritti, Somanatha, Jagannatha, Raman and siddhamsa variants) match exactly, sign by sign and part by part; the unequal Trimsamsa (D30) and divisional longitudes also match.
* Chara karakas, compound (panchadha) relationships: exact on all 120 charts.
* Bhava arudhas: exact on every chart where PyJHora's convention of counting the Lagna as a planet does not apply.
* Bhava, Hora and Ghati lagnas within 0.12′; Indu lagna within 0.03′; Sree lagna within 1′ (it moves 27 times faster than the Moon).
* Sun-based upagrahas exact; time-based upagrahas within 1′ for day births where both part-lord conventions agree.

Reference deviations found and documented (the engine follows the classical texts):

* PyJHora's PyPI package ships no planetary data files, so Swiss Ephemeris falls back to the Moshier model (Moon off by up to ~3″, nodes by up to ~50″); fixtures are generated with the real files.
* It uses true (geometric) positions, about 20″ from the apparent positions most almanacs use; the engine offers both (`position_type`).
* It adds the timezone twice when taking the Sun at sunrise for special lagnas, counts a clock second as one tharparai in Pranapada, measures night upagraha parts from sunrise, and places the lordless eighth part after Saturn.

## Transit events (M3) versus Swiss Ephemeris

Reference: Swiss Ephemeris 2.10.03 (Lahiri, apparent, true node), sidereal sign ingresses 1995–2025 (the Moon 1995–1996) and planetary stations, each bisected to about 10 ms.

| Body | Ingresses (engine / reference) | Max | Median | Stations | Max | Median |
|---|---|---|---|---|---|---|
| Sun | 360 / 360 | 0.16 s | 0.02 s | — | — | — |
| Moon | 321 / 321 | 0.05 s | 0.02 s | — | — | — |
| Mars | 205 / 205 | 0.31 s | 0.02 s | 29 / 29 | 0.50 s | 0.18 s |
| Mercury | 441 / 441 | 0.17 s | 0.02 s | 190 / 190 | 0.20 s | 0.06 s |
| Jupiter | 42 / 42 | 0.54 s | 0.08 s | 55 / 55 | 0.77 s | 0.31 s |
| Venus | 383 / 383 | 0.17 s | 0.02 s | 36 / 36 | 0.44 s | 0.15 s |
| Saturn | 26 / 26 | 0.31 s | 0.09 s | 58 / 58 | 1.64 s | 0.55 s |
| Rahu | 19 / 19 | 13.41 s | 1.25 s | — | — | — |

Milestone target: ingress times within one minute. The true node's reversals are not reported as stations (Rahu and Ketu are treated as always retrograde).

## Nakshatra dashas (M3) versus PyJHora 4.8.7

40 charts; the engine is given PyJHora's Moon longitude and dasha year, so these numbers measure the dasha arithmetic itself.

| System | Periods compared | Lords matching | Max start difference |
|---|---|---|---|
| Vimshottari | 3240 | 3240 | 0.004 s |
| Ashtottari | 2560 | 2560 | 0.004 s |
| Yogini | 7680 | 7680 | 0.004 s |
| Shodashottari | 2560 | 2560 | 0.004 s |
| Dwadashottari | 2560 | 2560 | 0.004 s |
| Panchottari | 1960 | 1960 | 0.004 s |
| Shatabdika | 1960 | 1960 | 0.004 s |
| Chaturashiti Sama | 1960 | 1960 | 0.004 s |
| Dwisaptati Sama | 5120 | 5120 | 0.004 s |
| Shashtihayani | 5120 | 5120 | 0.004 s |
| Shattrimsha Sama | 7680 | 7680 | 0.004 s |

* Antardashas are divided the way PyJHora divides them: in proportion to the lords' years for Vimshottari and Ashtottari, equally for the rest. BPHS divides them proportionally in every system, which is the engine's default.
* True sidereal year (Mesha sankranti to Mesha sankranti): the engine is within 0.24 s of an exact Swiss Ephemeris bisection on every chart. PyJHora's own value is off by up to 168 s, because it interpolates each sankranti from sunrise samples, and on 1 chart(s) by 0.9 days (a wrong sankranti day); its dasha dates move accordingly.
* Applicability of the conditional dashas: 280 of 280 verdicts agree (7 systems; PyJHora has no rule for Shodashottari or Shattrimsha Sama).
* Yogini dasha follows BPHS's formula, (birth nakshatra + 3) mod 8; a cyclic count from Ardra gives different lords for births in Ashwini to Mrigashira.

## Jaimini sign dashas (M3) versus PyJHora 4.8.7

60 charts, identical positions. Chara dasha (K.N. Rao): mahadasha signs, lengths and dates match exactly on 51 charts. Narayana dasha (both rounds, mahadashas and antardashas): exact on 49 charts.

Every other chart differs only through one of these reference behaviours, which `test_sign_dasha_golden.py` detects chart by chart (the engine follows the rule as written):

* Mercury in Virgo is not treated as exalted (BPHS: exalted), so Gemini and Virgo dashas are a year shorter;
* the lagna is counted as a planet when choosing between co-lords;
* in the stronger-sign test (rule 2), Jupiter or Mercury is counted twice when it also rules the sign, and a lord in its own sign is missed;
* when the co-lord rules tie, the co-lord whose own sign has the longer dasha wins, rather than the one that gives the sign in question the longer dasha.

PyJHora also gives every Chara mahadasha the same antardasha order, starting from the lagna; the engine uses K.N. Rao's order (from the sign after the dasha sign, ending with the dasha sign), so Chara antardashas are not compared.
