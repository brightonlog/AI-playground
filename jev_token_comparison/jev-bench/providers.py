"""One call per provider. Each returns answers in the same shape plus the API's own usage numbers.

answers = {"department": str, "frustration": int, "is_urgent": float}
"""
import os
import time

import anthropic
import httpx2

from data import QUESTIONS

JEV_URL = "https://api.typesafe.ai/v1/systemone"
CLAUDE_MODELS = {
    "haiku": "claude-haiku-5-5",
    "sonnet": "claude-sonnet-5-5",
    "opus": "claude-opus-5-5",
}
# USD per million tokens: (input, output)
PRICES = {
    "jev-latest": (0.042, 0.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
}

# Module-level clients so tests can swap in mock transports.
# Retries are off on both sides: a retry would hide failures and inflate latency.
http = httpx2.Client(timeout=60)
claude = None  # anthropic.Anthropic, created by run.py after the env check


class AuthError(Exception):
    """401/403: the whole run must stop."""


def cost(model, input_tokens, output_tokens):
    price_in, price_out = PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def ask_jev(text):
    body = {"state": text, "model": "jev-latest", "questions": QUESTIONS}
    headers = {"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY'].strip()}"}
    start = time.perf_counter()
    resp = http.post(JEV_URL, json=body, headers=headers)
    ms = (time.perf_counter() - start) * 1000
    if resp.status_code in (401, 403):
        raise AuthError(f"TypeSafe HTTP {resp.status_code}: {resp.text[:200]}")
    if resp.is_error:
        raise RuntimeError(f"TypeSafe HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    a = data["answers"]
    probs = a["frustration"]["probabilities"]
    answers = {
        "department": a["department"]["choice"],
        # score is a probability-weighted mean (e.g. 0.67); the most likely level is the comparable integer
        "frustration": int(max(probs, key=probs.get)),
        "frustration_raw": a["frustration"]["score"],
        "is_urgent": a["is_urgent"]["noul"],
    }
    return answers, data["usage"]["input_tokens"], data["usage"]["output_tokens"], ms


def _tool():
    props = {}
    for key, q in QUESTIONS.items():
        if q["type"] == "choice":
            desc = q["instructions"] + " " + "; ".join(f"{k}: {v}" for k, v in q["criteria"].items())
            props[key] = {"type": "string", "enum": list(q["criteria"]), "description": desc}
        elif q["type"] == "score":
            desc = q["instructions"] + " " + "; ".join(f"{i}: {v}" for i, v in enumerate(q["criteria"]))
            props[key] = {"type": "integer", "minimum": 0, "maximum": len(q["criteria"]) - 1, "description": desc}
        else:  # noul
            desc = q["instructions"] + " Probability that the answer is yes, from 0 to 1."
            props[key] = {"type": "number", "minimum": 0, "maximum": 1, "description": desc}
    return {
        "name": "answer",
        "description": "Record the judgments for the ticket.",
        "input_schema": {"type": "object", "properties": props, "required": list(props)},
    }


TOOL = _tool()
SYSTEM = "You triage Korean customer support tickets. Answer by calling the `answer` tool."


def _check(answers):
    """The API does not enforce enum/range for non-strict tools, so validate here."""
    for key, q in QUESTIONS.items():
        v = answers.get(key)
        if q["type"] == "choice":
            ok = v in q["criteria"]
        elif q["type"] == "score":
            ok = type(v) is int and 0 <= v < len(q["criteria"])
        else:
            ok = type(v) in (int, float) and 0 <= v <= 1
        if not ok:
            raise ValueError(f"invalid {key}: {v!r}")


def ask_claude(text, model):
    # Haiku 5.5 accepts a forced tool_choice. Sonnet 5.5 / Opus 5.5 reject it with a 400,
    # so they get "auto" plus the system prompt instruction, and a missing call counts as a failure.
    forced = model == "claude-haiku-5-5"
    kwargs = {"tool_choice": {"type": "tool", "name": "answer"}} if forced else {"output_config": {"effort": "low"}}
    start = time.perf_counter()
    try:
        msg = claude.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM,
            tools=[TOOL],
            messages=[{"role": "user", "content": text}],
            **kwargs,
        )
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
        raise AuthError(f"Anthropic HTTP {e.status_code}: {e.message[:200]}") from None
    ms = (time.perf_counter() - start) * 1000
    block = next((b for b in msg.content if b.type == "tool_use"), None)
    if block is None:
        raise ValueError(f"no tool call (stop_reason={msg.stop_reason})")
    answers = dict(block.input)
    _check(answers)
    return answers, msg.usage.input_tokens, msg.usage.output_tokens, ms
