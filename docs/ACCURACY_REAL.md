# Real-chart benchmark: do the timing rules find real events?

The engine's calculations are checked against reference software in `ACCURACY.md`. This document asks the other question: when the prediction timeline marks a time as active for marriage, children or career, did real events happen then more often than chance would give?

## The test

- **Charts:** 20 public figures born between 1913 and 1984 whose birth times Astro-Databank rates AA (17, from a birth record) or A (3, from family memory), as reported in web summaries of their entries. They are ten politicians, four royals, five film and music figures and a company founder, from the United States, the United Kingdom and India. Each chart was cast with the recorded UTC offset (war time, summer time and Indian Standard Time as they applied). Charts with disputed times (Amitabh Bachchan, Hillary Clinton, Princess Diana) were left out.
- **Events:** 158 widely published, dated events: 41 births of children, 31 marriages, 10 divorces, 27 promotions (inaugurations, accessions, major awards), 8 first jobs or elections, 8 job losses (lost elections, resignations), 4 businesses founded, 22 deaths of a parent, 3 of a spouse, 3 graduations and 1 move abroad.
- **Scoring:** the Accuracy Lab (`lab/backtest.py`). Each event is scored by the percentile of its month among the months its life area is read in (1 is the strongest month of a life, 0.5 is what a random month scores on average), and by whether one of the area's windows contains it.
- **Controls:** the same birth date and place at random times of day (8 per chart; the slow planets stay, while the Moon, lagna, dashas and houses change), and other people's events moved to the same ages.
- **Models:** `classic` (Vimshottari to the pratyantardasha, Yogini agreement, Jupiter and Saturn transits) and `full` (adding the divisional charts, Jaimini Chara dasha, KP house groups, Ashtakavarga-weighted transits and Saturn on the house lord), and each technique added to `classic` and removed from `full` on its own.

The cases are kept outside the repository; `scripts/accuracy_lab.py --cases <file> --model classic|full` runs the same test on any case file.

## Results

Mean event percentile (higher is better; 0.5 is chance) and window hit rate:

| Model | True charts | Random birth times | Swapped events | Hit rate (true / random) | p-value |
|---|---|---|---|---|---|
| classic | 0.461 | 0.486 | 0.510 | 0.22 / 0.24 | 0.89 |
| full | 0.463 | 0.493 | 0.503 | 0.20 / 0.23 | 1.00 |
| classic + divisional charts | 0.473 | 0.494 | 0.514 | 0.22 / 0.23 | 0.78 |
| classic + Chara dasha | 0.453 | 0.484 | 0.503 | 0.22 / 0.23 | 1.00 |
| classic + KP house groups | 0.456 | 0.486 | 0.507 | 0.20 / 0.24 | 1.00 |
| classic + Ashtakavarga | 0.464 | 0.487 | 0.506 | 0.22 / 0.24 | 0.89 |
| classic + Saturn on the lord | 0.459 | 0.487 | 0.509 | 0.20 / 0.25 | 0.89 |

By life area, full model (true charts against random birth times):

| Area | Events | True | Random | Difference |
|---|---|---|---|---|
| Career | 47 | 0.468 | 0.531 | −0.063 |
| Children | 41 | 0.499 | 0.481 | +0.018 |
| Marriage (with divorces and a spouse's death) | 44 | 0.357 | 0.477 | −0.119 |
| Parents | 22 | 0.594 | 0.455 | +0.139 |

Windows labelled strong contained an event of their area in 17 of 1,195 cases (1.4 %), moderate ones in 14 of 1,146 (1.2 %).

## What this means

- **No model found the real events better than chance.** The true charts ranked event months at about the 46th percentile, no better than the same days at random times. With 158 events the standard error of a mean percentile is about 0.023, so the differences between models, about 0.01, are well inside the noise: none of the added techniques measurably helped or hurt.
- **The per-area differences are what chance produces** when several areas are compared: marriage fell about two standard errors below the controls and parents' events about two above.
- **The confidence labels are not calibrated:** strong windows were no more likely than moderate ones to contain an event.
- This agrees with the published controlled tests of astrology (Carlson 1985; Dean and Kelly 2003; Narlikar and others 2009, where astrologers judged Indian charts at chance level).

## Limits

- Twenty charts are few. A real but small effect, of a few percentile points, could hide in this sample. Several hundred well-timed charts with dated events would be needed to see it.
- Public figures' lives are not typical, and dates of public events (an inauguration, an award) may not be the dates astrology would mark.
- Birth times rated A rest on family memory.

## What the product does about it

- Calculations stay exact and are checked against reference software; that part of accuracy is real and measured.
- Readings present timing as traditional indication, not forecast; the Kundli Check page says so beside every timeline, and its question answers say so when asked.
- The page asks people to mark past moments as happened or not, and the Accuracy Lab can use consented, recorded events to test again on many more lives. Weights are not tuned to this small sample, which would only fit its noise.
