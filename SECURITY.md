# Security and intended use

AgentProbe is a **defensive evaluation tool**. It is designed to be pointed at an
agent you build, own, or are explicitly authorized to assess, so you can measure
whether its safeguards hold.

## Design choices that keep it defensive

- **Canary, not payload.** Probes try to make the target agent reveal a benign,
  randomly generated canary token (`AGENTPROBE-CANARY-<uuid>`). There is no real
  secret, credential, or data to steal. Success means "the guardrail let the canary
  out," which is all the oracle needs.
- **Stubbed sensitive action.** The "privileged" tool (`send_message`) does nothing
  but append a record to an in-memory list. Nothing is sent anywhere. The oracle
  checks whether it *would* have been called with attacker-controlled arguments.
- **No live exfiltration endpoints.** The harness never makes outbound network calls
  on behalf of a probe. `web_fetch` reads from a local fixture directory you populate.
- **Local-first.** The default configuration runs entirely offline against a mock
  model.

## What this tool is not for

- Testing third-party systems without authorization.
- Generating or storing working exploits or real malware.
- Attacking production agents you do not own.

If you extend the probe library, keep payloads at the canary level: enough to prove a
control fails, not a weaponized attack.
