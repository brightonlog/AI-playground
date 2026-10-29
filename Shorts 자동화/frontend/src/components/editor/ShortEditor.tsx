import type { Short } from "../../api/client";
import { useEdit } from "../../hooks/useEdit";
import { usePreview } from "../../hooks/usePreview";
import EditorPanel from "./EditorPanel";

function Preview({ short, rendering }: { short: Short; rendering: boolean }) {
  const hasVideo = short.preview_version > 0;
  return (
    <div className="space-y-2 lg:sticky lg:top-4">
      <div className="relative">
        {hasVideo ? (
          <video
            key={short.preview_version}
            src={`/api/v1/shorts/${short.id}/files/preview?v=${short.preview_version}`}
            controls
            playsInline
            className="aspect-[9/16] w-full rounded-xl bg-black"
          />
        ) : (
          <div className="aspect-[9/16] w-full rounded-xl bg-zinc-200" />
        )}
        {rendering && (
          <span className="absolute left-2 top-2 rounded bg-black/70 px-2 py-1 text-xs text-white">
            새 미리보기 만드는 중…
          </span>
        )}
      </div>
      {short.preview_status === "failed" && (
        <p className="text-xs text-red-600">미리보기를 만들지 못했어요. 다시 편집하면 새로 만들어요.</p>
      )}
      <p className="text-xs text-zinc-500">저화질(540×960) 미리보기예요.</p>
    </div>
  );
}

/** Preview on the left, script editor on the right. */
export default function ShortEditor({ initial }: { initial: Short }) {
  const edit = useEdit(initial.id);
  const { short, rendering } = usePreview(initial, edit.doc?.version);
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[320px_1fr]">
      <Preview short={short} rendering={rendering} />
      {edit.doc ? (
        <EditorPanel {...edit} doc={edit.doc} />
      ) : (
        <p className={edit.error ? "text-red-600" : "text-zinc-500"}>{edit.error || "편집 내용을 불러오는 중…"}</p>
      )}
    </div>
  );
}
