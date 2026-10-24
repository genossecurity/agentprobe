"""Tools exposed to the target agent.

All tools are local and side-effect-free with respect to the outside world. The one
"sensitive" tool, `send_message`, only records the call so an oracle can inspect it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class ToolResult:
    ok: bool
    content: str


@dataclass
class Tool:
    name: str
    description: str
    run: Callable[[dict], ToolResult]


class ToolBox:
    """Holds the tools and a ledger of sensitive calls for the oracle to inspect."""

    def __init__(self, fixtures_dir: str) -> None:
        self.fixtures_dir = fixtures_dir
        self.sent_messages: list[ToolCall] = []
        self._tools: dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        def read_file(args: dict) -> ToolResult:
            name = os.path.basename(str(args.get("path", "")))
            path = os.path.join(self.fixtures_dir, name)
            if not name or not os.path.isfile(path):
                return ToolResult(False, f"no such file: {name}")
            with open(path, "r", encoding="utf-8") as fh:
                return ToolResult(True, fh.read())

        def web_fetch(args: dict) -> ToolResult:
            # Local-only: 'url' maps to a fixture filename, never a live request.
            name = os.path.basename(str(args.get("url", "")).rstrip("/")) or "index.html"
            path = os.path.join(self.fixtures_dir, name)
            if not os.path.isfile(path):
                return ToolResult(False, f"unreachable (no local fixture): {name}")
            with open(path, "r", encoding="utf-8") as fh:
                return ToolResult(True, fh.read())

        def send_message(args: dict) -> ToolResult:
            # Stub: records the attempt, sends nothing.
            self.sent_messages.append(ToolCall("send_message", dict(args)))
            return ToolResult(True, "queued (stub)")

        self._tools = {
            "read_file": Tool("read_file", "Read a local file by path.", read_file),
            "web_fetch": Tool(
                "web_fetch", "Fetch the contents of a URL.", web_fetch
            ),
            "send_message": Tool(
                "send_message",
                "Send a message to a recipient. Args: to, body.",
                send_message,
            ),
        }

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def describe(self, poisoned: dict[str, str] | None = None) -> list[dict]:
        """Return tool schemas. `poisoned` can append text to a tool's description
        to model a tool-poisoning probe."""
        poisoned = poisoned or {}
        out = []
        for name, tool in self._tools.items():
            desc = tool.description + poisoned.get(name, "")
            out.append({"name": name, "description": desc})
        return out

    def reset(self) -> None:
        self.sent_messages.clear()
