import { useCallback, useEffect, useState } from "react";

import { type Analysis, api, type Recommendation, type Sentence, unwrap, type Waveform as WaveformData } from "../api/client";
import { SHORT_MAX_SEC, SHORT_MIN_SEC } from "../config";
import { useYouTubePlayer } from "../hooks/useYouTubePlayer";
import { snapToSentences } from "../lib/snap";
import { formatTime } from "../lib/time";
import RecommendationList from "./RecommendationList";
import TranscriptList from "./TranscriptList";
import Waveform from "./Waveform";

type Selection = { start: number; end: number; rank: number | null };

function useSceneData(analysisId: string) {
  const [data, setData] = useState<{ recs: Recommendation[]; sentences: Sentence[]; waveform: WaveformData }>();
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

export default function ScenePicker({ analysis }: { analysis: Analysis }) {
  const { data, error } = useSceneData(analysis.id);
  const { containerRef, currentTime, seek } = useYouTubePlayer(analysis.video_id);
  const [picked, setSelection] = useState<Selection | null>(null);
  const [notice, setNotice] = useState("");

  // Until the user picks something, show the top recommendation.
  const top = data?.recs[0];
  const selection: Selection | null =
    picked ?? (top ? { start: top.start_sec, end: top.end_sec, rank: top.rank } : null);

  const pick = useCallback(
    (item: Recommendation) => {
      setSelection({ start: item.start_sec, end: item.end_sec, rank: item.rank });
      seek(item.start_sec, true);
    },
    [seek],
  );

  const select = useCallback(
    (start: number, end: number) => {
      // A hand-adjusted range snaps to sentence boundaries and is no longer a recommendation.
      setSelection({ ...snapToSentences(data?.sentences ?? [], start, end), rank: null });
    },
    [data],
  );

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-zinc-500">장면 정보를 불러오는 중…</p>;

  const duration = selection ? selection.end - selection.start : 0;
  const valid = selection !== null && duration >= SHORT_MIN_SEC && duration <= SHORT_MAX_SEC;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div ref={containerRef} className="aspect-video w-full overflow-hidden rounded-lg bg-black" />
        <RecommendationList items={data.recs} activeRank={selection?.rank ?? null} onPick={pick} />
      </div>
      <Waveform
        waveform={data.waveform}
        selection={selection}
        currentTime={currentTime}
        onSelect={select}
        onSeek={(t) => seek(t)}
      />
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-200 bg-white p-3">
        <div className="text-sm">
          {selection ? (
            <>
              <span className="tabular-nums">
                {formatTime(selection.start)} – {formatTime(selection.end)}
              </span>
              <span className={`ml-2 tabular-nums ${valid ? "text-zinc-500" : "text-red-600"}`}>
                {duration.toFixed(1)}초 {!valid && `(${SHORT_MIN_SEC}~${SHORT_MAX_SEC}초만 가능)`}
              </span>
            </>
          ) : (
            <span className="text-zinc-500">파형을 드래그하거나 추천을 눌러 구간을 고르세요</span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            disabled={!selection}
            onClick={() => selection && seek(selection.start, true)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50"
          >
            구간 재생
          </button>
          <button
            disabled={!valid}
            onClick={() =>
              setNotice(
                `선택: ${formatTime(selection!.start)}–${formatTime(selection!.end)}` +
                  (selection!.rank ? ` (추천 ${selection!.rank}번)` : " (직접 선택)") +
                  ". 쇼츠 생성은 다음 단계(M4)에서 연결돼요.",
              )
            }
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            이 구간으로 만들기
          </button>
        </div>
      </div>
      {notice && <p className="rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">{notice}</p>}
      <TranscriptList sentences={data.sentences} selection={selection} currentTime={currentTime} onSeek={(t) => seek(t)} />
    </div>
  );
}
