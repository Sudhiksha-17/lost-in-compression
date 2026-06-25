#!/usr/bin/env python3
"""Runner for the lost-in-compression study (length-matched single vs multi hop)."""

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

COMPRESS_SENTENCES = "Summarize the following report in {n} sentences.\n\n{text}"
COMPRESS_WORDCAP = (
    "Summarize the following in one sentence of no more than {words} words.\n\n{text}"
)


def call_model(model, prompt, api_key, temperature=0.2, max_tokens=800, retries=3):
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=120)
            r.raise_for_status()
            data = r.json()
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {}) or {}
            content = msg.get("content")
            if content is None or content == "":
                # some models return content in reasoning, or empty on a finish_reason
                content = msg.get("reasoning") or ""
            if content is None or content.strip() == "":
                last_err = "empty content; raw choice = " + json.dumps(choice)[:500]
                time.sleep(2 * (attempt + 1))
                continue
            return content.strip()
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Model call failed after retries: " + str(last_err))


def word_count(text):
    return len(text.split())


def run_once(item, model, api_key, run_idx, wordcap):
    steps = {}

    qa = RISK_QUESTION.format(text=item["fact_a"])
    steps["gate_fact_a"] = {"prompt": qa, "response": call_model(model, qa, api_key)}
    qb = RISK_QUESTION.format(text=item["fact_b"])
    steps["gate_fact_b"] = {"prompt": qb, "response": call_model(model, qb, api_key)}

    sh_prompt = COMPRESS_WORDCAP.format(words=wordcap, text=item["source"])
    sh_summary = call_model(model, sh_prompt, api_key)
    steps["single_hop_summary"] = {
        "prompt": sh_prompt, "response": sh_summary, "word_count": word_count(sh_summary),
    }
    sh_q = RISK_QUESTION.format(text=sh_summary)
    steps["single_hop_reader"] = {"prompt": sh_q, "response": call_model(model, sh_q, api_key)}

    h1_prompt = COMPRESS_SENTENCES.format(n="four", text=item["source"])
    h1 = call_model(model, h1_prompt, api_key)
    steps["multi_hop_1"] = {"prompt": h1_prompt, "response": h1, "word_count": word_count(h1)}

    h2_prompt = COMPRESS_SENTENCES.format(n="two", text=h1)
    h2 = call_model(model, h2_prompt, api_key)
    steps["multi_hop_2"] = {"prompt": h2_prompt, "response": h2, "word_count": word_count(h2)}

    h3_prompt = COMPRESS_WORDCAP.format(words=wordcap, text=h2)
    h3 = call_model(model, h3_prompt, api_key)
    steps["multi_hop_3"] = {"prompt": h3_prompt, "response": h3, "word_count": word_count(h3)}

    mh_q = RISK_QUESTION.format(text=h3)
    steps["multi_hop_reader"] = {"prompt": mh_q, "response": call_model(model, mh_q, api_key)}

    return {"run_index": run_idx, "steps": steps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--wordcap", type=int, default=25)
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY in your environment.")

    item = json.loads(Path(args.item).read_text(encoding="utf-8"))

    record = {
        "item_id": item["id"],
        "domain": item["domain"],
        "model": args.model,
        "temperature": args.temperature,
        "wordcap": args.wordcap,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recovery_criterion": item["recovery_criterion"],
        "runs": [],
    }

    for i in range(args.runs):
        print("  run " + str(i + 1) + "/" + str(args.runs) + " ...", flush=True)
        record["runs"].append(run_once(item, args.model, api_key, i, args.wordcap))

    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_model = args.model.replace("/", "_")
    out = results_dir / (item["id"] + "__" + safe_model + "__" + ts + ".json")
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("wrote " + str(out))


if __name__ == "__main__":
    main()