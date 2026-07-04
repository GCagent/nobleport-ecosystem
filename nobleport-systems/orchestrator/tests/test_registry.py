from nobleport.modules import CATALOG, Risk, Status
from nobleport.registry import ModuleRegistry, UnknownModuleError

import pytest


def test_catalog_has_fifty_plus_modules():
    assert len(CATALOG) >= 50


def test_catalog_names_unique():
    names = [m.name for m in CATALOG]
    assert len(names) == len(set(names))


def test_every_module_has_known_agent():
    agents = {"stephanie", "gcagent", "permitstream", "cyborg"}
    assert {m.agent for m in CATALOG} <= agents


def test_treasury_surfaces_are_critical():
    reg = ModuleRegistry()
    for name in ("finance.payout_release", "token.mint_burn"):
        assert reg.is_hard_blocked_autonomous(name)
        assert reg.requires_human_gate(name)


def test_read_only_modules_never_execute_effects():
    reg = ModuleRegistry()
    for m in CATALOG:
        if m.status is Status.READ_ONLY:
            assert not reg.may_execute_effects(m.name)


def test_staged_modules_never_execute_effects():
    reg = ModuleRegistry()
    for m in CATALOG:
        if m.status is Status.STAGED:
            assert not reg.may_execute_effects(m.name)


def test_unknown_module_raises():
    reg = ModuleRegistry()
    with pytest.raises(UnknownModuleError):
        reg.get("nope.nothing")


def test_circuit_breaker_trips_after_threshold():
    reg = ModuleRegistry()
    name = "intake.lead_capture"
    assert reg.may_execute_effects(name)
    for _ in range(ModuleRegistry.BREAKER_THRESHOLD):
        reg.record_failure(name)
    assert reg.health(name).tripped
    assert not reg.may_execute_effects(name)
    reg.record_success(name)
    assert reg.may_execute_effects(name)
