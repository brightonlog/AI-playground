import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin, { type Region } from "wavesurfer.js/plugins/regions";

import type { Waveform as WaveformData } from "../api/client";

type Props = {
  waveform: WaveformData;
  selection: { start: number; end: number } | null;
  currentTime: number;
  onSelect: (start: number, end: number) => void;
  onSeek: (sec: number) => void;
};

/** Whole-video waveform with a draggable selection and a playhead. Peaks only, no audio. */
export default function Waveform({ waveform, selection, currentTime, onSelect, onSeek }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const regionRef = useRef<Region | null>(null);
  const regionsRef = useRef<ReturnType<typeof RegionsPlugin.create> | null>(null);
  const addingRef = useRef(false);
  // Latest callbacks without re-creating wavesurfer on every render.
  const handlers = useRef({ onSelect, onSeek });
  useEffect(() => {
    handlers.current = { onSelect, onSeek };
  });

  useEffect(() => {
    if (!containerRef.current) return;
    const regions = RegionsPlugin.create();
    const ws = WaveSurfer.create({
      container: containerRef.current,
      peaks: [waveform.peaks],
      duration: waveform.duration_sec,
      height: 80,
      waveColor: "#a1a1aa",
      progressColor: "#a1a1aa",
      cursorWidth: 0,
      plugins: [regions],
    });
    ws.on("interaction", (t) => handlers.current.onSeek(t));
    regions.on("region-updated", (r) => handlers.current.onSelect(r.start, r.end));
    // Drag on empty space to draw a new selection.
    regions.enableDragSelection({ color: "rgba(24, 24, 27, 0.15)" });
    regions.on("region-created", (r) => {
      const previous = regionRef.current;
      regionRef.current = r;
      if (addingRef.current) return; // created by us from `selection`
      previous?.remove();
      handlers.current.onSelect(r.start, r.end);
    });
    regionsRef.current = regions;
    return () => {
      ws.destroy();
      regionRef.current = null;
      regionsRef.current = null;
    };
  }, [waveform]);

  useEffect(() => {
    const regions = regionsRef.current;
    if (!regions) return;
    if (!selection) {
      regionRef.current?.remove();
      regionRef.current = null;
    } else if (!regionRef.current) {
      addingRef.current = true;
      regions.addRegion({
        start: selection.start,
        end: selection.end,
        color: "rgba(24, 24, 27, 0.15)",
      });
      addingRef.current = false;
    } else {
      regionRef.current.setOptions({ start: selection.start, end: selection.end });
    }
  }, [selection]);

  const playhead = (currentTime / waveform.duration_sec) * 100;
  return (
    <div className="relative rounded-lg border border-zinc-200 bg-white px-1 py-2">
      <div ref={containerRef} />
      <div
        className="pointer-events-none absolute top-0 bottom-0 w-px bg-red-500"
        style={{ left: `${Math.min(100, Math.max(0, playhead))}%` }}
      />
    </div>
  );
}
