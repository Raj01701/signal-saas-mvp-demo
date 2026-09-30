"use client";

import { type FormEvent, useId, useState } from "react";

import type { BirthRequest } from "@/components/BirthForm";
import { Status } from "@/components/common";
import { input } from "@/components/PlaceField";
import { api } from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";

const anchor = (id: string) => `evidence-${id.replace(/[^a-z0-9]+/gi, "-")}`;

/** A plain-language reading whose every paragraph cites the engine evidence behind it. */
export function ReportPanel({ request }: { request: BirthRequest }) {
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
      <AskBox request={request} />
    </div>
  );
}

function AskBox({ request }: { request: BirthRequest }) {
  const id = useId();
  const [draft, setDraft] = useState("");
  const [question, setQuestion] = useState<string | null>(null);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (draft.trim()) setQuestion(draft.trim());
  };
  return (
    <section aria-labelledby={`${id}-heading`} className="grid gap-2 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
      <h3 id={`${id}-heading`} className="font-semibold">Ask about this chart</h3>
      <form onSubmit={submit} className="flex flex-wrap gap-2" aria-label="Ask about this chart">
        <label htmlFor={`${id}-question`} className="sr-only">Question</label>
        <input
          id={`${id}-question`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="For example: how is my career now?"
          className={`${input} min-w-0 flex-1`}
        />
        <button type="submit" className="rounded-md bg-amber-700 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-800">
          Ask
        </button>
      </form>
      {question && <Answer request={request} question={question} />}
    </section>
  );
}

function Answer({ request, question }: { request: BirthRequest; question: string }) {
  const { data, error, loading } = useLoad(`${question} ${JSON.stringify(request)}`, () =>
    api.POST("/v1/charts/chat", { body: { ...request, messages: [{ role: "user", content: question }] } }),
  );
  if (!data) return <Status loading={loading} error={error} />;
  return (
    <div className="grid gap-1 text-sm" aria-live="polite">
      <p className="whitespace-pre-line">{data.answer}</p>
      <p className="text-xs text-zinc-500">Evidence: {data.evidence.map((e) => e.id).join(", ")}</p>
    </div>
  );
}
