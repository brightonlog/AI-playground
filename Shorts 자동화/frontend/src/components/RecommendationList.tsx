import type { Recommendation } from "../api/client";
import { formatTime } from "../lib/time";

type Props = {
  items: Recommendation[];
  activeRank: number | null;
  onPick: (item: Recommendation) => void;
};

export default function RecommendationList({ items, activeRank, onPick }: Props) {
  if (items.length === 0) {
    return <p className="text-sm text-zinc-500">추천 구간이 없어요. 파형을 드래그해 직접 골라 주세요.</p>;
  }
  return (
    <ol className="space-y-2">
      {items.map((item) => {
        const product = item.products[0];
        return (
          <li key={item.rank}>
            <button
              onClick={() => onPick(item)}
              aria-pressed={activeRank === item.rank}
              className={`w-full rounded-lg border p-3 text-left transition ${
                activeRank === item.rank
                  ? "border-zinc-900 bg-zinc-900 text-white"
                  : "border-zinc-200 bg-white hover:border-zinc-400"
              }`}
            >
              <div className="mb-1 flex items-baseline justify-between gap-2">
                <span className="font-semibold">
                  {item.rank}. {product ? [product.brand, product.product].filter(Boolean).join(" ") : "제품"}
                </span>
                <span className="shrink-0 text-xs tabular-nums opacity-70">
                  {formatTime(item.start_sec)}–{formatTime(item.end_sec)} · {Math.round(item.duration_sec)}초
                </span>
              </div>
              <div className="mb-1 flex flex-wrap gap-1">
                {item.tag_labels.map((label) => (
                  <span key={label} className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-700">
                    {label}
                  </span>
                ))}
              </div>
              <p className="line-clamp-2 text-sm opacity-80">{item.preview}</p>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
