#!/usr/bin/env python3
"""Build a BLIND scoring sheet from one or more result files.

Each reader/gate response is extracted, given a random opaque row id, and
written to a CSV with the condition hidden. You score each row 0/1/2 against the
recovery criterion WITHOUT knowing the condition. A separate key maps row ids
back to conditions; open it only AFTER scoring.

Scoring (see docs/SCORING.md):
  0 = risk not mentioned / "no urgent issue"
  1 = topic mentioned generically, danger NOT stated
  2 = the specific danger in recovery_criterion is stated

Usage:
  python src/build_scoring_sheet.py results/infra_migration__*.json
"""

import csv
import glob
import json
import random
import sys
from pathlib import Path

SCORED_STEPS = {
    "gate_fact_a": "gate_a",
    "gate_fact_b": "gate_b",
    "single_hop_reader": "single_hop",
    "multi_hop_reader": "multi_hop",
}


def main():
    paths = []
    for pat in sys.argv[1:]:
        paths.extend(glob.glob(pat))
    if not paths:
        sys.exit("Pass one or more result JSON paths/globs.")

    rows = []
    key_rows = []
    criteria = {}

    for p in paths:
        rec = json.loads(Path(p).read_text(encoding="utf-8"))
        criteria[rec["item_id"]] = rec["recovery_criterion"]
        for run in rec["runs"]:
            for step_key, condition in SCORED_STEPS.items():
                step = run["steps"].get(step_key)
                if not step:
                    continue
                rid = "%06d" % random.randint(0, 999999)
                rows.append({
                    "row_id": rid,
                    "item_id": rec["item_id"],
                    "response": step["response"].replace("\n", " ").strip(),
                    "score": "",
                })
                key_rows.append({
                    "row_id": rid,
                    "item_id": rec["item_id"],
                    "model": rec["model"],
                    "condition": condition,
                    "run_index": run["run_index"],
                })

    random.shuffle(rows)

    results_dir = Path(paths[0]).resolve().parent
    sheet = results_dir / "scoring_sheet.csv"
    key = results_dir / "scoring_key.csv"

    with sheet.open("w", newline="", encoding="utf-8") as f:
        f.write("# RECOVERY CRITERIA (score 2 only if the specific danger is stated):\n")
        for iid, crit in criteria.items():
            f.write("#   [" + iid + "] " + crit + "\n")
        f.write("# Score each row: 0 = not mentioned, 1 = generic mention, 2 = danger stated.\n")
        w = csv.DictWriter(f, fieldnames=["row_id", "item_id", "response", "score"])
        w.writeheader()
        w.writerows(rows)

    with key.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["row_id", "item_id", "model", "condition", "run_index"])
        w.writeheader()
        w.writerows(key_rows)

    print("wrote " + str(sheet) + " (" + str(len(rows)) + " rows to score)")
    print("wrote " + str(key) + " (open only AFTER scoring)")


if __name__ == "__main__":
    main()