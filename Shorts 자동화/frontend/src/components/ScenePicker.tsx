import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router";

import {
  type Analysis,
  api,
  type Recommendation,
  type Sentence,
  unwrap,
  type Waveform as WaveformData,
} from "../api/client";
import { SNAP_TOLERANCE_SEC, ZOOM_LEVELS } from "../config";
import { useYouTubePlayer } from "../hooks/useYouTubePlayer";
import { snapToSentences } from "../lib/snap";
import { formatTime } from "../lib/time";
import RecommendationList from "./RecommendationList";
import SelectionBar from "./SelectionBar";
import TranscriptList from "./TranscriptList";
import Waveform from "./Waveform";

type Selection = { start: number; end: number; rank: number | null };
type SceneData = { recs: Recommendation[]; sentences: Sentence[]; waveform: WaveformData };

const MIN_GAP_SEC = 1; // nudging never lets the edges cross
const END_PREVIEW_SEC = 3; // nudging the end plays the last few seconds

function useSceneData(analysisId: string) {
  const [data, setData] = useState<SceneData>();
  const [error, setError] = useState("");
  useEffect(() => {
    const path = { params: { path: { analysis_id: analysisId } } };
    Promise.all([
      unwrap(api.GET("/api/v1/analyses/{analysis_id}/recommendations", path)),
      unwrap(api.GET("/api/v1/analyses/{analysis_id}/transcript", path)),
      unwrap(api.GET("/api/v1/analyses/{analysis_id}/waveform", path)),
    ])
      .then(([recs, transcript, waveform]) =>
        setData({ recs: recs.items, sentences: transcript.sentences, waveform }),
      )
      .catch((e: Error) => setError(e.message));
  }, [analysisId]);
  return { data, error };
}

const round1 = (t: number) => Math.round(t * 10) / 10;

export default function ScenePicker({ analysis }: { analysis: Analysis }) {
  const { data, error } = useSceneData(analysis.id);
  const { containerRef, currentTime, seek } = useYouTubePlayer(analysis.video_id);
  const [picked, setPicked] = useState<Selection | null>(null);
  const [snap, setSnap] = useState(true);
  const [zoomIndex, setZoomIndex] = useState(0);
  const [focusTime, setFocusTime] = useState(0);
  const [notice, setNotice] = useState("");
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  // Until the user picks something, show the top recommendation.
  const top = data?.recs[0];
  const selection: Selection | null =
    picked ?? (top ? { start: top.start_sec, end: top.end_sec, rank: top.rank } : null);
  const videoEnd = data?.waveform.duration_sec ?? 0;

  const pick = useCallback(
    (item: Recommendation) => {
      setPicked({ start: item.start_sec, end: item.end_sec, rank: item.rank });
      setFocusTime(item.start_sec);
      seek(item.start_sec, true);
    },
    [seek],
  );

  // A hand-adjusted range is no longer a recommendation.
  const select = useCallback(
    (start: number, end: number) => {
      const range = snap
        ? snapToSentences(data?.sentences ?? [], start, end, SNAP_TOLERANCE_SEC)
        : { start, end };
      setPicked({ start: round1(range.start), end: round1(range.end), rank: null });
    },
    [data, snap],
  );

  const nudge = (edge: "start" | "end", delta: number) => {
    if (!selection) return;
    let { start, end } = selection;
    if (edge === "start") start = round1(Math.min(Math.max(0, start + delta), end - MIN_GAP_SEC));
    else end = round1(Math.max(Math.min(videoEnd, end + delta), start + MIN_GAP_SEC));
    setPicked({ start, end, rank: null });
    seek(edge === "start" ? start : Math.max(start, end - END_PREVIEW_SEC), true);
  };

  const create = async () => {
    if (!selection || creating) return;
    setCreating(true);
    setNotice("");
    try {
      const short = await unwrap(
        api.POST("/api/v1/shorts", {
          body: {
            analysis_id: analysis.id,
            template_id: analysis.template_id,
            start_sec: selection.start,
            end_sec: selection.end,
            recommendation_rank: selection.rank,
          },
        }),
      );
      navigate(`/shorts/${short.id}`);
    } catch (e) {
      setNotice((e as Error).message);
      setCreating(false);
    }
  };

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-zinc-500">장면 정보를 불러오는 중…</p>;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div ref={containerRef} className="aspect-video w-full overflow-hidden rounded-lg bg-black" />
        <RecommendationList items={data.recs} activeRank={selection?.rank ?? null} onPick={pick} />
      </div>
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <label className="flex items-center gap-2">
            확대
            <input
              type="range"
              min={0}
              max={ZOOM_LEVELS.length - 1}
              value={zoomIndex}
              onChange={(e) => {
                setZoomIndex(Number(e.target.value));
                if (selection) setFocusTime(selection.start);
              }}
            />
          </label>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={snap} onChange={(e) => setSnap(e.target.checked)} />
            문장 경계에 맞추기
          </label>
          <span className="text-xs tabular-nums text-zinc-500">현재 {formatTime(currentTime)}</span>
        </div>
        <Waveform
          waveform={data.waveform}
          selection={selection}
          currentTime={currentTime}
          zoom={ZOOM_LEVELS[zoomIndex]}
          focusTime={focusTime}
          onSelect={select}
          onSeek={(t) => seek(t)}
        />
      </div>
      <SelectionBar
        selection={selection}
        onNudge={nudge}
        onPlay={() => selection && seek(selection.start, true)}
        onCreate={create}
        creating={creating}
      />
      {notice && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{notice}</p>}
      <TranscriptList
        sentences={data.sentences}
        selection={selection}
        currentTime={currentTime}
        onSeek={(t) => seek(t)}
      />
    </div>
  );
}
