"""Module registry: discovery, lookup, and health state for catalog modules."""

from __future__ import annotations

from dataclasses import dataclass

from nobleport.modules import CATALOG, ModuleSpec, Risk, Status


class UnknownModuleError(KeyError):
    pass


@dataclass
class ModuleHealth:
    healthy: bool = True
    consecutive_failures: int = 0
    tripped: bool = False  # circuit breaker open


class ModuleRegistry:
    """In-process registry over the static catalog plus runtime health.

    The registry is the single authority workflows consult before invoking a
    module: it answers "does this module exist", "may it execute effects",
    and "is it currently healthy".
    """

    BREAKER_THRESHOLD = 3

    def __init__(self, catalog: tuple[ModuleSpec, ...] = CATALOG):
        self._modules: dict[str, ModuleSpec] = {}
        self._health: dict[str, ModuleHealth] = {}
        for spec in catalog:
            self.register(spec)

    def register(self, spec: ModuleSpec) -> None:
        if spec.name in self._modules:
            raise ValueError(f"duplicate module name: {spec.name}")
        self._modules[spec.name] = spec
        self._health[spec.name] = ModuleHealth()

    def get(self, name: str) -> ModuleSpec:
        try:
            return self._modules[name]
        except KeyError:
            raise UnknownModuleError(name) from None

    def all(self) -> list[ModuleSpec]:
        return list(self._modules.values())

    def by_agent(self, agent: str) -> list[ModuleSpec]:
        return [m for m in self._modules.values() if m.agent == agent]

    def by_cluster(self, cluster: str) -> list[ModuleSpec]:
        return [m for m in self._modules.values() if m.cluster == cluster]

    # -- execution policy ----------------------------------------------------

    def may_execute_effects(self, name: str) -> bool:
        """True if the module is allowed to emit state-changing effects.

        READ_ONLY modules never may; STAGED modules run in simulation, so
        their 'effects' are recorded but not applied. Only LIVE modules with
        a closed breaker execute for real.
        """
        spec = self.get(name)
        health = self._health[name]
        return spec.status is Status.LIVE and not health.tripped

    def requires_human_gate(self, name: str) -> bool:
        return self.get(name).risk in (Risk.HIGH, Risk.CRITICAL)

    def is_hard_blocked_autonomous(self, name: str) -> bool:
        """CRITICAL modules (treasury/securities) can never run autonomously,
        even with a recorded approval — execution happens off-platform via
        human multi-sig, the platform only prepares and records."""
        return self.get(name).risk is Risk.CRITICAL

    # -- health / circuit breaker ---------------------------------------------

    def health(self, name: str) -> ModuleHealth:
        self.get(name)
        return self._health[name]

    def record_success(self, name: str) -> None:
        h = self.health(name)
        h.healthy = True
        h.consecutive_failures = 0
        h.tripped = False

    def record_failure(self, name: str) -> None:
        h = self.health(name)
        h.healthy = False
        h.consecutive_failures += 1
        if h.consecutive_failures >= self.BREAKER_THRESHOLD:
            h.tripped = True
