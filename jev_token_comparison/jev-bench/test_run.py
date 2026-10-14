"""Offline check with mocked HTTP: normal path, a 500 on one ticket, and a 401 stop. Run: python test_run.py"""
import json
import os

import anthropic
import httpx2

import providers
import run
from data import TICKETS

os.environ.setdefault("TYPESAFE_API_KEY", "test-not-a-real-key")

JEV_OK = {
    "model": "jev-1.13.0",
    "answers": {
        "department": {"type": "choice", "choice": "billing", "confidence": 1.0, "probabilities": {"billing": 1.0}},
        "frustration": {"type": "score", "score": 1.4, "probabilities": {"0": 0.1, "1": 0.4, "2": 0.5}},
        "is_urgent": {"type": "noul", "noul": 0.8},
    },
    "usage": {"input_tokens": 100, "output_tokens": 50},
}
CLAUDE_OK = {
    "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
    "content": [{"type": "tool_use", "id": "tu_1", "name": "answer",
                 "input": {"department": "billing", "frustration": 2, "is_urgent": 0.3}}],
    "stop_reason": "tool_use", "stop_sequence": None,
    "usage": {"input_tokens": 600, "output_tokens": 80},
}


def install(jev_status, claude_status):
    """jev_status / claude_status: fn(call_index) -> HTTP status."""
    n = {"jev": 0, "claude": 0}
    seen_bodies = []

    def jev(req):
        i = n["jev"]; n["jev"] += 1
        seen_bodies.append(json.loads(req.content))
        s = jev_status(i)
        return httpx2.Response(s, json=JEV_OK if s == 200 else {"error": "x"})

    def claude(req):
        i = n["claude"]; n["claude"] += 1
        s = claude_status(i)
        body = CLAUDE_OK if s == 200 else {"type": "error", "error": {"type": "api_error", "message": "x"}}
        return httpx2.Response(s, json=body)

    providers.http = httpx2.Client(transport=httpx2.MockTransport(jev))
    providers.claude = anthropic.Anthropic(
        api_key="test-not-a-real-key", max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(claude)),
    )
    return n, seen_bodies


def test_normal():
    _, bodies = install(lambda i: 200, lambda i: 200)
    rows, stopped = run.bench(TICKETS[:3], "claude-haiku-5-5")
    assert stopped is None and len(rows) == 3
    r = rows[0]
    assert r["jev_frustration"] == 2 and r["jev_frustration_raw"] == 1.4  # argmax, not round(1.4)
    assert (r["jev_in"], r["jev_out"], r["claude_in"], r["claude_out"]) == (100, 50, 600, 80)
    assert bodies[0]["model"] == "jev-latest" and set(bodies[0]["questions"]) == set(run.KEYS)
    s = run.summarize(rows, "claude-haiku-5-5")
    assert "3/3" in s and "| department | 100% (3/3)" in s and "| frustration | 100%" in s
    assert "| is_urgent | 0% (0/3)" in s  # 0.8 vs 0.3 straddle 0.5
    assert "6.0x" in s  # input tokens 600 / 100


def test_500_recorded_and_continues():
    install(lambda i: 500 if i == 1 else 200, lambda i: 200)
    rows, stopped = run.bench(TICKETS[:3], "claude-haiku-5-5")
    assert stopped is None and len(rows) == 3
    assert rows[1]["jev_ok"] is False and "500" in rows[1]["jev_error"]
    assert rows[1]["claude_ok"] is True  # Claude still called for that ticket
    assert "2/3" in run.summarize(rows, "claude-haiku-5-5")


def test_401_stops():
    n, _ = install(lambda i: 200, lambda i: 401 if i == 1 else 200)
    rows, stopped = run.bench(TICKETS[:5], "claude-haiku-5-5")
    assert stopped and "401" in stopped and len(rows) == 1
    assert n["claude"] == 2 and n["jev"] == 2  # no calls after the 401


def test_bad_tool_input_is_failure():
    bad = json.loads(json.dumps(CLAUDE_OK))
    bad["content"][0]["input"]["frustration"] = 5
    providers.claude = anthropic.Anthropic(
        api_key="test-not-a-real-key", max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(lambda r: httpx2.Response(200, json=bad))),
    )
    row = run.call("claude", providers.ask_claude, "x", "claude-haiku-5-5")
    assert row["claude_ok"] is False and "frustration" in row["claude_error"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
