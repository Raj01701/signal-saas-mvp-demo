"use client";

import { type FormEvent, type KeyboardEvent, useEffect, useId, useRef, useState } from "react";

import { input } from "@/components/PlaceField";
import { api, errorMessage, type Schemas } from "@/lib/api/client";
import { chatKey, loadTurns, outgoing, saveTurns, type Turn } from "@/lib/chat";
import { useI18n } from "@/lib/i18n";

export type ChatTarget = Omit<Schemas["ChatRequest"], "messages" | "language" | "name">;

interface ChatProps {
  /** The chart the conversation is about (birth details, settings, gender). */
  request: ChatTarget;
  /** The person's first name, for more personal answers. */
  name?: string;
  /** Starter questions, shown until the first question. */
  suggestions?: string[];
}

/**
 * A conversation about one chart: the person asks anything in their own words, and each
 * answer comes from the engine's results (with Claude when the server has it), with the
 * findings it rests on. The conversation is kept only on this device, per chart.
 */
export function ChatPanel(props: ChatProps) {
  const key = chatKey(props.request.birth);
  return <Conversation key={key} storageKey={key} {...props} />;
}

function Conversation({ request, name, suggestions, storageKey }: ChatProps & { storageKey: string }) {
  const { t } = useI18n();
  const c = t.chat;
  const id = useId();
  const [turns, setTurns] = useState<Turn[]>(() => loadTurns(storageKey));
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (turns.length) end.current?.scrollIntoView({ block: "nearest" });
  }, [turns.length, busy]);
  useEffect(() => () => pending.current?.abort(), []);

  const ask = async (text: string) => {
    const question = text.trim();
    if (!question) return;
    if (busy) {
      setError(c.busy);
      return;
    }
    const before = turns;
    const asked: Turn[] = [...before, { role: "user", content: question }];
    setTurns(asked);
    setDraft("");
    setError(null);
    setBusy(true);
    const controller = new AbortController();
    pending.current = controller;
    const restore = () => {
      setTurns(before);
      setDraft(question);
    };
    try {
      const { data, error: failure } = await api.POST("/v1/charts/chat", {
        body: { ...request, name: name || null, language: "auto", messages: outgoing(asked) },
        signal: controller.signal,
      });
      if (data) {
        const answered: Turn[] = [
          ...asked,
          { role: "assistant", content: data.answer, evidence: data.evidence, narrator: data.narrator },
        ];
        setTurns(answered);
        saveTurns(storageKey, answered);
      } else {
        restore();
        setError(errorMessage(failure));
      }
    } catch {
      restore();
      if (!controller.signal.aborted) setError(c.error);
    } finally {
      if (pending.current === controller) pending.current = null;
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void ask(draft);
  };
  const onKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void ask(draft);
    }
  };
  const clear = () => {
    setTurns([]);
    saveTurns(storageKey, []);
    setError(null);
  };

  return (
    <section aria-labelledby={`${id}-heading`} className="grid gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="grid gap-1">
        <h3 id={`${id}-heading`} className="text-lg font-semibold">{c.heading}</h3>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{c.intro}</p>
      </div>
      {(turns.length > 0 || busy) && (
        <div role="log" aria-label={c.log} aria-busy={busy} className="grid max-h-[36rem] gap-3 overflow-y-auto pr-1">
          {turns.map((turn, i) => (
            <Message key={i} turn={turn} />
          ))}
          {busy && <p className="text-sm text-zinc-600 dark:text-zinc-400">{c.thinking}</p>}
          <div ref={end} />
        </div>
      )}
      {turns.length === 0 && !busy && suggestions && suggestions.length > 0 && (
        <div className="grid gap-1">
          <p className="text-sm font-medium">{c.tryThese}</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => void ask(s)}
                className="rounded-full border border-amber-300 px-3 py-1 text-left text-sm hover:bg-amber-50 dark:border-amber-800 dark:hover:bg-amber-950"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
      <form onSubmit={submit} className="grid gap-2">
        <label htmlFor={`${id}-question`} className="text-sm font-medium">{c.label}</label>
        <textarea
          id={`${id}-question`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          rows={2}
          maxLength={1000}
          placeholder={c.placeholder}
          className={`${input} resize-y`}
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy || !draft.trim()}
            className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-60"
          >
            {c.send}
          </button>
          {busy && (
            <button type="button" onClick={() => pending.current?.abort()} className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700">
              {c.stop}
            </button>
          )}
          {turns.length > 0 && !busy && (
            <button type="button" onClick={clear} className="text-sm underline">
              {c.clear}
            </button>
          )}
        </div>
        {error && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-400">
            {error}
          </p>
        )}
      </form>
      <p className="text-xs text-zinc-600 dark:text-zinc-400">
        {c.note} {c.stored}
      </p>
    </section>
  );
}

function Message({ turn }: { turn: Turn }) {
  const { t } = useI18n();
  const c = t.chat;
  if (turn.role === "user") {
    return (
      <div className="max-w-[85%] justify-self-end rounded-lg bg-amber-50 px-3 py-2 text-sm dark:bg-amber-950">
        <span className="sr-only">{c.you}: </span>
        <p className="whitespace-pre-line">{turn.content}</p>
      </div>
    );
  }
  const evidence = turn.evidence ?? [];
  return (
    <div className="max-w-[95%] rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800">
      <span className="sr-only">{c.astrologer}: </span>
      <p className="whitespace-pre-line leading-6">{turn.content}</p>
      {turn.narrator === "template" && <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">{c.offline}</p>}
      {evidence.length > 0 && (
        <details className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
          <summary className="cursor-pointer">{c.basedOn(evidence.length)}</summary>
          <ul className="mt-1 grid gap-1" lang="en">
            {evidence.map((e) => (
              <li key={e.id}>
                <span className="font-medium">{e.title}</span>
                {e.period ? ` (${e.period})` : ""}: {e.text}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
