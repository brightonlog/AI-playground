import { useParams } from "react-router";

import AnalysisProgress from "../components/AnalysisProgress";
import ScenePicker from "../components/ScenePicker";
import { useAnalysis } from "../hooks/useAnalysis";

const WARNINGS: Record<string, string> = {
  auto_captions: "자동 생성 자막이라 대사가 정확하지 않을 수 있어요.",
  llm_fallback: "제품 인식이 단순 규칙으로 대체됐어요. 추천 정확도가 낮을 수 있어요.",
  no_recommendations: "추천할 만한 제품 구간을 찾지 못했어요. 직접 구간을 골라 주세요.",
};

export default function AnalysisPage() {
  const { id = "" } = useParams();
  const { analysis, live, error, retry } = useAnalysis(id);

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
        <AnalysisProgress analysis={analysis} live={live} onRetry={retry} />
      )}
    </section>
  );
}
