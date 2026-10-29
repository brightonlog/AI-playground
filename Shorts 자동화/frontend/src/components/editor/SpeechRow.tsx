import { useState } from "react";

import type { EditOp, SpeechLine, Word } from "../../api/client";
import { NARRATION_MAX, WORD_MAX } from "../../config";
import TextField from "./TextField";

type Props = {
  line: SpeechLine;
  /** Neighboring speech lines, for moving an edge word across. */
  prevId: string | null;
  hasNext: boolean;
  selected: string | null;
  suggested: Set<string>;
  onSelect: (wordId: string | null) => void;
  apply: (ops: EditOp[]) => void;
};

type Mode = "none" | "word" | "display" | "narration";

function chipClass(w: Word, line: SpeechLine, selected: boolean, suggested: boolean) {
  const gone = w.deleted || line.deleted;
  return [
    "rounded px-1 py-0.5 cursor-pointer select-none",
    gone ? "text-zinc-400 line-through" : "text-zinc-900",
    w.raw_text ? "underline decoration-sky-500 decoration-2 underline-offset-4" : "",
    suggested && !gone ? "bg-amber-100" : "",
    selected ? "ring-2 ring-zinc-900" : "hover:bg-zinc-100",
  ].join(" ");
}

type ToolProps = Pick<Props, "line" | "prevId" | "hasNext" | "apply"> & { word: Word; onEdit: () => void };

/** Ops that move an edge word to the neighboring line: join both, then split again. */
function moveOps(word: Word, line: SpeechLine, prevId: string | null): EditOp[] {
  const index = line.words.findIndex((w) => w.id === word.id);
  if (index === 0 && prevId) {
    const after = line.words[1];
    return after
      ? [{ op: "join_lines", line_id: prevId }, { op: "split_line", line_id: prevId, word_id: after.id }]
      : [{ op: "join_lines", line_id: prevId }];
  }
  return [{ op: "join_lines", line_id: line.id }, { op: "split_line", line_id: line.id, word_id: word.id }];
}

function WordTools({ word, line, prevId, hasNext, apply, onEdit }: ToolProps) {
  const btn = "rounded border border-zinc-300 px-2 py-0.5 text-xs hover:bg-zinc-50";
  const first = line.words[0]?.id === word.id;
  const last = line.words[line.words.length - 1]?.id === word.id;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <button
        className={btn}
        onClick={() => apply([{ op: word.deleted ? "restore_words" : "delete_words", word_ids: [word.id] }])}
      >
        {word.deleted ? "살리기" : "지우기"}
      </button>
      <button className={btn} onClick={onEdit}>
        글자 고치기
      </button>
      {word.raw_text && (
        <button
          className={btn}
          title={`받아쓰기 원문: ${word.raw_text}`}
          onClick={() => apply([{ op: "set_word_text", word_id: word.id, text: word.raw_text ?? "" }])}
        >
          원문 '{word.raw_text}'로
        </button>
      )}
      {!first && (
        <button className={btn} onClick={() => apply([{ op: "split_line", line_id: line.id, word_id: word.id }])}>
          여기서 문장 나누기
        </button>
      )}
      {first && prevId && (
        <button className={btn} onClick={() => apply(moveOps(word, line, prevId))}>
          ↑ 앞 문장으로 보내기
        </button>
      )}
      {last && hasNext && line.words.length > 1 && (
        <button className={btn} onClick={() => apply(moveOps(word, line, null))}>
          ↓ 다음 문장으로 보내기
        </button>
      )}
    </div>
  );
}

export default function SpeechRow({ line, prevId, hasNext, selected, suggested, onSelect, apply }: Props) {
  const [mode, setMode] = useState<Mode>("none");
  const picked = line.words.find((w) => w.id === selected) ?? null;
  const link = "text-xs text-zinc-500 hover:text-zinc-900 hover:underline";
  return (
    <div className={`rounded-lg border p-3 ${line.deleted ? "border-dashed border-zinc-300 bg-zinc-50" : "border-zinc-200 bg-white"}`}>
      <div className="flex flex-wrap gap-0.5 text-[15px] leading-7">
        {line.words.map((w) =>
          mode === "word" && w.id === selected ? (
            <TextField
              key={w.id}
              value={w.text}
              maxLength={WORD_MAX}
              autoFocus
              className="w-28"
              onSave={(text) => {
                if (text) apply([{ op: "set_word_text", word_id: w.id, text }]);
                setMode("none");
              }}
              onCancel={() => setMode("none")}
            />
          ) : (
            <span
              key={w.id}
              title={w.raw_text ? `받아쓰기 원문: ${w.raw_text}` : undefined}
              className={chipClass(w, line, w.id === selected, suggested.has(w.id))}
              onClick={() => onSelect(w.id === selected ? null : w.id)}
            >
              {w.text}
            </span>
          ),
        )}
      </div>
      {line.display_text && mode !== "display" && (
        <p className="mt-1 text-xs text-sky-700">화면 문구: {line.display_text}</p>
      )}
      {picked && mode === "none" && (
        <div className="mt-2">
          <WordTools
            word={picked}
            line={line}
            prevId={prevId}
            hasNext={hasNext}
            apply={apply}
            onEdit={() => setMode("word")}
          />
        </div>
      )}
      {mode === "display" && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-zinc-500">화면 문구</span>
          <TextField
            value={line.display_text ?? line.text}
            maxLength={100}
            autoFocus
            className="flex-1"
            onSave={(text) => {
              apply([{ op: "set_display_text", line_id: line.id, text: text === line.text ? null : text }]);
              setMode("none");
            }}
            onCancel={() => setMode("none")}
          />
        </div>
      )}
      {mode === "narration" && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-zinc-500">이 문장 앞 나레이션</span>
          <TextField
            value=""
            maxLength={NARRATION_MAX}
            autoFocus
            className="flex-1"
            onSave={(text) => {
              if (text) apply([{ op: "add_narration", anchor_line_id: line.id, text }]);
              setMode("none");
            }}
            onCancel={() => setMode("none")}
          />
        </div>
      )}
      <div className="mt-2 flex gap-3">
        <button
          className={link}
          onClick={() => apply([{ op: line.deleted ? "restore_line" : "delete_line", line_id: line.id }])}
        >
          {line.deleted ? "문장 살리기" : "문장 지우기"}
        </button>
        <button className={link} onClick={() => setMode("display")}>
          화면 문구 고치기
        </button>
        <button className={link} onClick={() => setMode("narration")}>
          나레이션 추가
        </button>
      </div>
    </div>
  );
}
