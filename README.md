# AgentProbe

A small, defensive evaluation harness for measuring how well an LLM agent resists
**indirect prompt injection** and **tool-abuse** attempts. AgentProbe runs a library
of injection probes against a *target agent you control*, then uses deterministic
oracles (canary tokens and a forbidden-tool-call monitor) to decide whether each
probe succeeded. It reports an **attack success rate (ASR)** per probe category,
per model, and per defense configuration.

It is built for one job: telling you, with numbers, whether a guardrail actually
works. It is the agent/MCP-focused cousin of tools like
[garak](https://github.com/NVIDIA/garak), [promptfoo](https://www.promptfoo.dev/)
and [PyRIT](https://github.com/Azure/PyRIT).

> **Scope and intended use.** AgentProbe tests systems you own or are authorized to
> assess. Its probes carry a harmless canary string, not working exploit payloads,
> and the bundled "sensitive" action is a stubbed tool that records a call instead
> of doing anything. See [SECURITY.md](SECURITY.md).

## Why this exists

Agents read untrusted content — web pages, documents, tool results — straight back
into the model's context. An attacker who controls that content can try to steer the
agent: exfiltrate data through a tool call, invoke a privileged action, or ignore its
instructions. The defenses (input/output filters, tool allowlists, human-in-the-loop,
trusted/untrusted context separation) are only worth shipping if you can show they
lower ASR. AgentProbe measures that.

## What it does

```
             ┌──────────────┐      probe injected into        ┌──────────────┐
             │  Probe        │──────  a tool's output ────────▶│  Target agent │
             │  library      │                                 │  (ReAct loop) │
             └──────────────┘                                 └──────┬───────┘
                                                                     │ tool calls
                                                            ┌────────▼────────┐
                                                            │  Oracle:         │
                                                            │  canary leaked?  │
                                                            │  forbidden tool? │
                                                            └────────┬────────┘
                                                                     │ verdict
                                                            ┌────────▼────────┐
                                                            │  ASR report      │
                                                            │  (JSON + table)  │
                                                            └─────────────────┘
```

## Quick start

```bash
python -m pip install -r requirements.txt
# Dry run with the bundled deterministic mock model — no API key, no network:
python -m agentprobe run --config configs/default.yaml --model mock
# See the results table:
python -m agentprobe report --run results/latest.json
```

The mock model lets the whole pipeline run offline so you can develop probes and
oracles without touching a real LLM. To test a real model, point `--model` at an
Ollama model (local) or an API model via the adapter in `agentprobe/target/models.py`.

## Design

| Piece | File | Role |
| --- | --- | --- |
| Probe library | `agentprobe/attacks/library.py` | Injection strings + metadata (OWASP LLM, ATLAS) |
| Target agent | `agentprobe/target/agent.py` | Minimal ReAct loop with pluggable tools |
| Tools | `agentprobe/target/tools.py` | `read_file`, `web_fetch`, stubbed `send_message` |
| Defenses | `agentprobe/target/defenses.py` | Toggleable filters, allowlist, HITL, context tagging |
| Oracles | `agentprobe/oracles/` | Canary-leak and forbidden-call detectors |
| Runner | `agentprobe/runner.py` | N trials × models × defenses, writes JSON |
| Report | `agentprobe/report.py` | ASR table + per-category breakdown |

## Metrics

- **ASR** — fraction of trials where the oracle fired (lower is better for a defended agent).
- **Baseline delta** — ASR with a defense off minus ASR with it on. A defense that
  works shows a positive delta.
- **Per-category ASR** — broken out by probe class so you can see which attack a
  defense stops and which it misses.

## Mapping to the role

This repo demonstrates, in one place: building an *agentic AI security harness*,
*benchmarking*, and *evaluating* a control's effectiveness with reproducible numbers —
exactly the "research hypothesis → working code → recommendation" loop.

## License

MIT. See [LICENSE](LICENSE).
