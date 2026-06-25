#!/usr/bin/env python3
"""Plot recovery rate vs hop depth. Color = model, line style = mode, so each
model's neutral (solid) vs risk-aware (dashed) pair reads at a glance."""

import csv
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python src/plot_recovery.py <score_sheet.csv> <score_key.csv>")
    sheet_path, key_path = sys.argv[1], sys.argv[2]

    scores = {}
    with open(sheet_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(r for r in f if not r.startswith("#"))
        for row in reader:
            s = (row.get("score") or "").strip()
            if s != "":
                scores[row["row_id"]] = int(s)

    key = {}
    with open(key_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key[row["row_id"]] = row

    series = defaultdict(lambda: defaultdict(list))
    for rid, sc in scores.items():
        k = key.get(rid)
        if not k:
            continue
        hop = k["hop"]
        if hop == "single":
            continue
        series[(k["model"], k["mode"])][int(hop)].append(sc)

    # color per model, style per mode
    model_color = {}
    palette = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e"]
    mode_style = {"neutral": "-", "risk_aware": "--"}
    mode_label = {"neutral": "neutral", "risk_aware": "risk-aware"}

    plt.figure(figsize=(7, 4.5))
    for (model, mode), byhop in sorted(series.items()):
        m = model.split("/")[-1]
        if m not in model_color:
            model_color[m] = palette[len(model_color) % len(palette)]
        hops = sorted(byhop)
        rates = [100.0 * sum(1 for s in byhop[h] if s == 2) / len(byhop[h]) for h in hops]
        plt.plot(hops, rates, mode_style.get(mode, "-"), marker="o",
                 color=model_color[m], linewidth=2,
                 label=m + " / " + mode_label.get(mode, mode))

    plt.xlabel("summarization hop (0 = full source)")
    plt.ylabel("recovery rate (% scored 2)")
    plt.title("Safety-signal recovery vs summarization depth")
    plt.ylim(-5, 105)
    plt.xticks([0, 1, 2, 3, 4])
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, loc="lower left")
    plt.tight_layout()
    out = "results/recovery_vs_hop.png"
    plt.savefig(out, dpi=150)
    print("wrote " + out)


if __name__ == "__main__":
    main()