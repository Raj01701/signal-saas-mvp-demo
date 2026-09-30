export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-6 px-4 py-16">
      <p className="text-sm font-medium uppercase tracking-widest text-amber-700 dark:text-amber-400">
        Jyotish Platform
      </p>
      <h1 className="text-4xl font-semibold tracking-tight">
        Precise Vedic astrology, explained with its sources.
      </h1>
      <p className="text-lg leading-8 text-zinc-600 dark:text-zinc-300">
        Charts, divisional charts and dashas calculated to the arcsecond, with every setting
        visible. The consumer app follows on the same API.
      </p>
      <a
        href="/workbench"
        className="w-fit rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800"
      >
        Open the astrologer workbench
      </a>
    </main>
  );
}
