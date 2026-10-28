import { type FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { api, unwrap } from "../api/client";

export default function LinkPage() {
  const [params] = useSearchParams();
  const templateId = params.get("template") ?? "celeb_item";
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      // 202 = new analysis, 200 = an earlier analysis of the same video; both open it.
      const analysis = await unwrap(
        api.POST("/api/v1/analyses", { body: { url, template_id: templateId } }),
      );
      navigate(`/analyses/${analysis.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <section className="max-w-xl">
      <h1 className="mb-2 text-2xl font-bold">유튜브 링크를 넣어 주세요</h1>
      <p className="mb-6 text-sm text-zinc-600">제품을 소개하는 구간을 찾아 추천해 드려요.</p>
      <form onSubmit={submit} className="flex gap-2">
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 focus:border-zinc-900 focus:outline-none"
        />
        <button
          disabled={busy}
          className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          {busy ? "확인 중…" : "분석 시작"}
        </button>
      </form>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </section>
  );
}
