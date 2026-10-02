# Marriage matching (Guna Milan): tables, evidence and checks

This page explains how the engine scores Ashtakoota (Guna Milan, 36 points):

- where the published tables disagree, and which reading the engine uses;
- how precise a score is when the birth time is uncertain;
- how to check the engine against any matchmaking app.

The code is in `engine/jyotish_engine/match/`: `tables.py` holds the tables and their citations, `ashtakoota.py` the scoring, and `compute.py` the match of two charts.

## What the engine computes

Every koota reads only the two Moons:

- the Moon's sign (Varna, Vashya, Graha Maitri, Bhakoot);
- its nakshatra (Tara, Yoni, Gana, Nadi);
- for Vashya in Dhanu and Makara, which half of the sign it is in.

| Koota | Points | Reads | Rule |
|---|---|---|---|
| Varna | 1 | Moon sign | 1 when the groom's varna equals or ranks above the bride's |
| Vashya | 2 | Moon sign; Dhanu and Makara split at 15° | Points table by the two groups |
| Tara (Dina) | 3 | Nakshatras | 1.5 for each direction whose count (inclusive) leaves a remainder other than 3, 5 or 7 on dividing by 9 |
| Yoni | 4 | Nakshatras | Points table by the two animals |
| Graha Maitri | 5 | Lords of the Moon signs | 5-4-3-1-0.5-0 by the lords' natural relationship each way |
| Gana | 6 | Nakshatras | Points table by the two ganas |
| Bhakoot | 7 | Moon signs | 0 when the signs are 2/12, 5/9 or 6/8 from each other; otherwise 7 |
| Nadi | 8 | Nakshatras | 0 when both have the same nadi; otherwise 8 |

**Doshas and exceptions.** The total is the plain sum of the eight kootas. Doshas and their traditional exceptions are reported beside the total and never change it:

- **Nadi dosha** is cancelled by any of these:
  - same Moon sign but different nakshatras;
  - same nakshatra but different signs;
  - same nakshatra and sign but different padas;
  - different signs whose lords are the same planet or mutual friends.
- **Bhakoot dosha** is cancelled when the two Moon-sign lords are the same planet or mutual friends.
- **Gana dosha** (one partner Rakshasa, the other not) is relieved when the bride's nakshatra is beyond the 14th from the groom's.

The match also gives:

- Mangal (Kuja) dosha from the lagna, the Moon and Venus;
- papasamya;
- the ten South Indian poruthams (Dashakoota);
- the checks beyond the 36 points described in `RESEARCH.md` §7.4.

## Where the tables disagree, and what the engine uses

The groups agree across every source consulted: which varna, vashya, yoni, gana and nadi belongs to each sign or nakshatra. The points tables do not.

The engine keeps each disputed table as a named variant. A **profile** picks one variant of each table:

- **`popular`** is the default. It follows the tables Indian matchmaking guides and apps print.
- **`maitreya`** reproduces the Maitreya program's tables, as documented on its companion site Saravali.

The API takes the profile as `profile` on `/v1/match`. Every match also reports its total under the other profile, with each koota that differs.

Two-dimensional tables are read with **the bride down the rows and the groom across the columns**, as Saravali and Astroyogi print them.

| Koota | `popular` (default) | `maitreya` | Evidence |
|---|---|---|---|
| Varna | Fire Kshatriya, earth Vaishya, air Shudra, water Brahmin | Air Vaishya, earth Shudra | Guides vary; PyJHora follows Maitreya |
| Vashya | Astroyogi's table (below) | Saravali's table | Astroyogi prints its table with "Bride" down the rows; PyJHora carries the same table, marked "From astroyogi.com", and reads it bride first |
| Tara | Remainders 3, 5 and 7 inauspicious | Same | Agreed |
| Yoni | Saravali's table as published (shared) | Same | PyJHora uses the same table with its two lopsided cells made symmetric (both 1) |
| Graha Maitri | 5, 4, 3, 1, ½, 0 | 5, 4, 3, 2, 1, 0 | Two scales in use |
| Gana | Saravali's table (below, shared) | Same | Saravali ("Bride ↓") and Astroyogi ("Gana of Bride") print it with the bride down the rows; ClickAstro gives a Deva boy with a Manav girl 5; PyJHora transposed its table in version 3.1.1 to read it this way |
| Bhakoot | 2/12, 5/9 and 6/8 score 0 | Same | Agreed |
| Nadi | Same nadi scores 0 | Same | Agreed |

