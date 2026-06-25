#!/usr/bin/env python3
"""Build a BLIND scoring sheet from CONTROL_* and SCHED_* result files."""

import csv
import glob
import json
import random
import sys
from pathlib import Path


def rows_from_control(rec):
    out = []
    for c in rec["control"]:
        out.append({"item_id": rec["item_id"], "model": rec["model"],
                    "mode": c["instruction"], "hop": "single", "run_index": c["run_index"],
                    "response": c["reader"]})
    return out


def rows_from_sched(rec):
    out = []
    for run in rec["runs"]:
        for s in run["stages"]:
            out.append({"item_id": rec["item_id"], "model": rec["model"],
                        "mode": rec.get("mode", "neutral"), "hop": s["hop"],
                        "run_index": run["run_index"], "response": s["reader"]})
    return out


def main():
    paths = []
    for pat in sys.argv[1:]:
        paths.extend(glob.glob(pat))
    if not paths:
        sys.exit("Pass CONTROL_*.json and/or SCHED_*.json paths/globs.")

    all_rows = []
    criteria = {}
    for p in paths:
        rec = json.loads(Path(p).read_text(encoding="utf-8"))
        criteria[rec["item_id"]] = rec.get("recovery_criterion", "(none)")
        if "control" in rec:
            all_rows.extend(rows_from_control(rec))
        elif "runs" in rec:
            all_rows.extend(rows_from_sched(rec))
        else:
            print("skipping (unknown format): " + p)

    sheet_rows, key_rows = [], []
    for r in all_rows:
        rid = "%06d" % random.randint(0, 999999)
        sheet_rows.append({"row_id": rid, "item_id": r["item_id"],
                           "response": r["response"].replace("\n", " ").strip(), "score": ""})
        key_rows.append({"row_id": rid, "item_id": r["item_id"], "model": r["model"],
                         "mode": r["mode"], "hop": r["hop"], "run_index": r["run_index"]})

    random.shuffle(sheet_rows)

    results_dir = Path(paths[0]).resolve().parent
    sheet = results_dir / "score_sheet.csv"
    key = results_dir / "score_key.csv"

    with sheet.open("w", newline="", encoding="utf-8") as f:
        f.write("# BLIND SCORING SHEET. Score each row 0/1/2 against the criterion for its item.\n")
        f.write("# 2 = danger recovered WITH correct urgency; 1 = topic kept but urgency/specifics corrupted or generic; 0 = not recovered / no urgent issue.\n")
        f.write("# RECOVERY CRITERIA:\n")
        for iid, crit in sorted(criteria.items()):
            f.write("#   [" + iid + "] " + crit + "\n")
        f.write("# Do NOT open score_key.csv until you have filled every score.\n")
        w = csv.DictWriter(f, fieldnames=["row_id", "item_id", "response", "score"])
        w.writeheader()
        w.writerows(sheet_rows)

    with key.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["row_id", "item_id", "model", "mode", "hop", "run_index"])
        w.writeheader()
        w.writerows(key_rows)

    print("wrote " + str(sheet) + " (" + str(len(sheet_rows)) + " rows to score)")
    print("wrote " + str(key) + " (open only AFTER scoring)")


if __name__ == "__main__":
    main()