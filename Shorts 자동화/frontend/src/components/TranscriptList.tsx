import { useEffect, useRef } from "react";

import type { Sentence } from "../api/client";
import { formatTime } from "../lib/time";

type Props = {
  sentences: Sentence[];
  selection: { start: number; end: number } | null;
  currentTime: number;
  onSeek: (sec: number) => void;
};

export default function TranscriptList({ sentences, selection, currentTime, onSeek }: Props) {
  const listRef = useRef<HTMLOListElement>(null);
  const firstSelected = sentences.find((s) => selection && s.end_sec > selection.start);

  // Bring the selected section into view when the selection moves.
  useEffect(() => {
    if (!firstSelected) return;
    listRef.current
      ?.querySelector(`[data-id="${firstSelected.id}"]`)
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [firstSelected]);

  return (
    <ol ref={listRef} className="max-h-96 space-y-0.5 overflow-y-auto rounded-lg border border-zinc-200 bg-white p-2">
      {sentences.map((s) => {
        const selected = selection && s.start_sec < selection.end && s.end_sec > selection.start;
        const playing = currentTime >= s.start_sec && currentTime < s.end_sec;
        return (
          <li key={s.id} data-id={s.id}>
            <button
              onClick={() => onSeek(s.start_sec)}
              className={`flex w-full gap-3 rounded px-2 py-1 text-left text-sm ${
                selected ? "bg-zinc-100" : ""
              } ${playing ? "font-semibold" : ""} hover:bg-zinc-50`}
            >
              <span className="w-14 shrink-0 text-xs tabular-nums text-zinc-400">{formatTime(s.start_sec)}</span>
              <span>{s.text}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
