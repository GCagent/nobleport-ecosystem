#!/usr/bin/env python3
"""Runtime health check against a live Prometheus.

Queries the instant API for (a) scrape targets that are down and (b) the
governance guardrail counters that must always read zero. Stdlib only.

Usage:
    python3 health-check.py [--prometheus http://localhost:9090] [--window 24h]

Exit codes: 0 healthy · 1 unhealthy · 2 could not reach Prometheus.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

# Counters that represent hard-blocked / launch-gated violations. Any value > 0
# is an incident (see monitoring/prometheus/rules/governance_guardrails.yml).
GUARDRAILS = [
    "nobleport_autonomous_treasury_action_total",
    "nobleport_autonomous_securities_action_total",
    "nobleport_red_gate_execution_total",
    "kuzo_swap_execution_attempt_total",
    "nobleport_ny_blocked_activity_total",
    "nobleport_high_risk_action_auto_approved_total",
]


def query(base: str, expr: str) -> list[dict]:
    url = base.rstrip("/") + "/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(url, timeout=10) as resp:
        body = json.load(resp)
    if body.get("status") != "success":
        raise RuntimeError(f"query failed: {expr}: {body}")
    return body["data"]["result"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prometheus", default="http://localhost:9090")
    ap.add_argument("--window", default="24h")
    args = ap.parse_args()

    try:
        down = query(args.prometheus, "up == 0")
        chain = query(args.prometheus, "min(audit_log_chain_intact)")
    except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
        print(f"ERROR: cannot reach Prometheus at {args.prometheus}: {e}")
        return 2

    problems: list[str] = []

    for series in down:
        m = series["metric"]
        problems.append(f"target DOWN: {m.get('job', '?')} / {m.get('instance', '?')}")

    for metric in GUARDRAILS:
        res = query(args.prometheus, f"sum(increase({metric}[{args.window}]))")
        val = float(res[0]["value"][1]) if res else 0.0
        status = "OK" if val == 0 else "VIOLATION"
        print(f"  guardrail {metric}: {val:g}  [{status}]")
        if val > 0:
            problems.append(f"GUARDRAIL VIOLATION: {metric} = {val:g} over {args.window}")

    if chain and float(chain[0]["value"][1]) < 1:
        problems.append("AUDIT CHAIN BROKEN: audit_log_chain_intact < 1")

    if problems:
        print(f"\nUNHEALTHY — {len(problems)} issue(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nHEALTHY — all targets up, all guardrails at zero, audit chain intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
