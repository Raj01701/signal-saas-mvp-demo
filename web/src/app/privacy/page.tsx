import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy · Jyotish Platform",
  description: "What the Jyotish Platform stores, why, and your rights over it.",
};

const section = "grid gap-2";

export default function PrivacyPage() {
  return (
    <main className="mx-auto grid w-full max-w-3xl gap-6 px-4 py-8 text-sm leading-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Privacy notice</h1>
        <p className="rounded-md border border-amber-300 bg-amber-50 p-2 dark:border-amber-700 dark:bg-amber-950">
          Draft for review. This notice must be reviewed by a lawyer, and the contact details completed, before public launch.
        </p>
      </div>
      <section className={section} aria-labelledby="collect">
        <h2 id="collect" className="text-lg font-semibold">What we collect</h2>
        <p>
          Birth date, time and place, and optionally a name, gender and dated life events. Under India&apos;s Digital
          Personal Data Protection Act 2023 and the EU GDPR these are personal data.
        </p>
      </section>
      <section className={section} aria-labelledby="where">
        <h2 id="where" className="text-lg font-semibold">Where it is kept</h2>
        <p>
          Without an account, the details you enter in &ldquo;My reading&rdquo; stay in your browser on this device; our
          servers receive them only to calculate each result and do not store them. With an account, the people and events
          you save are stored in our database. Our request logs record the route, status and timing, never birth data or
          your network address (hosting providers may keep their own connection logs). If you turn on reminder
          notifications, we keep your browser&apos;s push address and the reminder texts
          and dates your browser sends (never your birth details), delete each reminder once it is sent, and forget the
          address when you turn notifications off or after 30 days without pending reminders.
        </p>
      </section>
      <section className={section} aria-labelledby="purposes">
        <h2 id="purposes" className="text-lg font-semibold">Purposes</h2>
        <p>
          To calculate charts and readings for you. Only if you opt in, your saved events, without names, are used to
          measure how well the methods work (the Accuracy Lab); you can withdraw that consent at any time.
        </p>
      </section>
      <section className={section} aria-labelledby="rights">
        <h2 id="rights" className="text-lg font-semibold">Your rights</h2>
        <p>
          You can see and export everything stored for your account, correct it, and delete your account with all its data
          at once. Details kept only on your device can be deleted from &ldquo;My reading&rdquo;. A person under 18 may be
          saved only with the consent of the account holder as guardian.
        </p>
      </section>
      <section className={section} aria-labelledby="sharing">
        <h2 id="sharing" className="text-lg font-semibold">Sharing</h2>
        <p>
          We do not sell personal data. Service providers process it for us: hosting, sign-in (Supabase) and, only where
          written readings by a language model are switched on, Anthropic, which receives the calculated evidence without
          your name.
        </p>
      </section>
      <section className={section} aria-labelledby="contact">
        <h2 id="contact" className="text-lg font-semibold">Contact and grievances</h2>
        <p>Grievance officer: to be appointed before launch.</p>
      </section>
      <section className={section} aria-labelledby="hindi" lang="hi">
        <h2 id="hindi" className="text-lg font-semibold">सारांश</h2>
        <p>
          हम जन्म की तिथि, समय और स्थान केवल आपकी कुंडली की गणना के लिए उपयोग करते हैं। खाते के बिना आपका विवरण केवल आपके डिवाइस पर रहता है।
          आप अपना सारा डेटा देख, निर्यात कर और हटा सकते हैं। शोध में उपयोग केवल आपकी सहमति से, बिना नाम के होता है।
          सूचनाएँ चालू करने पर हम केवल अनुस्मारक और उनकी तिथियाँ रखते हैं, जन्म विवरण नहीं।
        </p>
      </section>
    </main>
  );
}
