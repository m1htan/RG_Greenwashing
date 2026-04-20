"""
Cost tracker for Gemini API calls.

Logs every API call's token usage and cost to a JSONL file.
Import and call log_api_call() after each generate_content() response.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

LOG = logging.getLogger("cost_tracker")

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COST_LOG = _REPO_ROOT / "cost" / "cost_log.jsonl"

# ---------------------------------------------------------------------------
# Pricing table  (USD per 1 million tokens)
# Source: https://ai.google.dev/pricing  — March 2025
# Update these values when Google changes pricing.
# ---------------------------------------------------------------------------
PRICING: dict[str, dict[str, float]] = {
    # model_name_prefix: {input_per_1M, output_per_1M}
    # For simplicity, use the ≤200K context price (most PDFs fit)
    "gemini-2.5-pro": {
        "input_per_1m": 1.25,
        "output_per_1m": 10.00,
        "input_per_1m_long": 2.50,   # >200K context
        "output_per_1m_long": 15.00,
    },
    "gemini-2.5-flash": {
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
        "input_per_1m_long": 0.30,
        "output_per_1m_long": 2.50,
    },
    "gemini-2.0-flash": {
        "input_per_1m": 0.10,
        "output_per_1m": 0.40,
        "input_per_1m_long": 0.10,
        "output_per_1m_long": 0.40,
    },
}

LONG_CONTEXT_THRESHOLD = 200_000  # tokens


def get_pricing(model: str) -> dict[str, float]:
    """Return pricing dict for a model. Falls back to pro pricing if unknown."""
    model_lower = model.lower().strip()
    for prefix, prices in PRICING.items():
        if prefix in model_lower:
            return prices
    LOG.warning("Unknown model '%s' — using gemini-2.5-pro pricing as fallback.", model)
    return PRICING["gemini-2.5-pro"]


def compute_cost(
    model: str,
    prompt_tokens: int,
    candidates_tokens: int,
) -> dict[str, float]:
    """Calculate cost in USD for a single API call."""
    prices = get_pricing(model)

    is_long = prompt_tokens > LONG_CONTEXT_THRESHOLD
    input_rate = prices["input_per_1m_long"] if is_long else prices["input_per_1m"]
    output_rate = prices["output_per_1m_long"] if is_long else prices["output_per_1m"]

    cost_input = (prompt_tokens / 1_000_000) * input_rate
    cost_output = (candidates_tokens / 1_000_000) * output_rate

    return {
        "cost_input_usd": round(cost_input, 6),
        "cost_output_usd": round(cost_output, 6),
        "cost_total_usd": round(cost_input + cost_output, 6),
        "is_long_context": is_long,
    }


def extract_usage(response: Any) -> dict[str, Optional[int]]:
    """Extract token counts from a Gemini response object."""
    um = getattr(response, "usage_metadata", None)
    if um is None:
        return {"prompt_tokens": None, "candidates_tokens": None, "total_tokens": None}
    return {
        "prompt_tokens": getattr(um, "prompt_token_count", None),
        "candidates_tokens": getattr(um, "candidates_token_count", None),
        "total_tokens": getattr(um, "total_token_count", None),
    }


def log_api_call(
    response: Any,
    model: str,
    pdf_filename: str = "",
    status: str = "ok",
    cost_log_path: Optional[Path] = None,
    extra: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Log a single API call to the cost JSONL file.
    Returns the record dict.
    """
    log_path = cost_log_path or DEFAULT_COST_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)

    usage = extract_usage(response)
    prompt_t = usage["prompt_tokens"] or 0
    cand_t = usage["candidates_tokens"] or 0
    total_t = usage["total_tokens"] or (prompt_t + cand_t)

    cost = compute_cost(model, prompt_t, cand_t)

    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pdf_filename": pdf_filename,
        "model": model,
        "prompt_tokens": prompt_t,
        "candidates_tokens": cand_t,
        "total_tokens": total_t,
        **cost,
        "status": status,
    }
    if extra:
        record.update(extra)

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        LOG.error("Failed to write cost log: %s", e)

    return record


def read_cost_log(cost_log_path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Read all records from the cost JSONL file."""
    log_path = cost_log_path or DEFAULT_COST_LOG
    if not log_path.exists():
        return []
    records = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def get_summary(cost_log_path: Optional[Path] = None) -> dict[str, Any]:
    """Compute summary statistics from cost log."""
    records = read_cost_log(cost_log_path)
    if not records:
        return {
            "total_calls": 0,
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "avg_cost_per_file": 0.0,
            "by_model": {},
            "by_status": {},
            "records": [],
        }

    total_cost = sum(r.get("cost_total_usd", 0) for r in records)
    total_prompt = sum(r.get("prompt_tokens", 0) for r in records)
    total_output = sum(r.get("candidates_tokens", 0) for r in records)
    total_tokens = sum(r.get("total_tokens", 0) for r in records)

    # By model
    by_model: dict[str, dict[str, Any]] = {}
    for r in records:
        m = r.get("model", "unknown")
        if m not in by_model:
            by_model[m] = {"calls": 0, "cost_usd": 0.0, "tokens": 0}
        by_model[m]["calls"] += 1
        by_model[m]["cost_usd"] = round(by_model[m]["cost_usd"] + r.get("cost_total_usd", 0), 6)
        by_model[m]["tokens"] += r.get("total_tokens", 0)

    # By status
    by_status: dict[str, int] = {}
    for r in records:
        s = r.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "total_calls": len(records),
        "total_cost_usd": round(total_cost, 4),
        "total_prompt_tokens": total_prompt,
        "total_output_tokens": total_output,
        "total_tokens": total_tokens,
        "avg_cost_per_file": round(total_cost / len(records), 4) if records else 0.0,
        "by_model": by_model,
        "by_status": by_status,
        "records": records,
    }
