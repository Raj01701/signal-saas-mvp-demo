import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms · Jyotish Platform",
  description: "The terms on which the Jyotish Platform offers its calculations and interpretations.",
};

const section = "grid gap-2";

export default function TermsPage() {
  return (
    <main className="mx-auto grid w-full max-w-3xl gap-6 px-4 py-8 text-sm leading-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Terms of use</h1>
        <p className="rounded-md border border-amber-300 bg-amber-50 p-2 dark:border-amber-700 dark:bg-amber-950">
          Draft for review. These terms must be reviewed by a lawyer before public launch.
        </p>
      </div>
      <section className={section} aria-labelledby="service">
        <h2 id="service" className="text-lg font-semibold">What the service is</h2>
        <p>
          The platform calculates Vedic astrology charts precisely and presents the interpretations of the classical texts
          and of traditional practice, with their sources. Controlled studies have not shown that astrological predictions
          work better than chance; we measure our own results and publish them.
        </p>
      </section>
      <section className={section} aria-labelledby="not">
        <h2 id="not" className="text-lg font-semibold">What it is not</h2>
        <p>
          Readings are traditional interpretations, not certainties or guarantees. They are not medical, legal, financial or
          psychological advice; consult a qualified professional for those. Traditional remedies are described as practices
          of the tradition, never as cures.
        </p>
      </section>
      <section className={section} aria-labelledby="use">
        <h2 id="use" className="text-lg font-semibold">Fair use</h2>
        <p>
          Enter only data you are entitled to use, for yourself or with the person&apos;s consent. Automated bulk use of the
          API needs a separate agreement.
        </p>
      </section>
      <section className={section} aria-labelledby="liability">
        <h2 id="liability" className="text-lg font-semibold">Liability and law</h2>
        <p>Limitation of liability, governing law and jurisdiction: to be completed with legal review.</p>
      </section>
    </main>
  );
}
