import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin, { type Region } from "wavesurfer.js/plugins/regions";

import type { Waveform as WaveformData } from "../api/client";

type Props = {
  waveform: WaveformData;
  selection: { start: number; end: number } | null;
  currentTime: number;
  /** Pixels per second; 0 fits the whole video in the width. */
  zoom: number;
  /** Scroll so this time is in view whenever it changes. */
  focusTime: number;
  onSelect: (start: number, end: number) => void;
  onSeek: (sec: number) => void;
};

const SELECTION_COLOR = "rgba(24, 24, 27, 0.15)";
const PLAYHEAD_ID = "playhead";
const FOCUS_LEAD_SEC = 2; // show a little before the focused time

function applyView(ws: WaveSurfer | null, view: { zoom: number; focusTime: number }) {
  ws?.zoom(view.zoom);
  ws?.setScrollTime(Math.max(0, view.focusTime - FOCUS_LEAD_SEC));
}

/** Video waveform (peaks only, no audio) with a draggable selection and a playhead marker. */
export default function Waveform(props: Props) {
  const { waveform, selection, currentTime, zoom, focusTime } = props;
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);
  const regionsRef = useRef<ReturnType<typeof RegionsPlugin.create> | null>(null);
  const selectionRef = useRef<Region | null>(null);
  const playheadRef = useRef<Region | null>(null);
  const addingRef = useRef(false);
  const decodedRef = useRef(false);
  const draggingRef = useRef(false);
  const view = useRef({ zoom, focusTime });
  // Latest callbacks without re-creating wavesurfer on every render.
  const handlers = useRef({ onSelect: props.onSelect, onSeek: props.onSeek });
  useEffect(() => {
    handlers.current = { onSelect: props.onSelect, onSeek: props.onSeek };
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
      autoScroll: false,
      plugins: [regions],
    });
    ws.on("interaction", (t) => handlers.current.onSeek(t));
    // While a handle is held, re-renders (the playhead ticks 4x a second) must not reset it.
    regions.on("region-update", (r) => {
      if (r.id !== PLAYHEAD_ID) draggingRef.current = true;
    });
    regions.on("region-updated", (r) => {
      if (r.id === PLAYHEAD_ID) return;
      draggingRef.current = false;
      handlers.current.onSelect(r.start, r.end);
    });
    // Drag on empty space to draw a new selection.
    regions.enableDragSelection({ color: SELECTION_COLOR });
    regions.on("region-created", (r) => {
      if (addingRef.current || r.id === PLAYHEAD_ID) return; // created by us
      selectionRef.current?.remove();
      r.setOptions({ drag: false });
      selectionRef.current = r;
      handlers.current.onSelect(r.start, r.end);
    });
    ws.on("decode", () => {
      decodedRef.current = true;
      applyView(ws, view.current);
    });
    wsRef.current = ws;
    regionsRef.current = regions;
    return () => {
      ws.destroy();
      decodedRef.current = false;
      wsRef.current = regionsRef.current = selectionRef.current = playheadRef.current = null;
    };
  }, [waveform]);

  const add = (params: Parameters<ReturnType<typeof RegionsPlugin.create>["addRegion"]>[0]) => {
    addingRef.current = true;
    const region = regionsRef.current!.addRegion(params);
    addingRef.current = false;
    return region;
  };

  const start = selection?.start;
  const end = selection?.end;
  useEffect(() => {
    if (!regionsRef.current || draggingRef.current) return;
    const region = selectionRef.current;
    if (start === undefined || end === undefined) {
      region?.remove();
      selectionRef.current = null;
    } else if (!region) {
      // Only the two edge handles move it; the body stays put so it can't be nudged by accident.
      selectionRef.current = add({ start, end, color: SELECTION_COLOR, drag: false, resize: true });
    } else if (region.start !== start || region.end !== end) {
      region.setOptions({ start, end });
    }
  }, [start, end]);

  useEffect(() => {
    if (!regionsRef.current) return;
    if (!playheadRef.current) {
      playheadRef.current = add({
        id: PLAYHEAD_ID, start: currentTime, color: "#ef4444", drag: false, resize: false,
      }); // prettier-ignore
    } else {
      playheadRef.current.setOptions({ start: currentTime });
    }
  }, [currentTime]);

  // zoom() throws until the peaks finish loading ("decode"), so apply view changes only after it.
  useEffect(() => {
    view.current = { zoom, focusTime };
    if (decodedRef.current) applyView(wsRef.current, view.current);
  }, [zoom, focusTime]);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-1 py-2">
      <div ref={containerRef} className="waveform" />
    </div>
  );
}
