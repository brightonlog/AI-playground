import { NUDGE_SEC, SHORT_MAX_SEC, SHORT_MIN_SEC } from "../config";
import { formatTime } from "../lib/time";

type Selection = { start: number; end: number; rank: number | null };
type Edge = "start" | "end";

type Props = {
  selection: Selection | null;
  onNudge: (edge: Edge, delta: number) => void;
  onPlay: () => void;
  onCreate: () => void;
};

function Nudge({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded border border-zinc-300 px-1.5 py-0.5 text-xs tabular-nums hover:bg-zinc-50"
    >
      {label}
    </button>
  );
}

function EdgeControl({ title, value, onNudge }: { title: string; value: number; onNudge: (d: number) => void }) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-xs text-zinc-500">{title}</span>
      <Nudge label={`−${NUDGE_SEC}`} onClick={() => onNudge(-NUDGE_SEC)} />
      <span className="w-14 text-center text-sm tabular-nums">{formatTime(value)}</span>
      <Nudge label={`+${NUDGE_SEC}`} onClick={() => onNudge(NUDGE_SEC)} />
    </div>
  );
}

export default function SelectionBar({ selection, onNudge, onPlay, onCreate }: Props) {
  if (!selection) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-3 text-sm text-zinc-500">
        파형을 드래그하거나 추천을 눌러 구간을 고르세요
      </div>
    );
  }
  const duration = selection.end - selection.start;
  const valid = duration >= SHORT_MIN_SEC && duration <= SHORT_MAX_SEC;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-4">
        <EdgeControl title="시작" value={selection.start} onNudge={(d) => onNudge("start", d)} />
        <EdgeControl title="끝" value={selection.end} onNudge={(d) => onNudge("end", d)} />
        <span className={`text-sm tabular-nums ${valid ? "text-zinc-500" : "text-red-600"}`}>
          {duration.toFixed(1)}초 {!valid && `(${SHORT_MIN_SEC}~${SHORT_MAX_SEC}초만 가능)`}
        </span>
      </div>
      <div className="flex gap-2">
        <button onClick={onPlay} className="rounded-lg border border-zinc-300 px-3 py-2 text-sm">
          구간 재생
        </button>
        <button
          disabled={!valid}
          onClick={onCreate}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          이 구간으로 만들기
        </button>
      </div>
    </div>
  );
}
