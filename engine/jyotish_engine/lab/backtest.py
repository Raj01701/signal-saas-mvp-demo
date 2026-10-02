"""The Accuracy Lab: do the prediction windows find recorded events better than chance?

For each case (a birth and its dated life events) the prediction timeline is computed
for the recorded birth and for controls:

- **Shuffled time:** the same date and place at random times of day. The slow
  planets stay; the Moon, the lagna and so the dashas and houses change.
- **Swapped events:** another case's events, moved to the same ages, scored against
  this chart.

Each event is scored by the percentile of its month's score among the months its
domain is read in (1 = the strongest month) and by whether a window contains it.
The report gives, per domain and overall, these measures for the true charts and the
controls, the lift, and a permutation p-value from the shuffled-time replicates;
and per confidence label, how many windows contained an event of their domain.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, PredictionsOut
from jyotish_engine.predict import compute_predictions
from jyotish_engine.predict.techniques import FULL, TimingModel
from jyotish_engine.rectify.events import EVENT_SPECS, EventKind
from jyotish_engine.rectify.search import LifeEvent


@dataclass(frozen=True)
class Case:
    birth: BirthInput
    events: tuple[LifeEvent, ...]
    gender: str | None = None


@dataclass(frozen=True, slots=True)
class EventScore:
    domain: str
    percentile: float
    hit: bool


@dataclass
class Tally:
    n: int = 0
    hits: int = 0
    percentiles: float = 0.0

    def add(self, score: EventScore) -> None:
        self.n += 1
        self.hits += score.hit
        self.percentiles += score.percentile

    @property
    def hit_rate(self) -> float:
        return self.hits / self.n if self.n else 0.0

    @property
    def mean_percentile(self) -> float:
        return self.percentiles / self.n if self.n else 0.0


@dataclass
class LabReport:
    cases: int
    events: int
    replicates: int
    true: dict[str, Tally] = field(default_factory=lambda: defaultdict(Tally))
    shuffled: dict[str, Tally] = field(default_factory=lambda: defaultdict(Tally))
    swapped: dict[str, Tally] = field(default_factory=lambda: defaultdict(Tally))
    #: Mean event percentile of each shuffled-time replicate, for the p-value.
    replicate_means: list[float] = field(default_factory=list)
    #: Confidence label -> [windows, windows containing an event of their domain].
    calibration: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))

    @property
    def p_value(self) -> float:
        """Share of shuffled replicates at least as good as the true charts."""
        truth = self.true["all"].mean_percentile
        better = sum(m >= truth for m in self.replicate_means)
        return (1 + better) / (1 + len(self.replicate_means))


def _month(day: date) -> date:
    return date(day.year, day.month, 1)


def score_events(predictions: PredictionsOut, events: Sequence[LifeEvent]) -> list[EventScore]:
    """The percentile and window hit of each event inside the timeline's range."""
    index = {m: i for i, m in enumerate(predictions.months)}
    timelines = {d.domain.value: d for d in predictions.domains}
    out = []
    for event in events:
        spec = EVENT_SPECS.get(event.kind)
        month = index.get(_month(event.date))
        if spec is None or month is None:
            continue
        timeline = timelines[spec.domain.value]
        value = timeline.scores[month]
        read = [s for s in timeline.scores if s > 0]
        if value <= 0 or not read:
            percentile = 0.0
        else:
            below = sum(s < value for s in read)
            ties = sum(s == value for s in read)
            percentile = (below + 0.5 * ties) / len(read)
        hit = any(w.start <= event.date < w.end for w in timeline.windows)
        out.append(EventScore(spec.domain.value, percentile, hit))
    return out


def _predictions(
    birth: BirthInput, until: date, gender: str | None, model: TimingModel = FULL
) -> tuple[PredictionsOut, date]:
    chart = compute_chart(birth)
    start = birth.local_datetime.date().replace(day=1)
    end = _month(until) + timedelta(days=62)
    return compute_predictions(chart, start, end.replace(day=1), gender=gender, model=model), start


def _moved(events: Sequence[LifeEvent], source: BirthInput, target: BirthInput) -> list[LifeEvent]:
    """Events of one birth at the same ages for another."""
    shift = target.local_datetime.date() - source.local_datetime.date()
    return [LifeEvent(e.kind, e.date + shift) for e in events]


