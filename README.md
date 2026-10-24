# AgentProbe

Measure whether your LLM agent's guardrails actually stop **indirect prompt injection** and **tool abuse**.

AgentProbe injects attack probes into an agent's tool outputs, checks each run with deterministic oracles, and reports the **attack success rate (ASR)** per probe category, model, and defense.

> **Scope:** For agents you own or are authorized to test. Probes carry a harmless canary string, and the "sensitive" tool is a stub that only logs calls. See [SECURITY.md](SECURITY.md).

## How it works

1. **Inject:** A probe is planted in a tool result (a fetched page, a read file).
2. **Run:** The target agent (a minimal ReAct loop) processes it with a chosen defense on or off.
3. **Judge:** Oracles check whether the canary leaked or a forbidden tool was called.
4. **Report:** Verdicts roll up into ASR tables (JSON + terminal).

```
Probe library ──▶ tool output ──▶ Target agent ──▶ Oracle ──▶ ASR report
```

## Quick start

```bash
pip install -r requirements.txt

# Offline run with the deterministic mock model (no API key)
python -m agentprobe run --config configs/default.yaml --model mock

# View results
python -m agentprobe report --run results/latest.json
```

To test a real model, pass an Ollama or API model to `--model` (adapters in `agentprobe/target/models.py`).

## Metrics

| Metric | Meaning |
| --- | --- |
| **ASR** | Share of trials where an oracle fired. Lower is better. |
| **Baseline delta** | ASR with defense off − ASR with defense on. Positive means the defense helps. |
| **Per-category ASR** | ASR by probe class: shows which attacks a defense stops and which slip through. |

## Layout

| Component | Path | Role |
| --- | --- | --- |
| Probes | `agentprobe/attacks/library.py` | Injection strings tagged with OWASP LLM / ATLAS IDs |
| Agent | `agentprobe/target/agent.py` | ReAct loop with pluggable tools |
| Tools | `agentprobe/target/tools.py` | `read_file`, `web_fetch`, stubbed `send_message` |
| Defenses | `agentprobe/target/defenses.py` | Filters, tool allowlist, human-in-the-loop, context tagging |
| Oracles | `agentprobe/oracles/` | Canary-leak and forbidden-call detectors |
| Runner | `agentprobe/runner.py` | Trials × models × defenses → JSON |
| Report | `agentprobe/report.py` | ASR tables |

## Related tools

[garak](https://github.com/NVIDIA/garak), [promptfoo](https://www.promptfoo.dev/), and [PyRIT](https://github.com/Azure/PyRIT) are broad red-teaming frameworks; [AgentDojo](https://github.com/ethz-spylab/agentdojo) is the closest research benchmark. AgentProbe is a minimal, offline-first harness for A/B testing a single defense's effect on tool-call injection.

## License

MIT. See [LICENSE](LICENSE).
