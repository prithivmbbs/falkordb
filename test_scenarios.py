"""Scenario regression tests for the NexusGuard backend (rev1 backend-parity).

Verifies the 8 benchmark scenarios documented in README.md / walkthrough.md produce the
expected governance verdicts, plus the rev1 parity fixes:

- Fix 0: risk severity -> governance decision mapping (8 scenario decisions)
- Fix 1: MCP `get_memory_context` accepts a `repo` parameter
- Fix 2: `GET /api/tenants` returns all 3 tenants
- Fix 4: cross-tenant bridge fires for verifyJwtToken (foreign caller refundOrder)
- Fix 5: null-Doc guard in `block_or_approve_pr` (renderCart has no Doc)

Run (requires a live FalkorDB + seeded env):
    python test_scenarios.py

The script re-seeds the graphs before and after the run so the demo state stays pristine.
Exit code is non-zero if any assertion fails.
"""
import inspect
import sys

import seed
import tools
from agents import GovernanceOrchestrator

# (pr_id, function, repo, expected_decision, expected_reviewer)
SCENARIOS = [
    ("PR-904", "applyDiscount", "acme_checkout", "BLOCKED", "Priya"),
    ("PR-512", "chargeStripeInvoice", "acme_checkout", "CONDITIONAL_APPROVAL", "Nina"),
    ("PR-108", "renderCart", "acme_checkout", "AUTO_APPROVED", "Dev"),
    ("PR-401", "verifyJwtToken", "acme_auth", "BLOCKED", "Alice"),
    ("PR-770", "refundOrder", "acme_checkout", "CONDITIONAL_APPROVAL", "Priya"),
    ("PR-330", "hardDeleteAccount", "acme_data", "BLOCKED", "Marcus"),
    ("PR-610", "rateLimitRedisBucket", "acme_checkout", "CONDITIONAL_APPROVAL", "Elena"),
    ("PR-350", "encryptPiiField", "acme_data", "CONDITIONAL_APPROVAL", "Leila"),
]

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    if not condition:
        failures.append(label)
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")


def warn(label: str, condition: bool, detail: str = "") -> None:
    status = "OK" if condition else "WARN"
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")


def test_scenario_decisions() -> None:
    print("\n[Fix 0] 8 benchmark scenario verdicts (GovernanceOrchestrator.simulate_pr)")
    orchestrator = GovernanceOrchestrator()
    for pr_id, fn, repo, expected, expected_reviewer in SCENARIOS:
        sim = orchestrator.simulate_pr(pr_id=pr_id, target_function=fn, repo=repo)
        decision = sim["decision"]
        check(
            f"{pr_id} {repo}/{fn} -> {expected}",
            decision == expected,
            f"got {decision} (risk={sim['risk_level']}, reviewer={sim['assigned_reviewer']})",
        )
        warn(
            f"{pr_id} reviewer {expected_reviewer}",
            sim["assigned_reviewer"] == expected_reviewer,
            f"got {sim['assigned_reviewer']}",
        )

        if pr_id == "PR-108":
            stale = sim["fixer_action"]["action_result"].get("flagged_stale_docs", [])
            check("[Fix 5] PR-108 renderCart stale docs empty (null-Doc guard)", stale == [], f"got {stale}")

        if pr_id == "PR-401":
            cross = sim["consolidator_findings"]["cross_tenant_data"]
            bridges = cross.get("bridges", [])
            check(
                "[Fix 4] PR-401 cross-tenant bridge detected",
                bool(cross.get("has_cross_tenant_risk")) and any(
                    b.get("bridged_function") == "refundOrder" and b.get("foreign_tenant") == "acme_checkout"
                    for b in bridges
                ),
                f"bridges={[b.get('foreign_tenant') + ':' + b.get('bridged_function', '') for b in bridges]}",
            )


def test_memory_context_tenants() -> None:
    print("\n[Fix 1] get_memory_context works per tenant")
    m_checkout = tools.get_memory_context("applyDiscount", repo="acme_checkout")
    m_auth = tools.get_memory_context("verifyJwtToken", repo="acme_auth")
    m_data = tools.get_memory_context("hardDeleteAccount", repo="acme_data")
    check(
        "acme_checkout applyDiscount has I-007",
        any(i.get("incident_id") == "I-007" for i in m_checkout["episodic_memory"]["past_incidents"]),
    )
    check(
        "acme_auth verifyJwtToken has I-010",
        any(i.get("incident_id") == "I-010" for i in m_auth["episodic_memory"]["past_incidents"]),
    )
    check(
        "acme_data hardDeleteAccount has I-033",
        any(i.get("incident_id") == "I-033" for i in m_data["episodic_memory"]["past_incidents"]),
    )

    import mcp_server

    target = getattr(mcp_server.get_memory_context, "fn", mcp_server.get_memory_context)
    sig = inspect.signature(target)
    check("MCP get_memory_context exposes 'repo'", "repo" in sig.parameters, str(sig))


def test_api_tenants() -> None:
    print("\n[Fix 2] /api/tenants lists all tenants")
    import api

    tenants = [t["id"] for t in api.get_tenants()["tenants"]]
    check("API returns 3 tenants", len(tenants) == 3, f"got {tenants}")
    check("acme_data present", "acme_data" in tenants)


def main() -> int:
    print("=" * 72)
    print("NexusGuard scenario regression tests (rev1 backend-parity)")
    print("=" * 72)
    print("\nSeeding graphs for a deterministic test run...")
    seed.seed_all()

    try:
        test_scenario_decisions()
        test_memory_context_tenants()
        test_api_tenants()
    finally:
        print("\nRe-seeding graphs to restore clean demo state...")
        seed.seed_all()

    print("\n" + "=" * 72)
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
