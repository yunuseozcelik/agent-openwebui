"""Basit maliyet takibi - Portkey ve LangChain bağımlılığı YOK."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_PATH = DATA_DIR / "cost_control.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


DEFAULT_PRICING = {
    "gpt-5.2": {
        "input_per_million_usd": _float_env("PRICE_GPT_5_2_INPUT_PER_M", 1.75),
        "output_per_million_usd": _float_env("PRICE_GPT_5_2_OUTPUT_PER_M", 14.0),
    },
    "gpt-4o-mini": {
        "input_per_million_usd": _float_env("PRICE_GPT_4O_MINI_INPUT_PER_M", 0.15),
        "output_per_million_usd": _float_env("PRICE_GPT_4O_MINI_OUTPUT_PER_M", 0.60),
    },
    "gpt-4o": {
        "input_per_million_usd": _float_env("PRICE_GPT_4O_INPUT_PER_M", 2.50),
        "output_per_million_usd": _float_env("PRICE_GPT_4O_OUTPUT_PER_M", 10.0),
    },
}


def _default_state() -> dict[str, Any]:
    return {
        "updated_at": _utc_now(),
        "total_requests": 0,
        "totals": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "llm_calls": 0,
        },
        "engines": {},
        "models": {},
        "recent": [],
    }


class CostTracker:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if not STATE_PATH.exists():
            return _default_state()
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return _default_state()

    def _save(self) -> None:
        self._state["updated_at"] = _utc_now()
        STATE_PATH.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _engine_bucket(self, engine: str) -> dict[str, Any]:
        return self._state["engines"].setdefault(
            engine,
            {
                "requests": 0,
                "llm_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "components": {},
            },
        )

    @staticmethod
    def _normalize_model_id(model_id: str) -> str:
        model = (model_id or "unknown").strip().lower()
        if model.startswith("@") and "/" in model:
            model = model.rsplit("/", 1)[-1]
        for known in DEFAULT_PRICING:
            if model == known or model.startswith(f"{known}-"):
                return known
        return model

    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        price = DEFAULT_PRICING.get(self._normalize_model_id(model_id))
        if not price:
            return 0.0
        return round(
            (input_tokens / 1_000_000) * price["input_per_million_usd"]
            + (output_tokens / 1_000_000) * price["output_per_million_usd"],
            8,
        )

    def record_request(self, engine: str) -> None:
        with self._lock:
            self._state["total_requests"] += 1
            engine_bucket = self._engine_bucket(engine)
            engine_bucket["requests"] += 1
            self._save()

    def record_llm_call(
        self,
        *,
        engine: str,
        component: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int | None = None,
    ) -> None:
        total_tokens = total_tokens if total_tokens is not None else input_tokens + output_tokens
        estimated_cost = self.estimate_cost(model_id, input_tokens, output_tokens)
        normalized_model = self._normalize_model_id(model_id)

        with self._lock:
            totals = self._state["totals"]
            totals["input_tokens"] += input_tokens
            totals["output_tokens"] += output_tokens
            totals["total_tokens"] += total_tokens
            totals["estimated_cost_usd"] = round(totals["estimated_cost_usd"] + estimated_cost, 8)
            totals["llm_calls"] += 1

            engine_bucket = self._engine_bucket(engine)
            engine_bucket["input_tokens"] += input_tokens
            engine_bucket["output_tokens"] += output_tokens
            engine_bucket["total_tokens"] += total_tokens
            engine_bucket["estimated_cost_usd"] = round(engine_bucket["estimated_cost_usd"] + estimated_cost, 8)
            engine_bucket["llm_calls"] += 1

            component_bucket = engine_bucket["components"].setdefault(
                component,
                {
                    "llm_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
            )
            component_bucket["llm_calls"] += 1
            component_bucket["input_tokens"] += input_tokens
            component_bucket["output_tokens"] += output_tokens
            component_bucket["total_tokens"] += total_tokens
            component_bucket["estimated_cost_usd"] = round(
                component_bucket["estimated_cost_usd"] + estimated_cost, 8
            )

            model_bucket = self._state["models"].setdefault(
                normalized_model,
                {
                    "llm_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
            )
            model_bucket["llm_calls"] += 1
            model_bucket["input_tokens"] += input_tokens
            model_bucket["output_tokens"] += output_tokens
            model_bucket["total_tokens"] += total_tokens
            model_bucket["estimated_cost_usd"] = round(model_bucket["estimated_cost_usd"] + estimated_cost, 8)

            self._state["recent"].insert(
                0,
                {
                    "timestamp": _utc_now(),
                    "engine": engine,
                    "component": component,
                    "model_id": model_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost_usd": estimated_cost,
                },
            )
            self._state["recent"] = self._state["recent"][:50]
            self._save()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = deepcopy(self._state)

        soft_limit = _float_env("COST_SOFT_LIMIT_USD", 5.0)
        warning_limit = _float_env("COST_WARNING_LIMIT_USD", 3.0)
        total_cost = state["totals"]["estimated_cost_usd"]
        budget_pct = round((total_cost / soft_limit) * 100, 2) if soft_limit > 0 else 0.0

        state["budget"] = {
            "warning_limit_usd": warning_limit,
            "soft_limit_usd": soft_limit,
            "used_percent": budget_pct,
            "warning_exceeded": total_cost >= warning_limit,
            "soft_limit_exceeded": total_cost >= soft_limit,
        }
        state["pricing"] = DEFAULT_PRICING
        return state

    def reset(self) -> None:
        with self._lock:
            self._state = _default_state()
            self._save()


cost_tracker = CostTracker()
