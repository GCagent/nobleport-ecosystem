import pytest
from pydantic import ValidationError

from core.gateway.envelope import McpEnvelope


def test_minimal_envelope_defaults():
    env = McpEnvelope(requesting_agent="Stephanie.ai", target_agent="GCagent.ai",
                      module="Estimate Engine", action="gcagent.price_estimate")
    assert env.run_id is not None
    assert env.approval_level == "L0"
    assert env.audit_required is True
    assert env.truth_label == "STAGED"


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        McpEnvelope(requesting_agent="Stephanie.ai")  # missing target/module/action


def test_normalized_level_clamps_garbage():
    env = McpEnvelope(requesting_agent="a", target_agent="b", module="c",
                      action="d", approval_level="bogus")
    assert env.normalized_level() == "L0"


def test_normalized_level_uppercases():
    env = McpEnvelope(requesting_agent="a", target_agent="b", module="c",
                      action="d", approval_level="l4")
    assert env.normalized_level() == "L4"
