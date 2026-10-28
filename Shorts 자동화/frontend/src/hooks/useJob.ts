import { useCallback, useEffect, useState } from "react";

import { type Analysis, api, type Short, unwrap } from "../api/client";

type JobTypes = { analyses: Analysis; shorts: Short };
type Kind = keyof JobTypes;
type Live = { stage: string; progress: number };

type Fetchers = {
  [K in Kind]: {
    get: (id: string) => Promise<JobTypes[K]>;
    retry: (id: string) => Promise<JobTypes[K]>;
    /** Statuses where the job stopped running (no SSE needed). */
    settled: string[];
  };
};

const FETCHERS: Fetchers = {
  analyses: {
    get: (id) => unwrap(api.GET("/api/v1/analyses/{analysis_id}", { params: { path: { analysis_id: id } } })),
    retry: (id) =>
      unwrap(api.POST("/api/v1/analyses/{analysis_id}/retry", { params: { path: { analysis_id: id } } })),
    settled: ["ready", "failed"],
  },
  shorts: {
    get: (id) => unwrap(api.GET("/api/v1/shorts/{short_id}", { params: { path: { short_id: id } } })),
    retry: (id) => unwrap(api.POST("/api/v1/shorts/{short_id}/retry", { params: { path: { short_id: id } } })),
    settled: ["editing", "done", "failed"],
  },
};

/** A job's state, kept live over SSE while it runs. */
export function useJob<K extends Kind>(kind: K, id: string) {
  const fetchers = FETCHERS[kind] as Fetchers[K];
  const [job, setJob] = useState<JobTypes[K] | null>(null);
  const [live, setLive] = useState<Live | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(() => {
    fetchers
      .get(id)
      .then((j) => {
        setJob(j);
        setLive({ stage: j.stage ?? "queued", progress: j.progress });
      })
      .catch((e: Error) => setError(e.message));
  }, [fetchers, id]);

  useEffect(reload, [reload]);

  const running = job !== null && !fetchers.settled.includes(job.status);
  useEffect(() => {
    if (!running) return;
    const source = new EventSource(`/api/v1/${kind}/${encodeURIComponent(id)}/events`);
    source.addEventListener("progress", (e) => setLive(JSON.parse((e as MessageEvent).data)));
    const finish = () => {
      source.close();
      reload();
    };
    source.addEventListener("done", finish);
    source.addEventListener("failed", finish);
    return () => source.close();
  }, [kind, id, running, reload]);

  const retry = useCallback(async () => {
    try {
      setJob(await fetchers.retry(id));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [fetchers, id]);

  return { job, live, error, retry };
}
