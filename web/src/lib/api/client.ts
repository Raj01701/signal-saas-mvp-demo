/** Typed client for the Jyotish API, generated from its OpenAPI schema. */

import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];
export type Chart = Schemas["ChartResult"];
export type Body = Schemas["Body"];
export type Preset = Schemas["Preset"];

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = createClient<paths>({ baseUrl: API_URL });

/** The API's error message for a failed request. */
export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]) {
      return String((detail[0] as { msg: unknown }).msg);
    }
  }
  return "The request failed.";
}
