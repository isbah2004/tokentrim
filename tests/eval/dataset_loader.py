"""Dataset loader for the golden evaluation set.

Reads golden_v1.jsonl (one JSON object per line) and returns a list of
EvalCase dataclasses that the harness iterates over.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvalCase:
    id: str
    category: str
    query: str
    golden_answer: str
    history: List[Dict[str, str]] = field(default_factory=list)
    rag_chunks: List[str] = field(default_factory=list)
    warmup_query: Optional[str] = None
    expectations: Dict[str, Any] = field(default_factory=dict)
    known_limitation: bool = False
    judge_config: Dict[str, Any] = field(default_factory=dict)

    # Derived helpers
    @property
    def cache_hit_after_warmup(self) -> Optional[bool]:
        return self.expectations.get("cache_hit_after_warmup")

    @property
    def expected_model_tier(self) -> Optional[str]:
        return self.expectations.get("expected_model_tier")

    @property
    def required_in_trimmed_prompt(self) -> List[str]:
        return self.expectations.get("required_in_trimmed_prompt", [])

    @property
    def required_in_naive_prompt(self) -> List[str]:
        return self.expectations.get("required_in_naive_prompt", [])

    @property
    def min_judge_overall(self) -> float:
        return self.judge_config.get("min_overall", 0.70)


def load_dataset(path: str) -> List[EvalCase]:
    """Load a JSONL golden dataset from *path* and return EvalCase objects."""
    cases: List[EvalCase] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {lineno} of {path}: {exc}") from exc
            cases.append(
                EvalCase(
                    id=obj["id"],
                    category=obj.get("category", ""),
                    query=obj["query"],
                    golden_answer=obj["golden_answer"],
                    history=obj.get("history", []),
                    rag_chunks=obj.get("rag_chunks", []),
                    warmup_query=obj.get("warmup_query"),
                    expectations=obj.get("expectations", {}),
                    known_limitation=obj.get("known_limitation", False),
                    judge_config=obj.get("judge", {}),
                )
            )
    return cases
