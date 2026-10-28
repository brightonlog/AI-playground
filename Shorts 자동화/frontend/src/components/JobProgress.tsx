type Job = {
  status: string;
  stage?: string | null;
  progress: number;
  retry_count: number;
  error?: { message: string } | null;
};

type Props = {
  job: Job;
  live: { stage: string; progress: number } | null;
  /** Screen text per stage. */
  stages: Record<string, string>;
  failTitle: string;
  hint?: string;
  onRetry: () => void;
};

const MAX_RETRIES = 3; // backend max_retries

export default function JobProgress({ job, live, stages, failTitle, hint, onRetry }: Props) {
  if (job.status === "failed") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="mb-1 font-semibold text-red-700">{failTitle}</p>
        <p className="mb-4 text-sm text-red-700">{job.error?.message}</p>
        {job.retry_count < MAX_RETRIES && (
          <button onClick={onRetry} className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white">
            다시 시도 ({job.retry_count}/{MAX_RETRIES})
          </button>
        )}
      </div>
    );
  }
  const stage = live?.stage ?? job.stage ?? "queued";
  const percent = Math.round((live?.progress ?? job.progress) * 100);
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <div className="mb-2 flex justify-between text-sm">
        <span>{stages[stage] ?? stage}</span>
        <span className="tabular-nums">{percent}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-zinc-100"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full bg-zinc-900 transition-all" style={{ width: `${percent}%` }} />
      </div>
      {hint && <p className="mt-3 text-xs text-zinc-500">{hint}</p>}
    </div>
  );
}
