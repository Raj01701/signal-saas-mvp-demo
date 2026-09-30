# Accuracy Lab (synthetic check)

These events were generated from the engine's own rules, so this run only checks that the lab separates the true birth time from the controls. It says nothing about predictive validity; that needs recorded, consented events.

12 cases, 60 events, 5 shuffled-time replicates per case. Permutation p-value (mean percentile, shuffled time): 0.167.

| Domain | Events | Hit rate | Shuffled time | Swapped events | Mean percentile | Shuffled | Swapped | Lift (hits) |
|---|---|---|---|---|---|---|---|---|
| all | 60 | 0.67 | 0.25 | 0.09 | 0.79 | 0.48 | 0.47 | 2.67 |
| career | 24 | 0.58 | 0.21 | 0.00 | 0.79 | 0.50 | 0.45 | 2.80 |
| children | 12 | 0.67 | 0.25 | 0.00 | 0.78 | 0.43 | 0.38 | 2.67 |
| marriage | 12 | 0.67 | 0.25 | 0.33 | 0.75 | 0.47 | 0.69 | 2.67 |
| property | 12 | 0.83 | 0.33 | 0.08 | 0.84 | 0.52 | 0.33 | 2.50 |

Calibration: windows by confidence label, and the share containing an event of their domain.

| Confidence | Windows | With an event | Share |
|---|---|---|---|
| strong | 1063 | 25 | 0.02 |
| moderate | 350 | 12 | 0.03 |
| weak | 14 | 0 | 0.00 |

Reading the numbers:

- With 5 replicates the smallest possible p-value is 0.167; more replicates resolve smaller ones.
- A label is useful only if windows grow rarer and more often contain events as the label grows stronger. Here 1063 of 1427 windows are labelled strong, so the thresholds need recalibrating on recorded events before the labels mean much.
