import type { EditOp, Suggestion } from "../../api/client";
import type { CutType } from "../../hooks/useEdit";

type Props = {
  items: Suggestion[];
  busy: boolean;
  apply: (ops: EditOp[]) => void;
  suggest: (type: CutType) => void;
};

const TYPES: { type: CutType; label: string }[] = [
  { type: "silence", label: "쉼 찾기" },
  { type: "filler", label: "군말 찾기" },
];

export default function SuggestionPanel({ items, busy, apply, suggest }: Props) {
  const btn = "rounded-lg border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-50 disabled:opacity-50";
  const applyIds = (ids: string[]) => apply([{ op: "apply_suggestions", suggestion_ids: ids }]);
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">AI 추천 컷</span>
        {TYPES.map((t) => (
          <button key={t.type} className={btn} disabled={busy} onClick={() => suggest(t.type)}>
            {t.label}
          </button>
        ))}
        {items.length > 0 && (
          <button
            className="ml-auto rounded-lg bg-zinc-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            disabled={busy}
            onClick={() => applyIds(items.map((s) => s.id))}
          >
            모두 적용 ({items.length})
          </button>
        )}
      </div>
      {items.length > 0 && (
        <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-sm">
          {items.map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-2 rounded bg-amber-50 px-2 py-1">
              <span>{s.reason}</span>
              <button className="text-xs text-zinc-600 hover:underline" disabled={busy} onClick={() => applyIds([s.id])}>
                적용
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
