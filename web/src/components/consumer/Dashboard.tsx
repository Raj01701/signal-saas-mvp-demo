"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Status } from "@/components/common";
import { api, type Schemas } from "@/lib/api/client";
import { clock } from "@/lib/format";
import { icsCalendar } from "@/lib/ics";
import { formatDate, formatMonth, type Lang, useI18n } from "@/lib/i18n";
import { domainName, nakshatraName, planetName, tithiName, varaName } from "@/lib/names";
import { birthOf, type Profile } from "@/lib/profile";
import { disablePush, enablePush, pushState, type PushReminder, type PushState, refreshPush, reminderMoment } from "@/lib/push";
import { useLoad } from "@/lib/use-load";

type Tone = "favourable" | "mixed" | "challenging";
const toneOf = (value: number): Tone => (value > 0.15 ? "favourable" : value < -0.15 ? "challenging" : "mixed");
const polarityTone = (polarity?: string): Tone =>
  polarity === "positive" ? "favourable" : polarity === "negative" ? "challenging" : "mixed";
const card = "grid gap-2 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800";

function localToday(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function addMonths(day: string, months: number): string {
  const [y, m] = day.split("-").map(Number);
  const index = y * 12 + (m - 1) + months;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}-01`;
}

/** The consumer's plain-language dashboard: today, this month and the year ahead. */
export function Dashboard({ profile, onEdit, onForget }: { profile: Profile; onEdit: () => void; onForget: () => void }) {
  const { t, lang } = useI18n();
  const d = t.dashboard;
  const today = localToday();
  const birth = birthOf(profile);
  const key = JSON.stringify(birth);
  const period = useLoad(`period ${key}`, () => api.POST("/v1/charts/period", { body: { birth } }));
  const panchanga = useLoad(`panchanga ${today} ${key}`, () =>
    api.POST("/v1/panchanga", { body: { date: today, place: profile.location.place, zone: profile.location.zone } }),
  );
  const start = `${today.slice(0, 7)}-01`;
  const predictions = useLoad(`predictions ${start} ${key}`, () =>
    api.POST("/v1/charts/predictions", { body: { birth, start, end: addMonths(start, 12) } }),
  );
  const uncertain = profile.source === "estimate" || profile.source === "unknown" || profile.uncertainty >= 60;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-2xl font-semibold">{d.hello(profile.name)}</h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            {d.born(formatDate(profile.date, lang), profile.time, profile.location.place.name ?? "")}
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <button type="button" onClick={onEdit} className="rounded-md border border-zinc-300 px-3 py-1.5 dark:border-zinc-700">{d.edit}</button>
          <button type="button" onClick={onForget} className="rounded-md border border-zinc-300 px-3 py-1.5 dark:border-zinc-700">{d.forget}</button>
        </div>
      </div>

      {uncertain && (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-700 dark:bg-amber-950">
          {d.uncertain} <Link href="/rectify" className="font-medium underline">{d.rectify}</Link>
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <section aria-labelledby="today-heading" className={card}>
          <h3 id="today-heading" className="text-lg font-semibold">{d.today}</h3>
          <Status loading={panchanga.loading || period.loading} error={panchanga.error ?? period.error} />
          {panchanga.data && <TodayLines panchanga={panchanga.data} period={period.data} lang={lang} />}
          <Link href="/panchanga" className="text-sm underline">{d.panchangaLink}</Link>
        </section>

        <section aria-labelledby="month-heading" className={card}>
          <h3 id="month-heading" className="text-lg font-semibold">{d.month}</h3>
          <Status loading={period.loading} error={period.error} />
          {period.data && <MonthLines period={period.data} lang={lang} />}
        </section>
      </div>

      <section aria-labelledby="year-heading" className={card}>
        <h3 id="year-heading" className="text-lg font-semibold">{d.year}</h3>
        <Status loading={predictions.loading} error={predictions.error} />
        {predictions.data && <YearLines predictions={predictions.data} today={today} lang={lang} />}
      </section>

      {panchanga.data && period.data && predictions.data && (
        <Reminders panchanga={panchanga.data} predictions={predictions.data} today={today} lang={lang} />
      )}

      <p className="text-sm"><Link href="/match" className="underline">{d.matchLink}</Link></p>
      <p className="text-xs text-zinc-500">{t.common.disclaimer}</p>
    </div>
  );
}

function TodayLines({ panchanga, period, lang }: { panchanga: Schemas["PanchangaOut"]; period?: Schemas["PeriodReadingsOut"]; lang: Lang }) {
  const { t } = useI18n();
  const at = (iso: string) => clock(iso, panchanga.utc_offset_seconds, panchanga.civil_date);
  const tithi = panchanga.tithis[0];
  const nakshatra = panchanga.nakshatras[0];
  const rahu = panchanga.kalams.find((k) => k.name === "Rahu kalam");
  const moon = period?.transits.find((p) => p.body === "moon");
  const moonRule = period && moon
    ? [...period.transit_readings, ...period.cancelled].find((r) => r.id === `transit.moon_h${moon.house_from_moon}`)
    : undefined;
  return (
    <ul className="grid gap-1 text-sm">
      <li>{t.dashboard.todayLine(varaName(panchanga.vara, lang), tithiName(tithi.number, tithi.name, lang), nakshatraName(nakshatra.number, nakshatra.name, lang))}</li>
      {rahu && <li>{t.dashboard.rahu(at(rahu.start), at(rahu.end))}</li>}
      {moon && <li>{t.dashboard.moon(moon.house_from_moon, t.common.tones[polarityTone(moonRule?.polarity)])}</li>}
    </ul>
  );
}

function MonthLines({ period, lang }: { period: Schemas["PeriodReadingsOut"]; lang: Lang }) {
  const { t } = useI18n();
  const [md, ad] = period.dasha;
  const mdLord = md.lords[0];
  const adLord = ad.lords[1];
  const pair = period.dasha_readings.find((r) => r.id === `dasha.pair_${mdLord}_${adLord}`);
  const sadeSati = period.transit_readings.some((r) => r.id === "transit.sade_sati");
  const why = [...period.dasha_readings, ...period.transit_readings];
  return (
    <>
      <ul className="grid gap-1 text-sm">
        <li>{t.dashboard.period(planetName(mdLord, lang), planetName(adLord, lang), formatDate(ad.end, lang))}</li>
        {pair && <li>{t.dashboard.periodTone(t.common.tones[polarityTone(pair.polarity)])}</li>}
        {sadeSati && <li>{t.dashboard.sadeSati}</li>}
      </ul>
      <details className="text-sm">
        <summary className="cursor-pointer">{t.dashboard.why}</summary>
        <ul className="mt-1 grid gap-1 text-zinc-700 dark:text-zinc-300" lang="en">
          {why.map((r) => <li key={r.id}><span className="font-medium">{r.name}:</span> {r.summary}</li>)}
        </ul>
      </details>
    </>
  );
}

/** The strongest window of each domain in the next twelve months (health left to the professional view). */
export function yearWindows(predictions: Schemas["PredictionsOut"], today: string) {
  return predictions.domains
    .filter((d) => d.domain !== "health")
    .flatMap((d) => {
      const coming = d.windows.filter((w) => w.end > today);
      const best = coming.sort((a, b) => b.score - a.score)[0];
      return best ? [{ domain: d.domain as string, window: best }] : [];
    })
    .sort((a, b) => a.window.start.localeCompare(b.window.start));
}

function YearLines({ predictions, today, lang }: { predictions: Schemas["PredictionsOut"]; today: string; lang: Lang }) {
  const { t } = useI18n();
  const items = yearWindows(predictions, today);
  if (items.length === 0) return <p className="text-sm">{t.dashboard.noWindows}</p>;
  return (
    <ul className="grid gap-1 text-sm" aria-label={t.dashboard.year}>
      {items.map(({ domain, window }) => (
        <li key={domain}>
          {t.dashboard.window(
            domainName(domain, lang),
            formatMonth(window.start, lang),
            formatMonth(new Date(Date.parse(window.end) - 86_400_000).toISOString(), lang),
            t.common.tones[toneOf(window.tone)],
            t.common.confidence[window.confidence],
          )}
        </li>
      ))}
    </ul>
  );
}

function Reminders({ panchanga, predictions, today, lang }: { panchanga: Schemas["PanchangaOut"]; predictions: Schemas["PredictionsOut"]; today: string; lang: Lang }) {
  const { t } = useI18n();
  const d = t.dashboard;
  const at = (iso: string) => clock(iso, panchanga.utc_offset_seconds, panchanga.civil_date);
  const rahu = panchanga.kalams.find((k) => k.name === "Rahu kalam");
  const soon = addMonths(today, 3);
  const dashaChanges = predictions.periods
    .filter((p) => p.lords.length === 2 && p.start.slice(0, 10) > today && p.start.slice(0, 10) < soon)
    .map((p) => ({ date: p.start.slice(0, 10), text: d.alertDasha(formatDate(p.start, lang), planetName(p.lords[1], lang)) }));
  const windows = yearWindows(predictions, today)
    .filter(({ window }) => window.start > today && window.start < soon)
    .map(({ domain, window }) => ({ date: window.start, text: d.alertWindow(formatDate(window.start, lang), domainName(domain, lang)) }));
  const upcoming = [...dashaChanges, ...windows].sort((a, b) => a.date.localeCompare(b.date));
  const calendar = [
    ...predictions.periods
      .filter((p) => p.lords.length === 2 && p.start.slice(0, 10) > today)
      .map((p) => ({ date: p.start.slice(0, 10), summary: d.alertDasha(formatDate(p.start, lang), planetName(p.lords[1], lang)) })),
    ...yearWindows(predictions, today).map(({ domain, window }) => ({ date: window.start, summary: d.alertWindow(formatDate(window.start, lang), domainName(domain, lang)) })),
  ];
  const pushReminders = calendar
    .filter((c) => c.date > today)
    .map((c) => ({ at: reminderMoment(c.date), title: d.pushTitle, body: c.summary }));
  const stamp = `${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`;
  const href = `data:text/calendar;charset=utf-8,${encodeURIComponent(icsCalendar(calendar, stamp))}`;
  return (
    <section aria-labelledby="alerts-heading" className={card}>
      <h3 id="alerts-heading" className="text-lg font-semibold">{d.alerts}</h3>
      <ul className="grid gap-1 text-sm">
        {rahu && <li>{d.alertRahu(at(rahu.start), at(rahu.end))}</li>}
        {upcoming.map((u) => <li key={`${u.date}-${u.text}`}>{u.text}</li>)}
      </ul>
      <a href={href} download="jyotish-reminders.ics" className="w-fit text-sm font-medium underline">{d.calendar}</a>
      <PushToggle reminders={pushReminders} />
    </section>
  );
}

/** Browser notifications for the reminders; hidden where the browser or the API cannot do push. */
function PushToggle({ reminders }: { reminders: PushReminder[] }) {
  const { t } = useI18n();
  const d = t.dashboard;
  const [state, setState] = useState<PushState>("unsupported");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const key = JSON.stringify(reminders);
  useEffect(() => {
    let live = true;
    pushState()
      .then(async (current) => {
        if (current === "on") await refreshPush(JSON.parse(key) as PushReminder[]);
        if (live) setState(current);
      })
      .catch(() => {
        if (live) setState("unsupported");
      });
    return () => {
      live = false;
    };
  }, [key]);
  if (state === "unsupported") return null;
  const toggle = async () => {
    setBusy(true);
    setFailed(false);
    try {
      setState(state === "on" ? await disablePush() : await enablePush(reminders));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="grid gap-1 text-sm">
      {state === "denied" ? (
        <p>{d.pushDenied}</p>
      ) : (
        <button type="button" onClick={toggle} disabled={busy} className="w-fit rounded-md border border-zinc-300 px-3 py-1.5 dark:border-zinc-700">
          {state === "on" ? d.pushOff : d.pushOn}
        </button>
      )}
      {state === "on" && <p>{d.pushActive}</p>}
      {failed && <p role="alert">{d.pushError}</p>}
      <p className="text-zinc-600 dark:text-zinc-400">{d.pushPrivacy}</p>
    </div>
  );
}
