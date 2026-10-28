import { Link, useParams } from "react-router";

import JobProgress from "../components/JobProgress";
import { useJob } from "../hooks/useJob";
import { formatTime } from "../lib/time";

const STAGES: Record<string, string> = {
  queued: "차례를 기다리는 중",
  downloading: "선택한 구간 영상을 받는 중",
  preparing: "자막·크롭·제목·나레이션을 준비하는 중",
};

export default function ShortPage() {
  const { id = "" } = useParams();
  const { job: short, live, error, retry } = useJob("shorts", id);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!short) return <p className="text-zinc-500">불러오는 중…</p>;

  const ready = short.status === "editing" || short.status === "done";
  return (
    <section className="space-y-4">
      <div>
        <Link to={`/analyses/${short.analysis_id}`} className="text-sm text-zinc-500 hover:underline">
          ← 장면 다시 고르기
        </Link>
        <h1 className="mt-1 text-xl font-bold">쇼츠 초안</h1>
        <p className="text-sm text-zinc-500 tabular-nums">
          원본 {formatTime(short.start_sec)}–{formatTime(short.end_sec)} ·{" "}
          {(short.end_sec - short.start_sec).toFixed(1)}초
        </p>
      </div>
      {ready ? (
        <p className="rounded-xl border border-zinc-200 bg-white p-5 text-zinc-600">
          구간 영상을 받았어요. 자막·크롭·나레이션과 미리보기는 다음 단계(M4-b·c)에서 붙어요.
        </p>
      ) : (
        <JobProgress
          job={short}
          live={live}
          stages={STAGES}
          failTitle="쇼츠 초안을 만들지 못했어요"
          onRetry={retry}
        />
      )}
    </section>
  );
}
