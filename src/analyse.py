#!/usr/bin/env python3
"""Merge a completed scoring_sheet.csv with scoring_key.csv and report the
recovery-level distribution per condition. Run only AFTER scoring blind.

Usage:
  python src/analyse.py results/scoring_sheet.csv results/scoring_key.csv
"""

import csv
import sys
from collections import defaultdict


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python src/analyse.py <scoring_sheet.csv> <scoring_key.csv>")
    sheet_path, key_path = sys.argv[1], sys.argv[2]

    scores = {}
    with open(sheet_path, encoding="utf-8") as f:
        reader = csv.DictReader(r for r in f if not r.startswith("#"))
        for row in reader:
            if row["score"].strip() == "":
                continue
            scores[row["row_id"]] = int(row["score"])

    key = {}
    with open(key_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key[row["row_id"]] = row

    dist = defaultdict(lambda: {0: 0, 1: 0, 2: 0})
    for rid, sc in scores.items():
        k = key.get(rid)
        if not k:
            continue
        cond = k["model"] + " | " + k["condition"]
        dist[cond][sc] += 1

    print("%-45s  L0   L1   L2   n   recovery%%" % "condition")
    print("-" * 80)
    for cond in sorted(dist):
        d = dist[cond]
        n = d[0] + d[1] + d[2]
        rec = (d[2] / n * 100) if n else 0
        print("%-45s  %3d  %3d  %3d  %3d   %5.1f" % (cond, d[0], d[1], d[2], n, rec))

    print()
    print("Look for: single_hop HIGH L2 (preserved); multi_hop LOW L2 + more L0/L1 (lost/demoted);")
    print("gate_a and gate_b should be L0/L1 (facts inert alone). Any L2 in a gate = item over-determined.")


if __name__ == "__main__":
    main()