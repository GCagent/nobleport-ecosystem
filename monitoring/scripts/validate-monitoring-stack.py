#!/usr/bin/env python3
"""Static validation for the NoblePort monitoring stack.

Runs without a live Prometheus — safe for CI. Checks:

  1. Every alert rule file parses and each alert carries severity + runbook_url.
  2. The Grafana dashboard is valid JSON with at least one templated datasource.
  3. TRUTH GUARD: no file in monitoring/ reintroduces a claim that the Deep
     Truth Audit (TA-2026-05-23) deprecated in deployment_metrics.json.

Exit code is nonzero if any check fails.
"""
from __future__ import annotations

import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parent
RULES_DIR = ROOT / "prometheus" / "rules"
DASHBOARD = ROOT / "grafana" / "dashboards" / "nobleport-ops.json"
METRICS_JSON = REPO / "deployment_metrics.json"

errors: list[str] = []
checked = {"alerts": 0, "files": 0}


def check_rules() -> None:
    for path in sorted(RULES_DIR.glob("*.yml")):
        checked["files"] += 1
        doc = yaml.safe_load(path.read_text())
        if not doc or "groups" not in doc:
            errors.append(f"{path.name}: missing top-level 'groups'")
            continue
        for group in doc["groups"]:
            for rule in group.get("rules", []):
                if "alert" not in rule:
                    continue  # recording rule
                checked["alerts"] += 1
                name = rule["alert"]
                labels = rule.get("labels", {})
                annos = rule.get("annotations", {})
                if "severity" not in labels:
                    errors.append(f"{path.name}:{name}: missing labels.severity")
                if "runbook_url" not in annos:
                    errors.append(f"{path.name}:{name}: missing annotations.runbook_url")
                if "expr" not in rule:
                    errors.append(f"{path.name}:{name}: missing expr")


def check_dashboard() -> None:
    try:
        dash = json.loads(DASHBOARD.read_text())
    except Exception as e:  # noqa: BLE001
        errors.append(f"dashboard: invalid JSON ({e})")
        return
    if not dash.get("panels"):
        errors.append("dashboard: no panels")
    tpl = dash.get("templating", {}).get("list", [])
    if not any(t.get("type") == "datasource" for t in tpl):
        errors.append("dashboard: no templated datasource variable")


def check_truth_guard() -> None:
    """The whole point of the repo's audit culture: don't smuggle deprecated
    claims back in via dashboards or alert text."""
    if not METRICS_JSON.exists():
        errors.append("deployment_metrics.json not found — cannot run truth guard")
        return
    deprecated = json.loads(METRICS_JSON.read_text())["deprecated_claims"]
    # Normalize to lowercase substrings.
    needles = [d.lower() for d in deprecated]
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".yml", ".yaml", ".json", ".md", ".sh", ".py"}:
            continue
        if path.name == pathlib.Path(__file__).name:
            continue  # this validator legitimately references the list
        text = path.read_text(errors="ignore").lower()
        for needle in needles:
            if needle in text:
                errors.append(f"{path.relative_to(ROOT)}: contains DEPRECATED claim '{needle}'")


def main() -> int:
    check_rules()
    check_dashboard()
    check_truth_guard()
    print(f"checked {checked['files']} rule files, {checked['alerts']} alerts, 1 dashboard")
    if errors:
        print(f"\nFAILED — {len(errors)} issue(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK — stack is structurally valid and truth-bounded (TA-2026-05-23).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
