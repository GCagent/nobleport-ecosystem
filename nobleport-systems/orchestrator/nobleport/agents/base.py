"""Agent base class.

An agent owns a set of catalog modules (its domain) and executes workflow
steps dispatched by the engine. Agents never decide risk policy — the engine
and registry enforce gating before a handle() call ever reaches an agent.

Handlers are plain async methods registered per module name. Modules without
a dedicated handler fall back to a structured acknowledgment, so every catalog
module is invocable from day one and handlers can be deepened incrementally.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

Handler = Callable[[str, dict[str, Any], bool], Awaitable[dict[str, Any]]]


class BaseAgent:
    name: str = "base"

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}
        self.register_handlers()

    def register_handlers(self) -> None:
        """Subclasses register module handlers here via self.on()."""

    def on(self, module: str, handler: Handler) -> None:
        self._handlers[module] = handler

    async def handle(self, module: str, action: str, payload: dict[str, Any],
                     *, simulate: bool) -> dict[str, Any]:
        handler = self._handlers.get(module)
        if handler is None:
            return self._ack(module, action, simulate)
        result = await handler(action, payload, simulate)
        return {**self._ack(module, action, simulate), **result}

    def _ack(self, module: str, action: str, simulate: bool) -> dict[str, Any]:
        return {
            "agent": self.name,
            "module": module,
            "action": action,
            "mode": "SIMULATED" if simulate else "EXECUTED",
        }
