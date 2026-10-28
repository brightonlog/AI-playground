import { useCallback, useEffect, useState } from "react";

import { type Analysis, api, unwrap } from "../api/client";

type Live = { stage: string; progress: number };

const TERMINAL = ["ready", "failed"];

/** Analysis state, kept live over SSE while the job runs. */
export function useAnalysis(id: string) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [live, setLive] = useState<Live | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(() => {
    unwrap(api.GET("/api/v1/analyses/{analysis_id}", { params: { path: { analysis_id: id } } }))
      .then((a) => {
        setAnalysis(a);
        setLive({ stage: a.stage ?? "queued", progress: a.progress });
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);

  useEffect(reload, [reload]);

  const running = analysis !== null && !TERMINAL.includes(analysis.status);
  useEffect(() => {
    if (!running) return;
    const source = new EventSource(`/api/v1/analyses/${encodeURIComponent(id)}/events`);
    source.addEventListener("progress", (e) => setLive(JSON.parse((e as MessageEvent).data)));
    const finish = () => {
      source.close();
      reload();
    };
    source.addEventListener("done", finish);
    source.addEventListener("failed", finish);
    return () => source.close();
  }, [id, running, reload]);

  const retry = useCallback(async () => {
    try {
      setAnalysis(
        await unwrap(
          api.POST("/api/v1/analyses/{analysis_id}/retry", {
            params: { path: { analysis_id: id } },
          }),
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  return { analysis, live, error, retry };
}
