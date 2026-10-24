"""Command-line entry point: `python -m agentprobe ...`."""

from __future__ import annotations

import argparse
import os

import yaml

from . import report as report_mod
from .runner import DEFENSE_CONFIGS, run


def _load_config(path: str | None) -> dict:
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentprobe")
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the evaluation")
    r.add_argument("--config", default=None)
    r.add_argument("--model", action="append", default=None,
                   help="model spec, e.g. mock or ollama:llama3 (repeatable)")
    r.add_argument("--defense", action="append", default=None,
                   choices=list(DEFENSE_CONFIGS), help="defense config (repeatable)")
    r.add_argument("--trials", type=int, default=None)
    r.add_argument("--out", default="results")

    p = sub.add_parser("report", help="print an ASR report for a run")
    p.add_argument("--run", default="results/latest.json")

    args = parser.parse_args()

    if args.cmd == "run":
        cfg = _load_config(args.config)
        models = args.model or cfg.get("models", ["mock"])
        defenses = args.defense or cfg.get("defenses", ["none", "all"])
        trials = args.trials or cfg.get("trials", 5)
        rep = run(models, defenses, trials, args.out)
        print(f"Wrote results/run-{rep.run_id}.json "
              f"({len(rep.results)} trials). Now: python -m agentprobe report")
    elif args.cmd == "report":
        print(report_mod.render_text(args.run))


if __name__ == "__main__":
    main()
