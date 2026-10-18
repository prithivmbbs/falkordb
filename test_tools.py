"""Test and demonstrate all FastMCP tools without needing an external MCP client.

Run:
    python test_tools.py
"""
import json

try:
    import tools
except ImportError:
    from files import tools


def run_checks():
    target_fn = "applyDiscount"
    test_pr = "PR-904"

    print("=" * 60)
    print(f"1. ASSESS BLAST RADIUS FOR '{target_fn}'")
    print("=" * 60)
    blast = tools.assess_blast_radius(target_fn)
    print(json.dumps(blast, indent=2))

    print("\n" + "=" * 60)
    print(f"2. FIND TRUE EXPERT FOR '{target_fn}'")
    print("=" * 60)
    experts = tools.find_true_expert(target_fn)
    print(json.dumps(experts, indent=2))

    print("\n" + "=" * 60)
    print(f"3. GET DECISION PROVENANCE CHAIN FOR '{target_fn}'")
    print("=" * 60)
    decisions = tools.get_decision_chain(target_fn)
    print(json.dumps(decisions, indent=2))

    print("\n" + "=" * 60)
    print(f"4. GET AGENT MEMORY CONTEXT (Episodic, Semantic, Procedural)")
    print("=" * 60)
    memories = tools.get_memory_context(target_fn)
    print(json.dumps(memories, indent=2))

    print("\n" + "=" * 60)
    print(f"5. RECORD SCOUT-AGENT RISK FINDING ON '{test_pr}'")
    print("=" * 60)
    finding = tools.write_risk_finding(
        pr_id=test_pr,
        function=target_fn,
        risk_level="HIGH",
        summary="Modifies critical contractual discount branch linked to Client X and INC-77."
    )
    print(json.dumps(finding, indent=2))

    print("\n" + "=" * 60)
    print(f"6. EXECUTE FIXER-AGENT AUTONOMOUS GOVERNANCE ACTION")
    print("=" * 60)
    gov = tools.block_or_approve_pr(
        pr_id=test_pr,
        function=target_fn,
        decision="BLOCKED",
        reviewer_name="Priya",
        risk_level="HIGH"
    )
    print(json.dumps(gov, indent=2))

    print("\n" + "=" * 60)
    print(f"7. TRACK 02: BLACKBOARD WORKING-MEMORY TOKEN COORDINATION")
    print("=" * 60)
    sess_id = "SES-TEST-001"
    tok = tools.record_blackboard_token(
        session_id=sess_id,
        from_agent="Scout-Agent",
        to_agent="Consolidator-Agent",
        phase="SCOUT_HANDOFF",
        message="Risk assessed as HIGH. 7 callers found.",
        payload={"risk": "HIGH", "callers": 7}
    )
    print("Posted Token:", json.dumps(tok, indent=2))
    bb = tools.get_blackboard_session(sess_id)
    print("Retrieved Blackboard Session:", json.dumps(bb, indent=2))

    print("\n" + "=" * 60)
    print(f"8. TRACK 02: CROSS-TENANT MEMORY COORDINATION BRIDGE")
    print("=" * 60)
    cross = tools.query_cross_tenant_memory("applyDiscount", primary_tenant="acme_checkout")
    print(json.dumps(cross, indent=2))

    print("\n" + "=" * 60)
    print(f"9. TRACK 02: DYNAMIC MEMORY CONSOLIDATION ('TEACH THE BRAIN')")
    print("=" * 60)
    cons = tools.consolidate_new_learning(
        repo="acme_checkout",
        function="applyDiscount",
        incident_id="I-TEST-999",
        summary="Automated integration test discovered edge-case race condition.",
        loss_usd=7500,
        playbook_title="Test Automated Verification Playbook",
        playbook_steps=["Step 1: Check edge condition", "Step 2: Run test suite"]
    )
    print(json.dumps(cons, indent=2))


if __name__ == "__main__":
    run_checks()

