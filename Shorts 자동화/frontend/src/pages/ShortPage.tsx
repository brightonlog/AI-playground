import { Link, useParams } from "react-router";

import JobProgress from "../components/JobProgress";
import { useJob } from "../hooks/useJob";
import { formatTime } from "../lib/time";

const STAGES: Record<string, string> = {
  queued: "차례를 기다리는 중",
  downloading: "선택한 구간 영상을 받는 중",
  preparing: "자막·크롭·제목·나레이션·미리보기를 만드는 중",
};

const WARNINGS: Record<string, string> = {
  llm_fallback: "제목·나레이션을 자동으로 만들지 못해 원본 영상 제목을 썼어요.",
  crop_fallback: "얼굴을 찾지 못해 화면 가운데로 잘랐어요.",
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
      {short.warnings.map((w) => (
        <p key={w} className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {WARNINGS[w] ?? w}
        </p>
      ))}
      {ready ? (
        <div className="flex flex-col items-center gap-3">
          {short.preview_status === "ready" ? (
            <video
              key={short.preview_version}
              src={`/api/v1/shorts/${short.id}/files/preview?v=${short.preview_version}`}
              controls
              playsInline
              className="aspect-[9/16] w-full max-w-[360px] rounded-xl bg-black"
            />
          ) : (
            <p className="text-zinc-500">미리보기를 준비하는 중…</p>
          )}
          <p className="text-xs text-zinc-500">미리보기는 저화질(540×960)이에요. 편집은 다음 단계에서 붙어요.</p>
        </div>
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
