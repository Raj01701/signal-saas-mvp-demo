import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex flex-1 max-w-3xl flex-col justify-center gap-6 px-4 py-16">
      <p className="text-sm font-medium uppercase tracking-widest text-amber-700 dark:text-amber-400">
        Jyotish Platform
      </p>
      <h1 className="text-4xl font-semibold tracking-tight">
        Precise Vedic astrology, explained with its sources.
      </h1>
      <p className="text-lg leading-8 text-zinc-600 dark:text-zinc-300">
        Charts, divisional charts and dashas calculated to the arcsecond, with every setting
        visible; the panchanga and horoscope matching use the same engine. The consumer app follows on the same API.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/workbench"
          className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800"
        >
          Open the astrologer workbench
        </Link>
        <Link href="/panchanga" className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold dark:border-zinc-700">
          Today&apos;s panchanga
        </Link>
        <Link href="/match" className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-semibold dark:border-zinc-700">
          Match two charts
        </Link>
      </div>
    </main>
  );
}
