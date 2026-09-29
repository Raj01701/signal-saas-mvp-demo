# Research: Building a World-Class Vedic Astrology (Jyotish) Platform

*Research compiled September 2026. Sources are listed at the end, and each claim below points back to them.*

This document answers four questions:

1. What does a complete Vedic analysis of a person require?
2. What limits accuracy, and what maximises it?
3. Which knowledge sources and data will the platform use?
4. Which engines and libraries fit a product whose shipped code must be permissively licensed?

The build plan that follows from it is in [`ROADMAP.md`](ROADMAP.md). The module layout is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 1. Summary

- **Calculations can be made essentially exact.**
  - NASA JPL's DE440 ephemeris, read through Skyfield (MIT licence), gives planet positions to well under 1″ (one arcsecond).
  - With the historical corrections listed here, dashas, divisional charts and panchanga follow deterministically from those positions and the birth time.
- **Real-world error comes from the birth data, not the maths.**
  - Wrong or rounded birth times move the ascendant and the divisional-chart ascendants.
  - Historical time zones are frequently wrong. India had Bombay Time until 1955, Calcutta Time until 1948, and War Time from 1942 to 1945.
  - The platform therefore captures how reliable the birth time is, flags fragile factors, and offers rectification.
- **Interpretive fidelity comes from citations.**
  - Each rule is paraphrased from a classical text and cites its source.
  - Where schools of astrology differ, the choice is exposed as a setting.
- **Predictive validity is not scientifically established.**
  - The platform does not claim guaranteed predictions.
  - It measures its own hit rates against control groups (the Accuracy Lab).
- **Licensing.**
  - Swiss Ephemeris and the Python projects built on it (pyswisseph, PyJHora, Kerykeion, libephemeris) are AGPL. They are used only as test oracles, never shipped.
  - The product ships Skyfield plus JPL ephemerides (public domain) and our own Jyotish code.

---

## 2. What "accuracy" means

### 2.1 Three layers

| Layer | Achievable? | How we get there |
|---|---|---|
| **Computation** (positions, ascendant, dashas, vargas, panchanga) | Yes, near-perfect | JPL DE440, correct ΔT and time zones, golden tests against independent implementations |
| **Fidelity to tradition** (what the classics say a configuration means) | Yes, rigorous | Rule base with citations (text, edition, chapter, verse); school-specific settings; review by a Jyotishi |
| **Predictive validity** (does it forecast real life?) | Not established | No guarantees; measured hit rates against shuffled-birth-time controls; honest reporting |

### 2.2 Scientific evidence to be aware of

Controlled tests have not found predictive power:

- **Carlson (1985), double-blind test in *Nature*:** a negative result. A later reanalysis by Ertel disputes the conclusion.
- **Dean and Kelly (2003), "time twins":** more than 2,000 people born in London in 1958 within minutes of each other showed no more similarity across over 100 variables than unrelated pairs.
- **Narlikar et al. (2009), *Current Science* 96:641:**
  - Design: 51 Vedic astrologers each received 40 randomised charts drawn from 100 bright and 100 mentally challenged children.
  - Result: they sorted them no better than chance.

**Consequence for the product:**
- It presents traditional interpretations, not promises.
- Any accuracy claim in marketing must be backed by data. The advertising regulator ASCI treats unsubstantiated "100% guaranteed" claims as misleading.

### 2.3 How birth-time error propagates

