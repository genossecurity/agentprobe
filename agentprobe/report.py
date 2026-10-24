"""Turn a run's raw trials into attack-success-rate tables."""

from __future__ import annotations

import json
from collections import defaultdict

from tabulate import tabulate


def _asr(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if r["fired"]) / len(rows)


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def asr_by_defense(report: dict) -> list[list]:
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in report["results"]:
        cells[(r["model"], r["defense"])].append(r)
    table = []
    for (model, defense), rows in sorted(cells.items()):
        table.append([model, defense, f"{_asr(rows):.0%}", len(rows)])
    return table


def asr_by_category(report: dict, defense: str = "none") -> list[list]:
    cells: dict[str, list[dict]] = defaultdict(list)
    for r in report["results"]:
        if r["defense"] == defense:
            cells[r["category"]].append(r)
    table = []
    for category, rows in sorted(cells.items()):
        table.append([category, f"{_asr(rows):.0%}", len(rows)])
    return table


def defense_deltas(report: dict) -> list[list]:
    """ASR(none) - ASR(defense) per category: positive means the defense helped."""
    base: dict[str, list[dict]] = defaultdict(list)
    for r in report["results"]:
        if r["defense"] == "none":
            base[r["category"]].append(r)
    table = []
    for defense in sorted({r["defense"] for r in report["results"]} - {"none"}):
        for category in sorted(base):
            on = [r for r in report["results"]
                  if r["defense"] == defense and r["category"] == category]
            if not on:
                continue
            delta = _asr(base[category]) - _asr(on)
            table.append([defense, category, f"{delta:+.0%}"])
    return table


def render_text(path: str) -> str:
    report = load(path)
    out = []
    out.append(f"Run {report['run_id']}  "
               f"({report['trials_per_cell']} trials/cell, "
               f"models={','.join(report['models'])})\n")
    out.append("ASR by model x defense")
    out.append(tabulate(asr_by_defense(report),
                        headers=["model", "defense", "ASR", "n"], tablefmt="github"))
    out.append("\nASR by category (defenses off)")
    out.append(tabulate(asr_by_category(report, "none"),
                        headers=["category", "ASR", "n"], tablefmt="github"))
    out.append("\nDefense effectiveness (ASR drop vs none)")
    out.append(tabulate(defense_deltas(report),
                        headers=["defense", "category", "ASR drop"], tablefmt="github"))
    return "\n".join(out)
