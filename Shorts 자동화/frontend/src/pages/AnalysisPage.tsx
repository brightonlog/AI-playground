import { useParams } from "react-router";

import JobProgress from "../components/JobProgress";
import ScenePicker from "../components/ScenePicker";
import { useJob } from "../hooks/useJob";

const STAGES: Record<string, string> = {
  queued: "차례를 기다리는 중",
  fetching: "영상 정보·자막·오디오를 받는 중",
  transcribing: "자막이 없어 직접 받아쓰는 중",
  analyzing: "제품 소개 구간을 찾는 중",
};

const WARNINGS: Record<string, string> = {
  auto_captions: "자동 생성 자막이라 대사가 정확하지 않을 수 있어요.",
  llm_fallback: "제품 인식이 단순 규칙으로 대체됐어요. 추천 정확도가 낮을 수 있어요.",
  no_recommendations: "추천할 만한 제품 구간을 찾지 못했어요. 직접 구간을 골라 주세요.",
};

export default function AnalysisPage() {
  const { id = "" } = useParams();
  const { job: analysis, live, error, retry } = useJob("analyses", id);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!analysis) return <p className="text-zinc-500">불러오는 중…</p>;

  return (
    <section>
      <h1 className="mb-1 text-xl font-bold">{String(analysis.source.title ?? "")}</h1>
      <p className="mb-6 text-sm text-zinc-500">{String(analysis.source.channel ?? "")}</p>
      {analysis.warnings.map((w) => (
        <p key={w} className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {WARNINGS[w] ?? w}
        </p>
      ))}
      {analysis.status === "ready" ? (
        <ScenePicker analysis={analysis} />
      ) : (
        <JobProgress
          job={analysis}
          live={live}
          stages={STAGES}
          failTitle="분석에 실패했어요"
          hint="자막이 있는 영상은 보통 1분 안에 끝나요."
          onRetry={retry}
        />
      )}
    </section>
  );
}
