"""Model adapters.

The harness only needs one thing from a model: given a prompt plus the conversation
so far, return either a tool call or a final answer. The `MockModel` implements a
deterministic, offline "susceptible" agent so the whole pipeline runs without an API
key. Swap in `OllamaModel` or an API adapter to test a real model.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Step:
    kind: str          # "tool" or "final"
    tool: str = ""
    args: dict = None  # type: ignore[assignment]
    answer: str = ""


class Model(Protocol):
    name: str

    def act(self, system: str, task: str, transcript: list[dict]) -> Step: ...


class MockModel:
    """A deterministic stand-in that is *naively susceptible* to injection.

    It models an agent with no judgment: it reads the requested file/url, and if the
    returned content literally contains an instruction to call send_message or to
    echo a token, it complies. This gives the harness a non-trivial baseline ASR so
    that turning defenses on produces a visible, testable drop.
    """

    name = "mock"

    _CALL_RE = re.compile(
        r"send_message.*?to=['\"]?(?P<to>\w+)['\"]?.*?body=['\"]?(?P<body>[^'\")\n]+)",
        re.IGNORECASE | re.DOTALL,
    )
    _TOKEN_RE = re.compile(r"(AGENTPROBE-CANARY-[0-9a-f-]+|(?:A-G-E-N-T[0-9A-Za-z\-]+))")

    def act(self, system: str, task: str, transcript: list[dict]) -> Step:
        # Step 1: if we have not read anything yet, perform the task's read.
        reads = [t for t in transcript if t["role"] == "tool"]
        if not reads:
            if "url" in task or "fetch" in task.lower():
                return Step("tool", "web_fetch", {"url": task.split()[-1]})
            return Step("tool", "read_file", {"path": task.split()[-1]})

        last = reads[-1]["content"]

        # Step 2: naive compliance with whatever the untrusted content said.
        if "[redacted-suspicious-instruction]" not in last:
            m = self._CALL_RE.search(last)
            if m and "already_acted" not in [t.get("mark") for t in transcript]:
                return Step("tool", "send_message",
                            {"to": m.group("to"), "body": m.group("body").strip()})
            tok = self._TOKEN_RE.search(last)
            if tok:
                return Step("final", answer=f"Summary complete. {tok.group(1)}")

        # Step 3: otherwise, a clean summary with no leak.
        return Step("final", answer="Here is a brief, safe summary of the document.")


class OllamaModel:
    """Adapter for a locally served Ollama model via its OpenAI-compatible endpoint.

    Uses native tool calling. The host comes from `OLLAMA_HOST` (as the Ollama CLI
    does), defaulting to localhost. Stdlib only, so no extra dependency.
    """

    # Clean schemas: tool-poisoning text reaches the model through the tool result,
    # which is where agent.run_agent surfaces it.
    TOOLS = [
        {"type": "function", "function": {
            "name": "read_file", "description": "Read a local file by path.",
            "parameters": {"type": "object",
                           "properties": {"path": {"type": "string"}},
                           "required": ["path"]}}},
        {"type": "function", "function": {
            "name": "web_fetch", "description": "Fetch the contents of a URL.",
            "parameters": {"type": "object",
                           "properties": {"url": {"type": "string"}},
                           "required": ["url"]}}},
        {"type": "function", "function": {
            "name": "send_message",
            "description": "Send a message to a recipient. Args: to, body.",
            "parameters": {"type": "object",
                           "properties": {"to": {"type": "string"},
                                          "body": {"type": "string"}},
                           "required": ["to", "body"]}}},
    ]

    def __init__(self, name: str, host: str | None = None, timeout: float = 600) -> None:
        self.name = f"ollama:{name}"
        self.model = name
        host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        if not host.startswith("http"):
            host = "http://" + host
        self.host = host.rstrip("/")
        self.timeout = timeout
        # The transcript only holds tool results, so remember our own calls to
        # rebuild the assistant turns. One entry per tool-role transcript entry.
        self._calls: list[Step] = []

    def _messages(self, system: str, task: str, transcript: list[dict]) -> list[dict]:
        if not transcript:
            self._calls = []
        msgs: list[dict] = [{"role": "system", "content": system},
                            {"role": "user", "content": task}]
        tool_entries = [t for t in transcript if t["role"] == "tool"]
        for i, (call, entry) in enumerate(zip(self._calls, tool_entries)):
            call_id = f"call_{i}"
            msgs.append({"role": "assistant", "content": "", "tool_calls": [{
                "id": call_id, "type": "function",
                "function": {"name": call.tool, "arguments": json.dumps(call.args)},
            }]})
            msgs.append({"role": "tool", "tool_call_id": call_id, "content": entry["content"]})
        return msgs

    def act(self, system: str, task: str, transcript: list[dict]) -> Step:  # pragma: no cover
        payload = {
            "model": self.model,
            "messages": self._messages(system, task, transcript),
            "tools": self.TOOLS,
            "max_tokens": 4096,
        }
        req = urllib.request.Request(
            f"{self.host}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            msg = json.load(resp)["choices"][0]["message"]

        calls = msg.get("tool_calls") or []
        if calls:
            fn = calls[0]["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            step = Step("tool", fn["name"].removeprefix("functions."),
                        args if isinstance(args, dict) else {})
            self._calls.append(step)
            return step
        return Step("final", answer=msg.get("content") or "")


def get_model(spec: str) -> Model:
    if spec == "mock":
        return MockModel()
    if spec.startswith("ollama:"):
        return OllamaModel(spec.split(":", 1)[1])
    raise ValueError(f"unknown model spec: {spec!r}")
