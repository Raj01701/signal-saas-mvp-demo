"use client";

import type { BirthRequest } from "@/components/BirthForm";
import { ChatPanel } from "@/components/ChatPanel";
import { Status } from "@/components/common";
import { api } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n";
import { useLoad } from "@/lib/use-load";

const anchor = (id: string) => `evidence-${id.replace(/[^a-z0-9]+/gi, "-")}`;

/** A plain-language reading whose every paragraph cites the engine evidence behind it. */
export function ReportPanel({ request }: { request: BirthRequest }) {
  const { t } = useI18n();
  const { data, error, loading } = useLoad(JSON.stringify(request), () =>
    api.POST("/v1/charts/report", { body: request }),
  );
  const number = new Map(data?.evidence.map((e, i) => [e.id, i + 1]));
  return (
    <div className="grid gap-6">
      <Status loading={loading} error={error} />
      {data && (
        <article aria-labelledby="report-title" className="grid gap-4">
          <div>
            <h3 id="report-title" className="text-lg font-semibold">{data.report.title}</h3>
            <p className="text-xs text-zinc-500">
              {data.narrator === "template"
                ? "Assembled from the evidence by the offline narrator; no language model was used."
                : `Written by ${data.narrator} from the evidence below and checked before display.`}
            </p>
          </div>
          {data.report.sections.map((section) => (
            <section key={section.heading} className="grid gap-2">
              <h4 className="font-semibold">{section.heading}</h4>
              {section.paragraphs.map((p, i) => (
                <p key={i} className="text-sm leading-6">
                  {p.text}{" "}
                  {p.evidence_ids.map((id) => (
                    <a key={id} href={`#${anchor(id)}`} className="text-xs text-amber-800 underline dark:text-amber-400">
                      [{number.get(id)}]
                    </a>
                  ))}
                </p>
              ))}
            </section>
          ))}
          <section aria-labelledby="evidence-heading" className="grid gap-1 text-sm">
            <h4 id="evidence-heading" className="font-semibold">Evidence</h4>
            <ol className="list-decimal pl-6">
              {data.evidence.map((e) => (
                <li key={e.id} id={anchor(e.id)}>
                  <span className="font-medium">{e.title}</span>
                  {e.period ? ` (${e.period})` : ""}: {e.text}{" "}
                  <code className="text-xs text-zinc-500">{e.id}</code>
                  {e.sources && e.sources.length > 0 && <span className="text-xs text-zinc-500"> · {e.sources.slice(0, 2).join("; ")}</span>}
                </li>
              ))}
            </ol>
          </section>
          <p className="text-xs text-zinc-500">{data.disclaimer}</p>
        </article>
      )}
      <ChatPanel request={request} suggestions={t.chat.suggestions(new Date().getFullYear() + 1)} />
    </div>
  );
}
