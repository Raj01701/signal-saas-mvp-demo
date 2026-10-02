"use client";

import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api/client";

interface Loaded<T> {
  data?: T;
  error?: string;
  loading: boolean;
}

/**
 * Load data for ``key`` (for example a serialised request) with ``load``; loads
 * again when the key changes. A null key loads nothing.
 */
export function useLoad<T>(
  key: string | null,
  load: () => Promise<{ data?: T; error?: unknown }>,
): Loaded<T> {
  const [state, setState] = useState<{ key: string | null; data?: T; error?: string }>({ key: null });
  useEffect(() => {
    if (key === null) return;
    let live = true;
    load().then(
      ({ data, error }) => {
        if (live) setState({ key, data, error: data === undefined ? errorMessage(error) : undefined });
      },
      () => {
        if (live) setState({ key, error: "The API could not be reached." });
      },
    );
    return () => {
      live = false;
    };
    // The key identifies the request; ``load`` is recreated on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  const current = state.key === key;
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : undefined,
    loading: key !== null && !current,
  };
}

/** Julian day (UT) to a calendar date string, YYYY-MM-DD. */
export function jdToDate(jd: number): string {
  return new Date((jd - 2440587.5) * 86_400_000).toISOString().slice(0, 10);
}