| Quantity | Rate of change | Birth-time error that changes it |
|---|---|---|
| Ascendant (D1 Lagna) | about 1° per 4 min on average (varies by sign) | about 2 h per sign |
| Navamsa (D9) Lagna | 3°20′ segments | about 13 min on average |
| Dashamsa (D10) Lagna | 3° segments | about 12 min |
| Shashtiamsa (D60) Lagna | 0°30′ segments | about 2 min |
| Moon | about 0.5′ per minute | shifts every Vimshottari date by about 1.5–5 days per minute of error (depends on the birth nakshatra's lord) |

This is why the platform records a rating for the birth data and runs a sensitivity analysis on every chart. The rating follows the Rodden scale (AA = from a birth certificate or record; A = from memory; B = biography; C = caution; DD = conflicting data).

---

## 3. What a complete Vedic analysis requires

### 3.1 Inputs

- **Birth details:**
  - Date, time and place (latitude, longitude, elevation).
  - Where the birth time came from and its uncertainty window.
  - Gender (used by some classical techniques).
- **Optional:** dated life events (marriage, children, career changes, relocation, deaths in the family, accidents, surgeries). These are used for rectification and for the Accuracy Lab.
- **Matchmaking:** two complete birth records.

### 3.2 Time and place

1. **Geocoding:** GeoNames (CC BY 4.0), with Hindi and regional alternate names. A map pin handles places that aren't in the gazetteer.
2. **Timezone lookup:** `timezonefinder` from coordinates, then the IANA timezone database.
3. **Historical overrides.** This step is essential.
   - The IANA database documents that its pre-1970 data "does not suffice for applications requiring accurate handling of all past times everywhere".
   - It creates a separate zone only when clocks differ after 1970.
   - So `Asia/Kolkata` covers all of India with a single history:
     - Local Mean Time until 1854.
     - Howrah Mean Time until 1870.
     - Madras time until 1906.
     - IST afterwards, plus two periods of war time.
   - It does not model:
     - Bombay Time (UTC+4:51), kept locally until 1955.
     - Calcutta Time (UTC+5:53:20), kept until 1948.
   - The platform keeps a curated, sourced overrides dataset. When a birth falls in an ambiguous window, it asks which standard the record used.
4. **Time scales:** UTC → TT via ΔT (historic ΔT from Stephenson, Morrison and Hohenkerk 2016, as built into Skyfield) → Julian Day. Julian calendar dates are handled for historical charts.
5. **Sunrise and sunset:** the definition must be configurable because tools differ.
   - Traditional Hindu sunrise uses the centre of the Sun's disc without refraction.
   - Drik Panchang defaults to the upper limb with refraction, and offers a "middle limb" option.

### 3.3 Astronomy

- **Planet positions:** apparent geocentric ecliptic longitude, latitude and speed for the Sun, Moon, Mars, Mercury, Jupiter, Venus and Saturn.
  - Uranus, Neptune and Pluto are optional because they are not classical.
  - A topocentric Moon is optional. Parallax can move it by up to about 1°.
- **Lunar nodes (Rahu and Ketu):** both mean and true (osculating), since tools disagree.
  - PyJHora defaults to true nodes.
  - Traditional panchangas used mean nodes.
  - The two differ by up to about ±1.5°.
- **Planetary states:** retrograde status, combustion, declination.
- **Ascendant and midheaven.**
- **House systems:**
  - Whole-sign (Parashari default).
  - Sripati bhava chalit.
  - Placidus (KP).
  - Equal and others.
- **Ayanamsa options:**
  - Lahiri (Chitrapaksha), defined by the Indian Calendar Reform Committee and the Government of India standard.
  - True Chitra (Spica fixed at 180°), True Revati and True Pushya (δ Cancri at 106°, the PyJHora default).
  - Raman (about 1.5° from Lahiri).
  - KP.
  - Yukteshwar and Fagan-Bradley.
  - A user-defined value.

### 3.4 Jyotish basics

- **Signs and nakshatras:** rashi, 27 nakshatras and 108 padas with their lords, and the 249 KP subdivisions (27 × 9 subs, plus splits at sign boundaries).
- **Divisional charts (vargas):**
  - The 16 Shodashavarga charts: D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60.
  - Plus D5, D6, D8, D11, D81, D108 and D144.
  - Variant schemes are selectable: Parivritti; Jagannatha and Somanatha drekkanas.
- **Dignity:**
  - Exaltation and debilitation, moolatrikona, own sign.
  - Natural, temporary and five-fold compound relationships (Panchadha Maitri).
  - Functional benefics and malefics per Laghu Parashari.
- **Planetary conditions:**
  - Avasthas: Baladi, Jagradadi, Deeptadi, Lajjitadi, Shayanadi.
  - Combustion distances, including the reduced orbs for retrograde planets.
  - Planetary war (graha yuddha).
  - Gandanta, Pushkara navamsa and bhaga, Mrityu bhaga, 64th navamsa and 22nd drekkana.
- **Special points:**
  - Upagrahas: Dhuma, Vyatipata, Parivesha, Indrachapa and Upaketu, which are Sun-based; Gulika, Mandi and the other time-based upagrahas.
  - Special lagnas: Hora, Ghati, Bhava, Vighati, Pranapada, Indu, Sree, Varnada.
  - Arudha padas A1–A12 and Upapada.
  - Chara karakas (7- and 8-karaka schemes).
  - Sahams (Tajika).

### 3.5 Strength

- **Shadbala:**
  - Sthana bala: uchcha, saptavargaja, ojhayugma, kendradi and drekkana components.
  - Dig bala.
  - Kala bala: nathonnatha, paksha, tribhaga, year, month, weekday and hora lords, ayana, yuddha.
  - Cheshta, Naisargika and Drik bala.
- **Other strength measures:** Bhava Bala, Ishta and Kashta phala, and Vimshopaka bala (6-, 7-, 10- and 16-varga schemes).
- **Ashtakavarga:**
  - Individual (BAV), combined (SAV) and prastara tables.
  - Trikona and Ekadhipatya reductions (shodhana) and Shodhya Pinda.
  - Kakshya subdivisions of 3°45′ for transit timing.

### 3.6 Yogas and doshas

- **Rule-driven catalogue:** 300 or more yogas from:
  - BPHS, Saravali, Phaladeepika and Jataka Parijata.
  - B.V. Raman's *Three Hundred Important Combinations*.
  - For comparison, PyJHora implements 284.
- **Cancellation:** each yoga carries its cancellation (bhanga) conditions.
- **Doshas:**
  - Manglik (Kuja) with its classical exceptions.
  - Pitru, Grahana and Guru-Chandala.
  - Kemadruma with its cancellations.
  - Sade Sati.
- **Provenance tags:** Kala Sarpa Yoga is widely used today but does not appear in BPHS. It is tagged "modern, non-classical".

### 3.7 Timing: how past, present and future are read

- **Vimshottari dasha** (120 years):
  - Five levels: Mahadasha, Antardasha, Pratyantardasha, Sookshma, Prana.
  - The starting balance comes from the Moon's exact position within its nakshatra.
  - Year length is a setting:
    - Sidereal year (365.2564 days, the PyJHora default) or Julian year (365.25 days). These differ by less than half a day over 60 years.
    - 360-day savana year. This shifts dates by about 10 months by age 60.
- **Other nakshatra dashas:**
  - Yogini.
  - Ashtottari, used only when its conditions apply.
  - Shodashottari, Dwadashottari, Panchottari, Shatabdika, Chaturashiti Sama, Dwisaptati Sama, Shashtihayani, Shattrimsha Sama.
  - Kalachakra.
- **Sign-based (Jaimini) dashas:**
  - Chara: K.N. Rao's method and the PVR/Rath variant.
  - Narayana, Sthira, Shoola, Niryana Shoola, Drig, Brahma, Mandooka, Trikona.
- **Transits (gochara):**
  - Positions counted from the Moon and from the Lagna.
  - Vedha obstruction points.
  - Ashtakavarga points and kakshya subdivisions.
  - Sade Sati, Kantaka Shani and Ashtama Shani.
  - Jupiter-plus-Saturn double transit (K.N. Rao).
  - Tara bala, Chandra bala, Moorthy nirnaya.
- **Annual charts:**
  - Varshaphal (Tajika) sidereal solar return:
    - Muntha, year lord.
    - The 16 Tajika yogas: Ithasala, Ishrafa, Nakta, Yamaya, Kamboola and others.
    - Sahams, Mudda dasha, Patyayini dasha.
  - Tithi Pravesha chart.

### 3.8 Other modules

- **Panchanga:**
  - Tithi, vara, nakshatra, yoga and karana with their end times.
  - Sunrise, sunset, moonrise and moonset.
  - Rahu Kalam, Yamaganda, Gulika Kalam, Choghadiya, hora, Abhijit and Brahma muhurta.
  - Amanta and Purnimanta months, adhika masa, samvatsara, ayana, ritu.
  - Festival calendar later.
- **Matchmaking:**
  - Ashtakoota scoring out of 36: Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot 7, Nadi 8, with the Nadi and Bhakoot cancellations.
  - South Indian Dashakoota (10 poruthams).
  - Manglik comparison, papasamya (balancing of malefic influences), D9 comparison, dasha sandhi.
- **KP (Krishnamurti Paddhati):**
  - Placidus cusps with KP ayanamsa.
  - Star, sub and sub-sub lords.
  - 4-level significators, ruling planets.
  - 1–249 number horary.
- **Prashna (horary) and Muhurta (electional):** later milestones.
- **Lal Kitab and Nadi techniques (for example Bhrigu Bindu):** optional, later.
- **Remedies:** traditional practices (mantra, dana, fasting, worship, gemstones with contraindications). They are presented as tradition, never as a cure or a guarantee (see §8).

### 3.9 Settings where schools differ

Every report displays the settings used, and presets reproduce trusted tools.

| Setting | Options | Default ("Classic Parashari" preset) |
|---|---|---|
| Ayanamsa | Lahiri, True Chitra, True Revati, True Pushya, Raman, KP (old and new), Yukteshwar, Fagan-Bradley, user-defined | Lahiri |
| Nodes | Mean, true (osculating) | True |
| Dasha year | Sidereal 365.2564, Julian 365.25, tropical 365.2422, savana 360 | Sidereal |
| Houses | Whole-sign, Sripati, Placidus, equal, Porphyry | Whole-sign (Sripati for bhava chalit) |
| Sunrise | Hindu (disc centre, no refraction), upper limb with refraction, disc centre with refraction | Hindu |
| Moon | Geocentric, topocentric | Geocentric |
| Varga variants | Parashara, Parivritti, Jagannatha, Somanatha | Parashara |

**Presets:**
- Classic Parashari.
- Drik-compatible (upper-limb sunrise).
- KP (KP ayanamsa, Placidus, sub-lords).
- PVR/JHora-style (True Pushya, true nodes, sidereal year).

---

## 4. Accuracy maximisers

1. **Birth-data quality capture.** Record where the time came from and its uncertainty, and confirm the time standard in ambiguous historical windows.
2. **Exact astronomy.** DE440 apparent positions (light-time, aberration, nutation), historical ΔT, and correct handling of calendars and time zones.
3. **Sensitivity analysis.** For every chart, compute how long each key factor stays unchanged: the Lagna, the D9, D10 and D60 lagnas, the Moon's pada and each planet near a boundary. Flag the fragile ones.
4. **Rectification workbench.**
   - Scores a grid of candidate times against dated events, using dasha, transit and divisional-chart links.
   - Uses Kunda (Lagna × 81), Pranapada and gender checks as soft priors.
   - Returns ranked candidates with their evidence.
5. **Multi-technique convergence.** A prediction is "strong" only when two independent timing systems agree, for example Vimshottari plus Chara or Narayana dasha, and a transit trigger confirms it.
6. **Past-event validation loop.** The user confirms or rejects past windows, which feeds rectification and personal weighting.
7. **Transparent, reproducible settings.** Presets, plus the engine version and settings hash stored with every result.
8. **Explainability.** Each statement lists the rules that fired, their citations and the chart facts they used.
9. **Accuracy Lab.** Backtest each rule and timing method against shuffled-birth-time controls, calibrate the weights, and publish honest numbers.
10. **Expert review.** Knowledge-base rules stay `draft` until a qualified Jyotishi reviews them.

---

## 5. Knowledge and data sources

### 5.1 Astronomical

| Source | Coverage | Licence | Use |
|---|---|---|---|
| NASA JPL DE440 | 1550–2650 (about 114 MB) | Public domain | Production ephemeris |
| NASA JPL DE441 | −13200 to +17191 (about 3 GB) | Public domain | Optional, for historical charts |
| NASA JPL DE421 (packaged as `skyfield-data`) | 1899-07-28 to 2053-10-08 | MIT package, public-domain data | Offline development fallback |
| Skyfield 1.55 and jplephem 2.24 | IAU 2000A nutation, IAU 2006 precession, ΔT, rise/set, root-finding | MIT | Core astronomy library |
| Astronomy Engine 2.1.19 | VSOP87 and its own lunar theory, about ±1′ | MIT | Independent sanity check |
| Hipparcos catalogue values (Spica, ζ Piscium, δ Cancri) | Star positions and proper motions | Free | "True" ayanamsas |
| Lahiri definition (Indian Calendar Reform Committee) and annual *Indian Astronomical Ephemeris* values | — | Facts | Implementing and validating ayanamsa |

### 5.2 Place and time

| Source | Licence | Use |
|---|---|---|
| GeoNames (`cities500` + alternate names; `geonamescache` package offline) | CC BY 4.0 | Place search; attribution required |
| timezonefinder 9.0 (+ timezonefinder-data) | MIT; boundary data ODbL 1.0 | Timezone from coordinates; attribution required |
| IANA tz database (`zoneinfo` + `tzdata`) | Public domain / Apache-2.0 | Civil time history |
| Curated historical overrides (`engine/jyotish_engine/place/overrides/`) | Ours | Bombay and Calcutta Time, war time, LMT; every entry sourced |

### 5.3 Classical texts: the interpretive knowledge base

**How we use them:**
- The Sanskrit originals are public domain.
- We paraphrase each rule in our own words and cite text, edition, chapter and verse. Editions number chapters differently, so the edition is always recorded.
- Copyrighted modern translations are consulted for meaning but never copied.

| Text | Author | Used for |
|---|---|---|
| Brihat Parashara Hora Shastra (BPHS) | attributed to Parashara | The foundation: houses, lords, yogas, dashas and their results, Shadbala, Ashtakavarga, special lagnas, arudhas |
| Laghu Parashari (Jataka Chandrika) | — | Functional benefics and malefics; dasha results |
| Brihat Jataka | Varahamihira | Planetary natures, yogas, longevity (pro view only) |
| Saravali | Kalyana Varma | Detailed planet-in-sign and house results, yogas |
| Phaladeepika | Mantreswara | Yogas, house analysis, transit results, dasha results |
| Jataka Parijata | Vaidyanatha Dikshita | Yogas, house results |
| Sarvartha Chintamani | Venkatesha | House-by-house analysis |
| Uttara Kalamrita | Kalidasa | Karakatwas (significations), house significations |
| Jaimini Upadesha Sutras | Jaimini | Chara karakas, arudhas, sign aspects, Chara, Narayana and other sign dashas |
| Tajika Neelakanthi | Neelakantha | Varshaphal: Tajika yogas, sahams, Muntha |
| Prashna Marga | — | Horary (later) |
| Muhurta Chintamani | Rama Daivagya | Electional astrology (later) |
| Surya Siddhanta | — | Traditional astronomy references (for example combustion orbs) |

Digital Sanskrit sources include sanskritdocuments.org and archive.org scans.

### 5.4 Modern method references (verification, not copying)

- **P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated Approach*:** a free PDF from the author, and the basis of PyJHora's roughly 6,800 tests.
- **B.V. Raman:**
  - *How to Judge a Horoscope*, Vols 1–2.
  - *Three Hundred Important Combinations*.
  - *Graha and Bhava Balas*, which has worked Shadbala examples.
- **K.N. Rao:** *Predicting through Jaimini's Chara Dasha*, and the double-transit method.
- **Sanjay Rath:** *Crux of Vedic Astrology*.
- **K.S. Krishnamurti:** *KP Readers* 1–6.

### 5.5 Empirical data (measuring accuracy)

- **Our own consented, dated life events.** This is opt-in research use and becomes the long-term differentiator.
- **VedAstro's 15,000 famous people dataset** (MIT, on Hugging Face):
  - Claims AA birth data with DST-corrected time zones.
  - Includes a companion marriage and divorce dataset.
  - Provenance must be verified before use.
- **AstroDatabank (Astrodienst):**
  - Rodden-rated records, freely browsable.
  - Using it for research requires a licence from Astrodienst.

### 5.6 Validation oracles (never shipped)

- **JPL Horizons:** the truth source for positions.
- **Swiss Ephemeris 2.10.03 via pyswisseph (AGPL):**
  - Used only in the isolated `oracle/` harness to emit numeric fixtures.
  - Its data files are fetched from the official GitHub repository.
- **PyJHora 4.8.7 (AGPL):**
  - About 6,800 tests checked against Jagannatha Hora 8.0 and PVR's book.
  - Used in the oracle harness only.
- **Jagannatha Hora 8.0:** Windows freeware, for manual spot checks.
- **Drik Panchang:** manual panchanga spot checks, using the same sunrise definition.
- **Commercial APIs (Prokerala, VedicAstroAPI, AstrologyAPI.com):** optional spot checks.

---

## 6. Engine and library evaluation

| Option | Licence | Verdict |
|---|---|---|
| **Swiss Ephemeris 2.10.03** (C, Astrodienst) | AGPL-3.0 **or** Professional Licence (CHF 700–750 one-time, unlimited) | Gold standard, but AGPL covers network use. Rejected for shipping by product decision; used as a test oracle only. |
| pyswisseph 2.10.3.2 | AGPL-3.0 | Test oracle only |
| sweph (Node) 2.10.3 | AGPL-3.0 (LGPL-3.0 with a professional licence) | Not used |
| PyJHora 4.8.7 | AGPL-3.0 | The richest open Jyotish implementation (22+ graha dashas, 22+ rasi dashas, D1–D300 vargas, 284 yogas, Shadbala, Ashtakavarga, Tajika, KP). Test oracle only. |
| libephemeris | AGPL-3.0-only (some pre-releases were wrongly labelled Apache-2.0) | Rejected |
| Kerykeion | AGPL-3.0 | Rejected |
| openephem | MIT; very early (26 commits) | Reference only; too immature to depend on |
| **Skyfield 1.55** + jplephem | MIT | **Chosen:** precise, vectorised, well maintained, reads DE440 and DE441 directly |
| Astronomy Engine 2.1.19 | MIT | Chosen as an independent ±1′ cross-check |
| VedAstro | MIT (C#/.NET) | Useful reference for encoding predictions as data, and for its datasets. Different stack, so not a dependency. |
| Maitreya 8 | GPL | Rejected |
| Jagannatha Hora 8.0 | Proprietary freeware (Windows) | Manual reference |

**What we build ourselves because of the licensing decision:**
- Ayanamsa family.
- House systems.
- Mean and true nodes.
- The whole Jyotish layer.

Each is validated numerically against the oracles. Only the output numbers are compared; no AGPL code is copied.

---

## 7. Prediction methodology

### 7.1 Promise × period × trigger

Each life domain maps to houses, karakas and a divisional chart:

| Domain | Houses | Karakas | Divisional chart |
|---|---|---|---|
| Career | 10, 6, 2, 11 | Sun, Saturn, Mercury | D10 |
| Marriage | 7, 2, 11 | Venus (Jupiter for a woman's chart, by tradition) | D9 |
| Children | 5 | Jupiter | D7 |
| Wealth | 2, 11 | Jupiter | D2 |
| Property and vehicles | 4 | Mars, Venus | D4 |
| Education | 4, 5 | Mercury, Jupiter | D24 |
| Parents | 4, 9 | Moon, Sun | D12 |
| Spiritual life | 5, 9, 12 | Jupiter, Ketu | D20 |
| Health (tendencies only) | 1, 6, 8 | Sun, Moon | D30 |
| Travel and foreign lands | 3, 9, 12 | Rahu, Moon | — |

The domain score at a given time is built in three stages:

1. **Promise (natal).**
   - House and lord strength: Bhava Bala, SAV points, dignity, Shadbala, Vimshopaka.
   - Yogas, and the condition of the domain's divisional chart.
2. **Period.**
   - How the lords of dasha levels 1–3 link to the domain's houses and lords.
   - Links counted: lordship, occupation, aspect, nakshatra lord and KP-style significators, in D1 and the domain varga.
3. **Trigger** (monthly).
   - Transits over the domain's houses and lords, counted from both the Lagna and the Moon.
   - Jupiter-plus-Saturn double transit.
   - Ashtakavarga points in the transited sign.

**Combining the stages:**
- Score = promise × period × trigger.
- A convergence bonus applies when a second timing system (Chara, Narayana or Yogini) agrees.
- Weights start from classical priority and are recalibrated in the Accuracy Lab.

**Output:**
- A timeline heat-map of past, present and future.
- The top windows for each domain, each with its evidence and a confidence label.

### 7.2 Rectification

1. **Input:**
   - Approximate time and an uncertainty window of up to ±2 h.
   - 4–10 dated events.
2. **Candidates:** a grid at 10–30 s steps. Only time-sensitive factors are recomputed, vectorised: lagnas, cusps, the Moon and dasha dates.
3. **Event score:** how the dasha lords link to the event's signifying houses and varga, plus the transit trigger. Scores are summed as log-likelihoods.
4. **Priors:** Kunda, Pranapada and gender checks act as soft priors.
5. **Output:** the top five candidates with probability shares, per-event evidence, and what differs between them.

---

## 8. Compliance, privacy and ethics

- **India's data protection law (DPDP Act 2023):**
  - The Rules were notified on 13 Nov 2025.
  - Consent-manager registration starts 13 Nov 2026.
  - All obligations apply from 13 May 2027, with penalties up to ₹250 crore.
  - Birth data is personal data, so the product needs explicit consent, export and deletion, encryption, minimal retention, and opt-in research use.
  - Users under 18 need verifiable parental consent. The platform models the account holder as the guardian of charts they create for children.
- **GDPR** applies to EU users.
- **Advertising and consumer rules:**
  - ASCI: no absolute or "guaranteed" claims; any accuracy claim needs data behind it.
  - Consumer Protection Authority (CCPA) Dark Patterns Guidelines 2023 (13 listed patterns): no false urgency, basket sneaking or confirm-shaming in remedy or consultation upsells.
  - Drugs and Magic Remedies Act 1954: its definition of a "magic remedy" includes talismans and mantras. Never claim that a remedy cures, diagnoses or prevents disease.
- **Sensitive predictions:**
  - Longevity and death timing (Ayurdaya, Maraka) appear only in the professional view behind an explicit toggle.
  - Health is framed as tendencies, with a pointer to a doctor.
- **Distribution:** Apple's App Store guideline 4.3 names fortune-telling apps as a saturated category, so the product launches as a web app and installable web app. Native apps come later with clear differentiation.
- **Attribution:** GeoNames (CC BY 4.0), timezone boundaries (ODbL), NASA JPL.

---

## 9. Market landscape

| Product | Position |
|---|---|
| Jagannatha Hora 8.0 | The most complete calculations; free; Windows-only desktop |
| AstroSage Kundli | Consumer leader; more than 70 million downloads |
| Astrotalk | Consultation marketplace; ₹1,214 crore revenue in FY25 (+85%); 1.5 million monthly transacting users |
| Drik Panchang | The reference for panchanga accuracy |
| Prokerala, VedicAstroAPI, AstrologyAPI.com | Vedic calculation APIs sold to developers |

**Positioning:** JHora-level depth with consumer-grade UX. Explainable predictions with classical citations. Birth-time sensitivity and rectification. Honest, measured accuracy.

---

## 10. Sources

**Ephemeris and libraries**
- [Swiss Ephemeris price list](https://www.astro.com/swisseph/swephprice_e.htm)
- [Swiss Ephemeris source code](https://github.com/aloistr/swisseph)
- [PyJHora](https://github.com/naturalstupid/PyJHora)
- [libephemeris](https://github.com/g-battaglia/libephemeris)
- [openephem](https://github.com/NoahChristian/openephem)
- [Skyfield](https://rhodesmill.org/skyfield/)
- [skyfield-data](https://pypi.org/project/skyfield-data/)
- [Astronomy Engine](https://github.com/cosinekitty/astronomy)
- [sweph Node bindings](https://github.com/timotejroiko/sweph)
- [VedAstro](https://github.com/VedAstro/VedAstro)

**Time and place**
- [IANA tz database](https://github.com/eggert/tz): `theory.html` for scope; the `asia` file for Asia/Kolkata
- [Time in India](https://en.wikipedia.org/wiki/Time_in_India)
- [Bombay Time](https://en.wikipedia.org/wiki/Bombay_Time)
- [Calcutta Time](https://en.wikipedia.org/wiki/Calcutta_Time)
- [GeoNames](https://www.geonames.org/about.html)
- [timezonefinder](https://github.com/jannikmi/timezonefinder)

**Jyotish conventions**
- [Drik Panchang: Hindu sunrise](https://www.drikpanchang.com/faq/faq-ans2.html)
- [Vimshottari year length](https://shyamasundaradasa.com/jyotish/resources/articles/how_long_year/how_long_year_1.html)
- [Mean vs true nodes](https://barbarapijan.com/bpa/Graha/Rahu/Rahu_Ketu_Mean_True.htm)
- [Kunda rectification](https://jyotish-blog.blogspot.com/2005/08/kunda-rectification.html?m=1)
- [Sanskrit jyotisha texts](https://sanskritdocuments.org/sanskrit/jyotisha/)
- [Brihat Parashara Hora Shastra](https://en.wikipedia.org/wiki/Brihat_Parashara_Hora_Shastra)

**Data**
- [VedAstro 15,000 famous people dataset](https://huggingface.co/datasets/vedastro-org/15000-Famous-People-Birth-Date-Location)
- [Astrodatabank](https://en.wikipedia.org/wiki/Astrodatabank)

**Scientific tests**
- [Carlson 1985, *Nature*](https://www.nature.com/articles/318419a0)
- [Dean and Kelly time twins](https://www.washingtontimes.com/news/2003/aug/17/20030817-105449-9384r/)
- [Narlikar et al. 2009 (summary)](https://skepticalinquirer.org/2022/05/indian-astrology-a-reality-check/)

**Law and platforms**
- [DPDP Rules 2025 (PIB)](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
- [DPDP phased rollout](https://www.azbpartners.com/bank/indias-digital-personal-data-protection-act-phased-rollout-and-key-compliance-milestones/)
- [ASCI on astrology apps](https://bestmediainfo.com/mediainfo/mediainfo-marketing/astrology-apps-on-the-rise-in-india-but-who-guarantees-their-credibility-10511514)
- [CCPA dark patterns](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2268302)
- [Drugs and Magic Remedies Act](https://en.wikipedia.org/wiki/Drugs_and_Magic_Remedies_(Objectionable_Advertisements)_Act,_1954)
- [Apple guideline 4.3](https://www.macrumors.com/2026/06/09/app-store-guidelines-low-quality-apps/)

**Market**
- [Astrotalk FY25](https://www.bwdisrupt.com/article/astrotalk-revenue-jumps-85-to-rs-1-214-cr-591016)
- [AstroSage 70M downloads](https://www.astrosage.com/magazine/astrosage-kundli-app-crosses-70-million-downloads.asp)