### Gana, the cell that matters most

| Bride ↓ · Groom → | Deva | Manushya | Rakshasa |
|---|---|---|---|
| **Deva** | 6 | 6 | 0 |
| **Manushya** | 5 | 6 | 0 |
| **Rakshasa** | 1 | 0 | 6 |

So a Deva bride with a Manushya groom scores 6, and a Manushya bride with a Deva groom scores 5.

Muhurta Chintamani gives only the ranking behind this table:

- own gana is best;
- Deva with Manushya is middling;
- Deva with Rakshasa brings enmity;
- Manushya with Rakshasa is the worst ("death").

The direction comes from later almanacs, and reproductions do not all keep it:

- Some guides, and two JavaScript libraries (`@prisri/jyotish` and `astrology-insights`), read the table the other way round: a Deva groom with a Manushya bride scores 6.
- Some give Deva with Rakshasa 0 or 1 in both directions.

A pair whose Moons are Deva and Manushya (or Deva and Rakshasa) can therefore show a total one point apart between apps. The test pairs below show which reading an app uses.

### Vashya (default)

Astroyogi's table, with the bride down the rows:

| Bride ↓ · Groom → | Chatushpada | Manava | Jalachara | Vanachara | Keeta |
|---|---|---|---|---|---|
| **Chatushpada** | 2 | 1 | 1 | 1.5 | 1 |
| **Manava** | 1 | 2 | 1.5 | 0 | 1 |
| **Jalachara** | 1 | 1.5 | 2 | 1 | 1 |
| **Vanachara** | 0 | 0 | 0 | 2 | 0 |
| **Keeta** | 1 | 1 | 1 | 0 | 2 |

The groups are:

| Group | Moon signs |
|---|---|
| Chatushpada (quadruped) | Mesha, Vrishabha, the second half of Dhanu, the first half of Makara |
| Manava (human) | Mithuna, Kanya, Tula, Kumbha, the first half of Dhanu |
| Jalachara (water) | Karka, Meena, the second half of Makara |
| Vanachara | Simha |
| Keeta | Vrishchika |

The engine splits Dhanu and Makara at 15°. PyJHora splits them by pada number, which differs in the middle pada.

### Yoni

The engine uses Saravali's 14 × 14 table as published, with the bride down the rows. Two cells differ from their mirror images:

- a horse bride with a deer groom scores 3, the reverse 1;
- a lion bride with a buffalo groom scores 2, the reverse 1.

Other software scores these four pairs 1, or reads the table with the groom first. Pair 5 below shows which.

## How precise is a score?

A score changes only if a Moon falls in a different nakshatra or sign, or the other half of Dhanu or Makara.

The Moon moves about half a degree an hour. It stays in a nakshatra for about a day and in a sign for about two and a half days. So a birth time that is a little off usually does not matter. A Moon near a boundary is the exception.

The match reports, for each partner, how many hours the Moon kept the same nakshatra, sign and Vashya half before and after the given time. The Kundli Check page turns this into plain words:

| Margin | What the page says |
|---|---|
| 3 hours or more | A birth time off by an hour or two does not change the score |
| 1 to 3 hours | A birth time off by more than the margin would change the score |
| Under 1 hour | The score depends on an exact birth time |

Software settings matter in the same way:

- **Ayanamsa.** The engine and nearly all Indian apps use Lahiri. Raman's ayanamsa is about 1.4° less, which moves the Moon by roughly two and a half hours' worth of motion. A Moon within that margin of a boundary can score differently in software set to Raman.
- **Time zones.** Calcutta kept its own local time until 1948 and Bombay until 1955. The engine corrects for them, so a birth there in those years should be entered as the clock showed it. Apps that ignore them place the Moon about half an hour's motion away.

## Checking the engine against matchmaking apps

The build environment cannot reach the apps' sites, so the check is done by hand. The five people below were chosen so that each Moon is more than 9 hours from any boundary. Every app should therefore agree on the nakshatras, and any difference in points comes from the tables alone.

All five were born in New Delhi, India (IST). `test_app_check_pairs_of_the_matching_doc` in `engine/tests/test_match.py` checks every value below, so a table change that alters them fails until this page is updated.

