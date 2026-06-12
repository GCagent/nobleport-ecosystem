from core.gateway import registry


def test_fifty_modules_consistent():
    registry.validate()
    assert len(registry.MODULES) == 50


def test_every_tool_belongs_to_a_known_agent():
    for tool in registry.TOOLS:
        assert tool.agent_name in registry.AGENT_NAMES


def test_every_module_owner_is_a_known_agent():
    for module in registry.MODULES:
        assert module.owner_agent in registry.AGENT_NAMES


def test_modules_seed_blocked():
    assert all(m.truth_label == "BLOCKED" for m in registry.MODULES)


def test_l4_tools_are_write_capable_money_legal():
    # capture_customer_approval is the L4 money/legal/permit-critical tool.
    l4 = [t for t in registry.TOOLS if t.approval_level == "L4"]
    assert l4 and all(t.write_capable for t in l4)
