import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

import { api, type Template, unwrap } from "../api/client";

export default function TemplatePage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    unwrap(api.GET("/api/v1/templates"))
      .then(setTemplates)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <section>
      <h1 className="mb-6 text-2xl font-bold">어떤 쇼츠를 만들까요?</h1>
      {error && <p className="text-red-600">{error}</p>}
      <div className="grid gap-4 sm:grid-cols-3">
        {templates.map((t) => (
          <button
            key={t.id}
            disabled={!t.available}
            onClick={() => navigate(`/new?template=${encodeURIComponent(t.id)}`)}
            className="rounded-xl border border-zinc-200 bg-white p-5 text-left shadow-sm transition hover:border-zinc-900 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-zinc-200"
          >
            <div className="mb-1 flex items-center gap-2 font-semibold">
              {t.name}
              {!t.available && (
                <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-500">준비 중</span>
              )}
            </div>
            <p className="text-sm text-zinc-600">{t.description}</p>
          </button>
        ))}
      </div>
    </section>
  );
}
