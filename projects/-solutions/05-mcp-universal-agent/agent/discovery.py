"""Stage 1 & 2 of the agent loop: discovery and tool listing.

Discovery reads ``registry.json``, spawns each listed MCP server as a stdio
subprocess and lists the tools it exposes. The result is a flat list of
:class:`ToolInfo` records the rest of the agent works with.

This module owns the lifecycle of every MCP subprocess it spawns. Callers
MUST use it as a context manager (``with discover_servers(...) as ...``) so
that subprocesses are torn down cleanly even on errors.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass
class ToolInfo:
    """A single tool discovered from some MCP server."""

    name: str  # fully-qualified, e.g. "filesystem.read_file"
    server: str  # server name from registry, e.g. "filesystem"
    category: str  # category from registry, e.g. "files"
    tool_name: str  # bare tool name, e.g. "read_file"
    description: str
    input_schema: Dict  # JSON-schema of the tool's arguments

    def short(self) -> str:
        """One-line representation used by the LLM prompt."""
        return f"{self.name}: {self.description.splitlines()[0] if self.description else ''}"


@dataclass
class DiscoveredServer:
    """A live connection to one MCP server plus the tools it exposes."""

    name: str
    category: str
    description: str
    session: ClientSession
    tools: List[ToolInfo] = field(default_factory=list)


@dataclass
class DiscoveryResult:
    """Aggregate of every discovered server + flat tool list."""

    servers: List[DiscoveredServer]
    tools: List[ToolInfo]

    def by_category(self) -> Dict[str, List[ToolInfo]]:
        out: Dict[str, List[ToolInfo]] = {}
        for t in self.tools:
            out.setdefault(t.category, []).append(t)
        return out


def load_registry(registry_path: str | Path = "registry.json") -> List[dict]:
    """Read ``registry.json`` and return the list of server entries."""
    p = Path(registry_path)
    if not p.is_file():
        raise FileNotFoundError(f"Registry not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    servers = data.get("servers") if isinstance(data, dict) else data
    if not isinstance(servers, list):
        raise ValueError("registry.json must contain a top-level 'servers' list")
    return servers


@asynccontextmanager
async def discover_servers(
    registry_path: str | Path = "registry.json",
    only: Optional[List[str]] = None,
) -> AsyncIterator[DiscoveryResult]:
    """Spawn every server in the registry, list its tools, yield a
    :class:`DiscoveryResult`, then tear everything down on exit.

    Args:
        registry_path: Path to ``registry.json``.
        only: Optional list of server names to limit discovery to. Useful for
            tests that only want one or two servers.

    Yields:
        A :class:`DiscoveryResult` with every server connected and every tool
        enumerated.
    """
    entries = load_registry(registry_path)
    if only:
        entries = [e for e in entries if e["name"] in only]
        missing = set(only or []) - {e["name"] for e in entries}
        if missing:
            raise ValueError(f"Servers not found in registry: {missing}")

    spawned: List[tuple] = []  # (cm, session, server_meta)
    servers: List[DiscoveredServer] = []
    tools: List[ToolInfo] = []

    try:
        for entry in entries:
            params = StdioServerParameters(
                command=entry["command"],
                args=list(entry.get("args", [])),
                env={**os.environ, **entry.get("env", {})},
            )
            cm = stdio_client(params)
            read, write = await cm.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            resp = await session.list_tools()
            server_tools = []
            for t in resp.tools:
                # Fully-qualified name avoids collisions across servers.
                fq = f"{entry['name']}.{t.name}"
                ti = ToolInfo(
                    name=fq,
                    server=entry["name"],
                    category=entry.get("category", "misc"),
                    tool_name=t.name,
                    description=t.description or "",
                    input_schema=t.inputSchema or {"type": "object", "properties": {}},
                )
                server_tools.append(ti)
                tools.append(ti)
            ds = DiscoveredServer(
                name=entry["name"],
                category=entry.get("category", "misc"),
                description=entry.get("description", ""),
                session=session,
                tools=server_tools,
            )
            servers.append(ds)
            spawned.append((cm, session))
        yield DiscoveryResult(servers=servers, tools=tools)
    finally:
        # Tear down in reverse order of spawn.
        for cm, session in reversed(spawned):
            try:
                await session.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
            try:
                await cm.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