| Person | Born | Moon | Nakshatra | Gana |
|---|---|---|---|---|
| P1 | 5 January 1990, 6:00 pm | Mesha 5.3° | Ashwini pada 2 | Deva |
| P2 | 24 January 1991, 12:00 noon | Mesha 18.7° | Bharani pada 2 | Manushya |
| P3 | 22 January 1990, 1:00 am | Vrishchika 9.7° | Anuradha pada 2 | Deva |
| P4 | 14 January 1991, 1:00 am | Dhanu 5.5° | Mula pada 2 | Rakshasa |
| P5 | 14 January 1990, 6:00 am | Simha 5.0° | Magha pada 2 | Rakshasa |

Enter each pair with the first person as the boy (groom) and the second as the girl (bride). Compare the app's koota rows with the engine's:

| # | Boy | Girl | Varna | Vashya | Tara | Yoni | Maitri | Gana | Bhakoot | Nadi | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | P1 | P2 | 1 | 2 | 3 | 2 | 5 | 5 | 7 | 8 | **33** |
| 2 | P2 | P1 | 1 | 2 | 3 | 2 | 5 | 6 | 7 | 8 | **34** |
| 3 | P1 | P4 | 1 | 1 | 3 | 2 | 5 | 1 | 0 | 0 | **13** |
| 4 | P4 | P1 | 1 | 1 | 3 | 2 | 5 | 0 | 0 | 0 | **12** |
| 5 | P3 | P1 | 1 | 1 | 1.5 | 3 | 5 | 6 | 0 | 8 | **25.5** |
| 6 | P5 | P1 | 1 | 1.5 | 3 | 2 | 5 | 0 | 0 | 8 | **20.5** |
| 7 | P1 | P5 | 1 | 0 | 3 | 2 | 5 | 1 | 0 | 8 | **20** |

The totals other readings give for the same pairs:

| # | Engine | Maitreya profile | Gana read the other way | Yoni read groom first | Yoni symmetric (PyJHora) | Vashya read groom first |
|---|---|---|---|---|---|---|
| 1 | 33 | 33 | 34 | 33 | 33 | 33 |
| 2 | 34 | 34 | 33 | 34 | 34 | 34 |
| 3 | 13 | 13 | 12 | 13 | 13 | 13 |
| 4 | 12 | 11 | 13 | 12 | 12 | 12 |
| 5 | 25.5 | 24.5 | 25.5 | 23.5 | 23.5 | 25.5 |
| 6 | 20.5 | 19.5 | 21.5 | 20.5 | 20.5 | 19 |
| 7 | 20 | 20 | 19 | 20 | 20 | 21.5 |

How to read the result:

- **Pairs 1 and 2** differ only in Gana. An app that gives pair 1 Gana 6 and pair 2 Gana 5 reads the Gana table groom first.
- **Pairs 3 and 4** show the Deva–Rakshasa cells.
- **Pair 5** shows the lopsided Yoni cell: 3 means bride first, 1 means groom first or a symmetric table.
- **Pairs 6 and 7** show the Vashya table's Simha cells and the Gana Deva–Rakshasa cells together.

If several major apps agree on a reading the engine does not use, change the default profile's table in `tables.py`, update the tests in `test_match.py` and this page, and recompute the stored matches.

## Couples already married

A match can be made for a couple already married (`married` with an optional `wedding_year` and `wedding_month` in `scripts/match_report.py`, and on the Kundli Check page). The report then:

- checks the wedding against each partner's strong windows for marriage (inside one, within a year of one, or further away);
- reads the windows ahead as times for married life, not wedding dates;
- states that the score describes how the two charts fit by tradition, not how the marriage is or will be.

Each partner's windows are the ones that partner's own life reading tells (`life_windows`, strong windows only), so the match, the reading, its timeline and the chat name the same times. The same applies to a single person's reading. Someone who says they are married has the wedding checked against the chart and later stretches read as married life. Someone who says they are not married gets the windows that have passed and the next one. When nobody has said, the reading allows for either.

## Limits

- The 36 points are a traditional screening device. No study shows that guna scores predict how marriages turn out, and the product never presents a score as a verdict on two people.
- Whether an app's calculator follows the table its help pages print can only be confirmed with the test pairs above.
