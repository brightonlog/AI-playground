import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Analysis = components["schemas"]["AnalysisOut"];
export type Template = components["schemas"]["Template"];
export type Recommendation = components["schemas"]["Recommendation"];
export type Sentence = components["schemas"]["Sentence"];
export type Waveform = components["schemas"]["WaveformOut"];

export const api = createClient<paths>({ baseUrl: "" });

/** Backend error body: {"error": code, "detail": human-readable message}. */
export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

type Result<T> = { data?: T; error?: unknown; response: Response };

export async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await request;
  if (data !== undefined) return data;
  const body = (error ?? {}) as { error?: string; detail?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : `요청 실패 (${response.status})`;
  throw new ApiError(body.error ?? "http_error", detail);
}