def backtest(
    cases: Sequence[Case], replicates: int = 5, seed: int = 0, model: TimingModel = FULL
) -> LabReport:
    """Score every case's events against its chart and against the controls, with the
    timing techniques of ``model``."""
    rng = random.Random(seed)
    scored = [c for c in cases if any(e.kind is not EventKind.OTHER for e in c.events)]
    report = LabReport(cases=len(scored), events=0, replicates=replicates)
    replicate_tallies = [Tally() for _ in range(replicates)]
    truths = []
    for case in scored:
        last = max(e.date for e in case.events)
        predictions, _ = _predictions(case.birth, last, case.gender, model)
        truths.append(predictions)
        for score in score_events(predictions, case.events):
            report.events += 1
            report.true[score.domain].add(score)
            report.true["all"].add(score)
        for domain in predictions.domains:
            for window in domain.windows:
                entry = report.calibration[window.confidence]
                entry[0] += 1
                entry[1] += any(
                    EVENT_SPECS.get(e.kind) is not None
                    and EVENT_SPECS[e.kind].domain is domain.domain
                    and window.start <= e.date < window.end
                    for e in case.events
                )
        for r in range(replicates):
            minutes = rng.randrange(24 * 60)
            moved = case.birth.local_datetime.replace(hour=minutes // 60, minute=minutes % 60)
            control, _ = _predictions(
                case.birth.model_copy(update={"local_datetime": moved}), last, case.gender, model
            )
            for score in score_events(control, case.events):
                report.shuffled[score.domain].add(score)
                report.shuffled["all"].add(score)
                replicate_tallies[r].add(score)
    for i, case in enumerate(scored):
        others = [c for j, c in enumerate(scored) if j != i]
        if not others:
            continue
        donor = others[rng.randrange(len(others))]
        for score in score_events(truths[i], _moved(donor.events, donor.birth, case.birth)):
            report.swapped[score.domain].add(score)
            report.swapped["all"].add(score)
    report.replicate_means = [t.mean_percentile for t in replicate_tallies if t.n]
    return report


def render_markdown(report: LabReport, title: str, note: str) -> str:
    """The report as Markdown."""
    lines = [
        f"# {title}",
        "",
        note,
        "",
        f"{report.cases} cases, {report.events} events, {report.replicates} shuffled-time "
        f"replicates per case. Permutation p-value (mean percentile, shuffled time): "
        f"{report.p_value:.3f}.",
        "",
        "| Domain | Events | Hit rate | Shuffled time | Swapped events "
        "| Mean percentile | Shuffled | Swapped | Lift (hits) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for domain in sorted(report.true, key=lambda d: (d != "all", d)):
        t, s, w = report.true[domain], report.shuffled[domain], report.swapped[domain]
        lift = f"{t.hit_rate / s.hit_rate:.2f}" if s.hit_rate else "n/a"
        rates = f"{t.hit_rate:.2f} | {s.hit_rate:.2f} | {w.hit_rate:.2f}"
        means = f"{t.mean_percentile:.2f} | {s.mean_percentile:.2f} | {w.mean_percentile:.2f}"
        lines.append(f"| {domain} | {t.n} | {rates} | {means} | {lift} |")
    lines += [
        "",
        "Calibration: windows by confidence label, and the share containing an event of "
        "their domain.",
        "",
    ]
    lines += ["| Confidence | Windows | With an event | Share |", "|---|---|---|---|"]
    windows = sum(total for total, _ in report.calibration.values())
    for label in ("strong", "moderate", "weak"):
        total, hit = report.calibration.get(label, [0, 0])
        share = f"{hit / total:.2f}" if total else "n/a"
        lines.append(f"| {label} | {total} | {hit} | {share} |")
    strong = report.calibration.get("strong", [0, 0])[0]
    lines += [
        "",
        "Reading the numbers:",
        "",
        f"- With {report.replicates} replicates the smallest possible p-value is "
        f"{1 / (report.replicates + 1):.3f}; more replicates resolve smaller ones.",
        "- A label is useful only if windows grow rarer and more often contain events as the "
        f"label grows stronger. Here {strong} of {windows} windows are labelled strong, so the "
        "thresholds need recalibrating on recorded events before the labels mean much.",
    ]
    return "\n".join(lines) + "\n"
