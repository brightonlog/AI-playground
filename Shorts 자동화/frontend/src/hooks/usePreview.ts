import { useCallback, useEffect, useState } from "react";

import { api, type Short, unwrap } from "../api/client";
import { PREVIEW_POLL_MS } from "../config";

/** Short state while its preview catches up with `editVersion` (checked every second). */
export function usePreview(initial: Short, editVersion: number | undefined) {
  const [short, setShort] = useState(initial);
  const refresh = useCallback(() => {
    unwrap(api.GET("/api/v1/shorts/{short_id}", { params: { path: { short_id: initial.id } } }))
      .then(setShort)
      .catch(() => undefined); // keep polling through a blip
  }, [initial.id]);

  // Each saved edit changes preview_status on the server; read it right away.
  useEffect(() => {
    if (editVersion !== undefined) refresh();
  }, [editVersion, refresh]);

  const status = short.preview_status;
  const rendering =
    status === "pending" ||
    status === "rendering" ||
    (editVersion !== undefined && short.preview_version < editVersion && status !== "failed");

  useEffect(() => {
    if (!rendering) return;
    const timer = setInterval(refresh, PREVIEW_POLL_MS);
    return () => clearInterval(timer);
  }, [rendering, refresh]);

  return { short, rendering };
}
