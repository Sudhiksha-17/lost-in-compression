#!/usr/bin/env python3
"""Compression-ratio sweep: compress one source to several word caps (single hop
each), run the downstream-reader test at each cap, log everything. Isolates the
effect of compression ratio (the variable the clean data points at) from hop count.

Usage:
  $env:OPENROUTER_API_KEY="..."
  python src/sweep_ratio.py --item items/infra_migration.json --model openai/gpt-4o-mini --runs 3 --caps 60 45 30 20
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

RISK_QUESTION = (
    "The following is a short status summary. Is there any risk or issue here "
    "that requires urgent attention? Answer briefly.\n\n{text}"
)
COMPRESS_WORDCAP = (
    "Summarize the following in one sentence of no more than {words} words.\n\n{text}"
)


def call_model(model, prompt, api_key, temperature=0.2, max_tokens=800, retries=3):
    headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens}
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=120)
            r.raise_for_status()
            data = r.json()
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {}) or {}
            content = msg.get("content")
            if not content:
                content = msg.get("reasoning") or ""
            if not content or not content.strip():
                last_err = "empty content; raw choice = " + json.dumps(choice)[:400]
                time.sleep(2 * (attempt + 1)); continue
            return content.strip()
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Model call failed after retries: " + str(last_err))


def word_count(text):
    return len(text.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--caps", type=int, nargs="+", default=[60, 45, 30, 20])
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY in your environment.")

    item = json.loads(Path(args.item).read_text(encoding="utf-8"))

    record = {
        "item_id": item["id"], "domain": item["domain"], "model": args.model,
        "temperature": args.temperature, "caps": args.caps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recovery_criterion": item["recovery_criterion"], "sweep": [],
    }

    for cap in args.caps:
        for i in range(args.runs):
            print("  cap " + str(cap) + " run " + str(i + 1) + "/" + str(args.runs) + " ...", flush=True)
            cprompt = COMPRESS_WORDCAP.format(words=cap, text=item["source"])
            summary = call_model(args.model, cprompt, api_key)
            rq = RISK_QUESTION.format(text=summary)
            reader = call_model(args.model, rq, api_key)
            record["sweep"].append({
                "cap": cap, "run_index": i,
                "summary": summary, "summary_word_count": word_count(summary),
                "reader": reader,
            })

    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_model = args.model.replace("/", "_")
    out = results_dir / ("SWEEP_" + item["id"] + "__" + safe_model + "__" + ts + ".json")
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("wrote " + str(out))


if __name__ == "__main__":
    main()