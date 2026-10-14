"""Run Jev and Claude on the same tickets, one call at a time, and compare tokens, latency, cost."""
import argparse
import csv
import os
import statistics
import sys

import providers
from data import TICKETS

KEYS = ("department", "frustration", "is_urgent")


def call(name, fn, *args):
    """Run one provider call. Per-ticket failures are recorded; AuthError propagates."""
    try:
        answers, tin, tout, ms = fn(*args)
    except providers.AuthError:
        raise
    except Exception as e:
        return {f"{name}_ok": False, f"{name}_error": f"{type(e).__name__}: {e}"[:300]}
    row = {f"{name}_ok": True, f"{name}_error": "", f"{name}_in": tin, f"{name}_out": tout, f"{name}_ms": round(ms)}
    row.update({f"{name}_{k}": v for k, v in answers.items()})
    return row


def bench(tickets, model):
    """Returns (rows, stopped_reason). Stops at the first 401/403."""
    rows = []
    for t in tickets:
        row = {"id": t["id"], "kind": t["kind"]}
        try:
            row.update(call("jev", providers.ask_jev, t["text"]))
            row.update(call("claude", providers.ask_claude, t["text"], model))
        except providers.AuthError as e:
            return rows, str(e)
        rows.append(row)
        print(f"  #{t['id']:>2} jev={'ok' if row['jev_ok'] else 'FAIL'} claude={'ok' if row['claude_ok'] else 'FAIL'}")
    return rows, None


def summarize(rows, model):
    both = [r for r in rows if r["jev_ok"] and r["claude_ok"]]
    out = [f"\n비교 대상: 두 모델 모두 성공한 {len(both)}/{len(rows)}건\n"]
    if not both:
        return "\n".join(out)

    stats = {}
    for name, m in (("jev", "jev-latest"), ("claude", model)):
        tin = [r[f"{name}_in"] for r in both]
        tout = [r[f"{name}_out"] for r in both]
        total = providers.cost(m, sum(tin), sum(tout))
        stats[name] = {
            "label": m,
            "in": statistics.mean(tin),
            "out": statistics.mean(tout),
            "p50": statistics.median(r[f"{name}_ms"] for r in both),
            "total": total,
            "monthly": total / len(both) * 1_000_000,
        }

    def ratio(k):
        j = stats["jev"][k]
        return f"{stats['claude'][k] / j:.1f}x" if j else "n/a (Jev=0)"

    out += [
        "| 모델 | 평균 입력 토큰 | 평균 출력 토큰 | 지연 p50 (ms) | 총비용 (USD) | 월 100만 건 환산 (USD) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for s in stats.values():
        out.append(
            f"| {s['label']} | {s['in']:.1f} | {s['out']:.1f} | {s['p50']:.0f} | ${s['total']:.6f} | ${s['monthly']:,.2f} |"
        )
    out.append(
        f"| Claude/Jev 배수 | {ratio('in')} | {ratio('out')} | {ratio('p50')} | {ratio('total')} | {ratio('monthly')} |"
    )

    out += ["", "| 질문 | 일치율 | 기준 |", "|---|---:|---|"]
    rules = {
        "department": ("choice 라벨 일치", lambda j, c: j == c),
        "frustration": ("score 정수 일치 (Jev는 최빈 단계)", lambda j, c: int(j) == int(c)),
        "is_urgent": ("noul 0.5 기준 일치", lambda j, c: (j >= 0.5) == (c >= 0.5)),
    }
    for k in KEYS:
        desc, same = rules[k]
        hits = sum(same(r[f"jev_{k}"], r[f"claude_{k}"]) for r in both)
        out.append(f"| {k} | {hits / len(both):.0%} ({hits}/{len(both)}) | {desc} |")
    return "\n".join(out)


def write_csv(rows, path):
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    # utf-8-sig so Excel opens Korean text correctly
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=list(providers.CLAUDE_MODELS), default="haiku")
    p.add_argument("--limit", type=int, default=len(TICKETS))
    p.add_argument("--out", default="results.csv")
    args = p.parse_args()

    missing = [k for k in ("TYPESAFE_API_KEY", "ANTHROPIC_API_KEY") if not os.environ.get(k)]
    if missing:
        print("환경변수가 비어 있어 실행하지 않습니다: " + ", ".join(missing))
        print("설정 예시 (값은 직접 입력):")
        print('  PowerShell: $env:TYPESAFE_API_KEY = "..."; $env:ANTHROPIC_API_KEY = "..."')
        print('  bash:       export TYPESAFE_API_KEY="..." ANTHROPIC_API_KEY="..."')
        sys.exit(2)

    import anthropic

    providers.claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip(), max_retries=0, timeout=60)
    model = providers.CLAUDE_MODELS[args.model]
    print(f"Jev vs {model}, {args.limit}건 순차 실행")
    rows, stopped = bench(TICKETS[: args.limit], model)
    write_csv(rows, args.out)
    if stopped:
        print(f"\n인증 오류로 중단: {stopped}. 완료된 {len(rows)}건만 {args.out}에 저장.")
        sys.exit(1)
    print(summarize(rows, model))
    print(f"\n상세: {args.out}")


if __name__ == "__main__":
    main()
