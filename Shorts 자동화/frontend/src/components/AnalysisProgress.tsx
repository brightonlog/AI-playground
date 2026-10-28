import type { Analysis } from "../api/client";

const STAGES: Record<string, string> = {
  queued: "차례를 기다리는 중",
  fetching: "영상 정보·자막·오디오를 받는 중",
  transcribing: "자막이 없어 직접 받아쓰는 중",
  analyzing: "제품 소개 구간을 찾는 중",
};

type Props = {
  analysis: Analysis;
  live: { stage: string; progress: number } | null;
  onRetry: () => void;
};

export default function AnalysisProgress({ analysis, live, onRetry }: Props) {
  if (analysis.status === "failed") {
    const canRetry = analysis.retry_count < 3;
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="mb-1 font-semibold text-red-700">분석에 실패했어요</p>
        <p className="mb-4 text-sm text-red-700">{analysis.error?.message}</p>
        {canRetry && (
          <button onClick={onRetry} className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white">
            다시 시도 ({analysis.retry_count}/3)
          </button>
        )}
      </div>
    );
  }
  const stage = live?.stage ?? analysis.stage ?? "queued";
  const percent = Math.round((live?.progress ?? analysis.progress) * 100);
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <div className="mb-2 flex justify-between text-sm">
        <span>{STAGES[stage] ?? stage}</span>
        <span className="tabular-nums">{percent}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-zinc-100"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full bg-zinc-900 transition-all" style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-3 text-xs text-zinc-500">자막이 있는 영상은 보통 1분 안에 끝나요.</p>
    </div>
  );
}
