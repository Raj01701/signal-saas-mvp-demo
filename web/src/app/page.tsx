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
        The calculation engine is being built first. The astrologer workbench and consumer app
        follow on the same API.
      </p>
    </main>
  );
}
