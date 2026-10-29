import { useCallback, useEffect, useRef, useState } from "react";

import { api, type EditDoc, type EditOp, unwrap } from "../api/client";
import { SILENCE_GAP_SEC } from "../config";

type State = { doc: EditDoc; duration: number };
export type CutType = "silence" | "filler";

const byId = (shortId: string) => ({ params: { path: { short_id: shortId } } });

/** A short's edit state. Changes go out one at a time, each on top of the latest version. */
export function useEdit(shortId: string) {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const queue = useRef(Promise.resolve());

  const load = useCallback(async () => {
    const out = await unwrap(api.GET("/api/v1/shorts/{short_id}/edit", byId(shortId)));
    setState({ doc: out.edit, duration: out.duration_sec });
    return out.edit.version;
  }, [shortId]);

  useEffect(() => {
    unwrap(api.GET("/api/v1/shorts/{short_id}/edit", byId(shortId)))
      .then((out) => setState({ doc: out.edit, duration: out.duration_sec }))
      .catch((e: Error) => setError(e.message));
  }, [shortId]);

  // Ops name what to change ("delete w3"), so they apply cleanly on the newest version.
  // Writes are chained so a quick second click never reuses a stale base_version.
  const run = useCallback(
    (write: (version: number) => Promise<unknown>) => {
      const next = queue.current.then(async () => {
        setBusy(true);
        setError("");
        try {
          await write(await load());
        } catch (e) {
          setError((e as Error).message);
        } finally {
          await load().catch(() => undefined);
          setBusy(false);
        }
      });
      queue.current = next;
      return next;
    },
    [load],
  );

  const apply = useCallback(
    (ops: EditOp[]) =>
      run((version) =>
        unwrap(
          api.PATCH("/api/v1/shorts/{short_id}/edit", {
            ...byId(shortId),
            body: { base_version: version, ops },
          }),
        ),
      ),
    [run, shortId],
  );

  const suggest = useCallback(
    (type: CutType) =>
      run(() =>
        unwrap(
          api.POST("/api/v1/shorts/{short_id}/cut-suggestions", {
            ...byId(shortId),
            body: type === "silence" ? { type, min_gap_sec: SILENCE_GAP_SEC } : { type },
          }),
        ),
      ),
    [run, shortId],
  );

  return { doc: state?.doc ?? null, duration: state?.duration ?? 0, error, busy, apply, suggest };
}
