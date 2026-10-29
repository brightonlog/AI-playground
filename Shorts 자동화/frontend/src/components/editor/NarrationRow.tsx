import type { EditOp, NarrationLine } from "../../api/client";
import { NARRATION_MAX } from "../../config";
import TextField from "./TextField";

type Props = { line: NarrationLine; apply: (ops: EditOp[]) => void };

export default function NarrationRow({ line, apply }: Props) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2">
      <span className="shrink-0 text-xs font-medium text-violet-700">나레이션 {line.audio_sec.toFixed(1)}초</span>
      <TextField
        value={line.text}
        maxLength={NARRATION_MAX}
        className="flex-1 bg-white"
        onSave={(text) => text && apply([{ op: "set_narration", line_id: line.id, text }])}
      />
      <button
        className="text-xs text-zinc-500 hover:text-red-600"
        onClick={() => apply([{ op: "delete_narration", line_id: line.id }])}
      >
        삭제
      </button>
    </div>
  );
}
