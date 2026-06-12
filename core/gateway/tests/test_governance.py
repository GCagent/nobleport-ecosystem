from core.gateway.config import settings
from core.gateway.envelope import McpEnvelope
from core.gateway.governance import GovernanceGate


def gate():
    return GovernanceGate(settings.launch_gates_path, max_message_chars=2000)


def env(**kw):
    base = dict(requesting_agent="Stephanie.ai", target_agent="GCagent.ai",
                module="Estimate Engine", action="gcagent.price_estimate")
    base.update(kw)
    return McpEnvelope(**base)


def test_clean_call_permitted():
    out = gate().evaluate(env(message="Explain contractor deposits"))
    assert out.decision == "PERMIT"


def test_prohibited_claim_blocked_l4():
    out = gate().evaluate(env(message="guaranteed returns on real estate"))
    assert out.decision == "BLOCK"
    assert out.level == "L4"


def test_unknown_agent_blocked_l0():
    out = gate().evaluate(env(target_agent="Rogue.ai"))
    assert out.decision == "BLOCK"
    assert out.level == "L0"


def test_oversize_message_blocked_l2():
    out = gate().evaluate(env(message="x" * 2001))
    assert out.decision == "BLOCK"
    assert out.level == "L2"


def test_red_gate_scope_blocked():
    out = gate().evaluate(env(module="nbpt_sale", action="kuzo.capture_lead",
                              target_agent="Kuzo.io"))
    assert out.decision == "BLOCK"
    assert out.level == "L4"


def test_ny_geo_block():
    out = gate().evaluate(env(action="kuzo_swap", module="kuzo_swap",
                              target_agent="Kuzo.io", requestor_region="NY"))
    assert out.decision == "BLOCK"
    assert out.level == "L3"


def test_l4_write_without_signature_parks():
    out = gate().evaluate(env(target_agent="Kuzo.io", module="Approval Queue",
                              action="kuzo.capture_customer_approval",
                              approval_level="L4", message="approve deposit"))
    assert out.decision == "PARK"
    assert out.requires_human is True


def test_l4_write_with_signature_permitted():
    out = gate().evaluate(env(target_agent="Kuzo.io", module="Approval Queue",
                              action="kuzo.capture_customer_approval",
                              approval_level="L4", human_signature="sig-abc",
                              message="approve deposit"))
    assert out.decision == "PERMIT"
