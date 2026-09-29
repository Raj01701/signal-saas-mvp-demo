# Knowledge base

Classical Jyotish rules encoded as data: yogas, house-lord results, planet-in-sign and
planet-in-house results, dasha results, transit results, remedies.

## Rules for contributors

- **Paraphrase, never copy.** Sanskrit originals are public domain; modern English
  translations are usually copyrighted. Write each rule in your own words.
- **Always cite.** Every rule lists its source (`text`, `edition`, `chapter`, `verse`) in
  `sources:`. Chapter numbering differs between editions, so the edition is mandatory.
  Mark `verified: false` until someone checks the citation against that edition.
- **Record provenance.** Tag rules as `classical` or `modern` (for example, Kala Sarpa
  Yoga is modern and absent from BPHS).
- **Ship tests.** Every rule has at least one chart where it should fire and one where
  it must not.
- **Review status.** Rules start as `status: draft`. Only a qualified Jyotishi moves a
  rule to `reviewed`. Draft rules are hidden from consumer readings.

The rule format and evaluator arrive in milestone M4. The bibliography lives in
[`sources.yaml`](sources.yaml).
