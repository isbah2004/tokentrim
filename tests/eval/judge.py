"""LLM-as-judge and rule-based judge for the TokenTrim evaluation harness.

Two implementations behind the same interface:

- RuleBasedJudge: fully offline, deterministic, stdlib-only. Used by default.
- LLMJudge: calls an OpenAI-compatible Model Studio endpoint. Activated when
  TOKENTRIM_JUDGE_LIVE=1 and DASHSCOPE_API_KEY are set.

Use make_judge() to get the right one for the current environment.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class JudgeScore:
    correctness: float        # 0-1: golden answer present / model says correct thing
    completeness: float       # 0-1: response covers what was asked
    conciseness: float        # 0-1: response is not excessively verbose
    hallucination_free: float # 0-1: response does not invent facts
    overall: float            # 0-1: weighted aggregate
    explanation: str          # human-readable rationale


class RuleBasedJudge:
    """Offline, deterministic judge using simple text heuristics.

    - correctness: 1.0 if golden answer is a substring of response (case-insensitive)
    - completeness: min(1, len(response) / len(golden)) — length ratio proxy
    - conciseness: 1.0 if response ≤ 2.5× golden length, else linear decay
    - hallucination_free: same as correctness (proxy: if it says the right thing it
      probably isn't hallucinating the core answer)
    - overall: weighted mean (correctness 0.4, completeness 0.2, conciseness 0.2, hf 0.2)
    """

    def score(self, query: str, golden: str, response: str) -> JudgeScore:
        g = golden.strip().lower()
        r = response.strip().lower()

        correctness = 1.0 if g in r else 0.0

        g_len = max(len(g), 1)
        r_len = len(r)
        completeness = min(1.0, r_len / g_len)

        ratio = r_len / g_len
        if ratio <= 2.5:
            conciseness = 1.0
        else:
            # linear decay: at 5× length → 0.5; at 10× → 0.0
            conciseness = max(0.0, 1.0 - (ratio - 2.5) / 7.5)

        hallucination_free = correctness  # proxy

        overall = (
            correctness * 0.4
            + completeness * 0.2
            + conciseness * 0.2
            + hallucination_free * 0.2
        )

        explanation = (
            f"correctness={correctness:.2f} (golden {'found' if correctness else 'NOT FOUND'} in response); "
            f"completeness={completeness:.2f} (len ratio {r_len}/{g_len}={ratio:.2f}); "
            f"conciseness={conciseness:.2f}; "
            f"overall={overall:.2f}"
        )
        return JudgeScore(
            correctness=correctness,
            completeness=completeness,
            conciseness=conciseness,
            hallucination_free=hallucination_free,
            overall=overall,
            explanation=explanation,
        )


class LLMJudge:
    """Live judge via an OpenAI-compatible Model Studio endpoint.

    Sends a structured rubric prompt requesting JSON scores for:
    correctness, completeness, conciseness, hallucination_free (each 1-5).
    Normalises to 0-1 range. Falls back gracefully on parse failure.
    """

    RUBRIC = (
        "You are an impartial evaluator. Given a QUERY, a GOLDEN ANSWER, and a RESPONSE, "
        "score the RESPONSE on the following criteria from 1 (poor) to 5 (excellent):\n"
        "- correctness: does the response contain the correct answer as in the golden answer?\n"
        "- completeness: does it fully address what was asked?\n"
        "- conciseness: is it appropriately brief (not excessively verbose)?\n"
        "- hallucination_free: does it avoid invented facts not in the golden answer?\n\n"
        "Return ONLY valid JSON: "
        '{\"correctness\": <1-5>, \"completeness\": <1-5>, \"conciseness\": <1-5>, '
        '\"hallucination_free\": <1-5>, \"explanation\": \"<one sentence>\"}'
    )

    def __init__(self, client=None, model: Optional[str] = None):
        self._client = client
        self.model = model or os.getenv("TOKENTRIM_JUDGE_MODEL", "qwen-plus")

    def _get_client(self):
        if self._client is None:
            from app import config
            from openai import OpenAI
            self._client = OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.BASE_URL)
        return self._client

    def score(self, query: str, golden: str, response: str) -> JudgeScore:
        prompt = (
            f"{self.RUBRIC}\n\n"
            f"QUERY: {query}\n\n"
            f"GOLDEN ANSWER: {golden}\n\n"
            f"RESPONSE: {response}"
        )
        try:
            completion = self._get_client().chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            raw = completion.choices[0].message.content or ""
            parsed = self._parse_response(raw)
        except Exception as exc:
            # On any failure, return a low score with explanation
            return JudgeScore(
                correctness=0.0, completeness=0.0, conciseness=0.0,
                hallucination_free=0.0, overall=0.0,
                explanation=f"LLMJudge error: {exc}",
            )
        return parsed

    def _parse_response(self, raw: str) -> JudgeScore:
        # Strip markdown code fences
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError:
            # Regex fallback: extract key:value pairs
            obj = {}
            for key in ("correctness", "completeness", "conciseness", "hallucination_free"):
                m = re.search(rf'"{key}"\s*:\s*([0-9.]+)', cleaned)
                if m:
                    obj[key] = float(m.group(1))
            m = re.search(r'"explanation"\s*:\s*"([^"]+)"', cleaned)
            if m:
                obj["explanation"] = m.group(1)

        def norm(val, default=0.0) -> float:
            """Normalise 1-5 → 0-1."""
            try:
                v = float(val)
                return max(0.0, min(1.0, (v - 1) / 4))
            except (TypeError, ValueError):
                return default

        correctness = norm(obj.get("correctness"))
        completeness = norm(obj.get("completeness"))
        conciseness = norm(obj.get("conciseness"))
        hallucination_free = norm(obj.get("hallucination_free"))
        overall = (correctness * 0.4 + completeness * 0.2 +
                   conciseness * 0.2 + hallucination_free * 0.2)
        return JudgeScore(
            correctness=correctness,
            completeness=completeness,
            conciseness=conciseness,
            hallucination_free=hallucination_free,
            overall=overall,
            explanation=str(obj.get("explanation", "No explanation.")),
        )


def make_judge():
    """Return LLMJudge if TOKENTRIM_JUDGE_LIVE=1 and API key present, else RuleBasedJudge."""
    if os.getenv("TOKENTRIM_JUDGE_LIVE") == "1":
        from app import config
        if config.DASHSCOPE_API_KEY:
            return LLMJudge()
    return RuleBasedJudge()
