import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Analysis = components["schemas"]["AnalysisOut"];
export type Short = components["schemas"]["ShortOut"];
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
  let result: Result<T>;
  try {
    result = await request;
  } catch (e) {
    // An HTML page instead of JSON: the dev server is not forwarding /api to the backend.
    if (e instanceof SyntaxError) {
      throw new ApiError("bad_response", "서버 응답을 읽지 못했어요. 백엔드와 개발 서버를 다시 켜 주세요.");
    }
    throw e;
  }
  const { data, error, response } = result;
  if (data !== undefined) return data;
  const body = (error ?? {}) as { error?: string; detail?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : `요청 실패 (${response.status})`;
  throw new ApiError(body.error ?? "http_error", detail);
}

export type EditDoc = components["schemas"]["EditDoc"];
export type SpeechLine = components["schemas"]["SpeechLine"];
export type NarrationLine = components["schemas"]["NarrationLine"];
export type Word = components["schemas"]["Word"];
export type Suggestion = components["schemas"]["Suggestion"];
export type EditOp = components["schemas"]["EditPatch"]["ops"][number];
