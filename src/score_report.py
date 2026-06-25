#!/usr/bin/env python3
"""Merge scored score_sheet.csv with score_key.csv and report recovery rates."""

import csv
import sys
from collections import defaultdict


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python src/score_report.py <score_sheet.csv> <score_key.csv>")
    sheet_path, key_path = sys.argv[1], sys.argv[2]

    scores = {}
    with open(sheet_path, encoding="utf-8") as f:
        reader = csv.DictReader(r for r in f if not r.startswith("#"))
        for row in reader:
            s = row["score"].strip()
            if s == "":
                continue
            scores[row["row_id"]] = int(s)

    key = {}
    with open(key_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key[row["row_id"]] = row

    buckets = defaultdict(list)
    for rid, sc in scores.items():
        k = key.get(rid)
        if not k:
            continue
        buckets[(k["model"], k["mode"], k["hop"])].append(sc)

    def hop_sort(h):
        return (0, -1) if h == "single" else (1, int(h))

    print("%-28s %-11s %-7s  n   L0  L1  L2   rec%%  (rec=L2)" % ("model", "mode", "hop"))
    print("-" * 78)
    for (model, mode, hop) in sorted(buckets, key=lambda t: (t[0], t[1], hop_sort(t[2]))):
        v = buckets[(model, mode, hop)]
        n = len(v)
        l0 = v.count(0); l1 = v.count(1); l2 = v.count(2)
        rec = (l2 / n * 100) if n else 0
        m = model.split("/")[-1]
        print("%-28s %-11s %-7s  %2d  %2d  %2d  %2d  %5.1f" % (m, mode, str(hop), n, l0, l1, l2, rec))

    print()
    print("Read: under neutral, recovery (L2) should fall with hop depth and/or be low;")
    print("under risk_aware it should stay high. L1 = topic kept but urgency/specifics lost.")


if __name__ == "__main__":
    main()