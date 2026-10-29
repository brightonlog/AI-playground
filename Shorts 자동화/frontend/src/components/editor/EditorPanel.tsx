import { useEffect, useState } from "react";

import type { EditDoc, EditOp, SpeechLine } from "../../api/client";
import { OUTPUT_MAX_SEC, OUTPUT_MIN_SEC, TITLE_MAX } from "../../config";
import type { CutType } from "../../hooks/useEdit";
import NarrationRow from "./NarrationRow";
import SpeechRow from "./SpeechRow";
import SuggestionPanel from "./SuggestionPanel";
import TextField from "./TextField";

type Props = {
  doc: EditDoc;
  duration: number;
  busy: boolean;
  error: string;
  apply: (ops: EditOp[]) => void;
  suggest: (type: CutType) => void;
};

function findWord(doc: EditDoc, wordId: string | null) {
  for (const line of doc.lines) {
    if (line.kind !== "speech") continue;
    const word = line.words.find((w) => w.id === wordId);
    if (word) return word;
  }
  return null;
}

export default function EditorPanel({ doc, duration, busy, error, apply, suggest }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const suggested = new Set(doc.pending_suggestions.flatMap((s) => s.word_ids));
  const tooLong = duration > OUTPUT_MAX_SEC;
  const tooShort = duration < OUTPUT_MIN_SEC;

  // Delete / Backspace toggles the selected word, Escape clears the selection.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "INPUT") return;
      if (e.key === "Escape") setSelected(null);
      const word = findWord(doc, selected);
      if (word && (e.key === "Delete" || e.key === "Backspace")) {
        e.preventDefault();
        apply([{ op: word.deleted ? "restore_words" : "delete_words", word_ids: [word.id] }]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [doc, selected, apply]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white p-3">
        <span className="shrink-0 text-sm font-medium">제목</span>
        <TextField
          value={doc.title.text}
          maxLength={TITLE_MAX}
          className="flex-1"
          onSave={(text) => apply([{ op: "set_title", text, visible: doc.title.visible }])}
        />
        <label className="flex shrink-0 items-center gap-1 text-xs text-zinc-600">
          <input
            type="checkbox"
            checked={doc.title.visible}
            onChange={(e) => apply([{ op: "set_title", text: doc.title.text, visible: e.target.checked }])}
          />
          보이기
        </label>
      </div>

      <SuggestionPanel items={doc.pending_suggestions} busy={busy} apply={apply} suggest={suggest} />

      <div className="flex items-center gap-3 text-sm">
        <span className={`tabular-nums ${tooLong || tooShort ? "font-medium text-red-600" : "text-zinc-600"}`}>
          길이 {duration.toFixed(1)}초
        </span>
        <span className="text-xs text-zinc-400">
          단어를 누르고 Delete로 지우기 · 밑줄은 자동 교정된 단어 · 노란색은 추천 컷
        </span>
        <button
          className="ml-auto text-xs text-zinc-500 hover:text-zinc-900 hover:underline"
          onClick={() => apply([{ op: "restore_all" }])}
        >
          지운 것 모두 살리기
        </button>
        {busy && <span className="text-xs text-zinc-400">저장 중…</span>}
      </div>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="space-y-2">
        {doc.lines.map((line) =>
          line.kind === "narration" ? (
            <NarrationRow key={line.id} line={line} apply={apply} />
          ) : (
            <SpeechRow
              key={line.id}
              line={line as SpeechLine}
              selected={selected}
              suggested={suggested}
              onSelect={setSelected}
              apply={apply}
            />
          ),
        )}
      </div>
    </div>
  );
}
