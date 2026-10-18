"""Unseen-company validation for rev1 backend-generalization.

Seeds a synthetic company that shares no tenant / function / people names with the
Acme demo (data in `unseen/`, ingested through the normalizer layer) and asserts the
full Scout -> Consolidator -> Fixer pipeline generalizes:

- Slack/Jira normalization lands in the graph (SlackThread ABOUT, Ticket REFERENCES,
  auto-materialized Person for an unmapped Slack author).
- Compliance blocking is data-driven: `reportRegulator` (never in the old hardcoded
  set) blocks because compliance_rules.json lists it.
- `compliance_rules.json` overrides the inline flag: `freezeAccount` is inline
  compliance_critical but NOT listed, so it auto-approves.
- A compliance-critical Decision (via integration_mapping decision_rules) blocks
  `signColdWalletTransaction`.
- Incident + playbook produces CONDITIONAL_APPROVAL (`settleTrade`).
- A function with no experts completes without a crash, AUTO_APPROVED, reviewer None.
- Cross-tenant bridge fires: `evaluateCreditRisk` (nova_risk) has a foreign caller
  `matchOrders` (nova_trade) with memory.
- `/api/tenants` discovers the unseen tenants from the graph.

Runs against isolated `gencheck_*` graphs (GRAPH_PREFIX) so the Acme demo state is
untouched; graphs are removed again at the end.

Run:
    python test_unseen.py
Exit code is non-zero if any assertion fails.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNSEEN_COMPANY = HERE / "unseen" / "company_unseen.json"

# Isolate from the dev demo graphs BEFORE importing db/seed (db reads env at import).
os.environ["GRAPH_PREFIX"] = "gencheck"
os.environ["REPO_NAME"] = "nova_trade"
os.environ["COMPANY_JSON"] = str(UNSEEN_COMPANY)

import seed  # noqa: E402
import tools  # noqa: E402
import agents  # noqa: E402
import api  # noqa: E402
from db import client, knowledge, rows, PREFIX  # noqa: E402

EXPECTED_TENANTS = ["nova_risk", "nova_trade", "nova_wallet"]
ALLOWED_DECISIONS = {"BLOCKED", "CONDITIONAL_APPROVAL", "AUTO_APPROVED"}

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    if not condition:
        failures.append(label)
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")


def q(cypher: str, params: dict | None = None) -> list[dict]:
    return rows(knowledge().ro_query(cypher, params or {}))


def test_normalization() -> None:
    print("\n[N1] Ingestion: Slack + Jira normalized into the knowledge graph")
    slack_about = q(
        "MATCH (s:SlackThread {id:'1759000000.000100'})-[:ABOUT]->(f:Function) "
        "RETURN f.name AS name")
    check("mapped SlackThread ABOUT settleTrade", [r["name"] for r in slack_about] == ["settleTrade"],
          str(slack_about))

    slack_date = q("MATCH (s:SlackThread {id:'1759000000.000100'}) RETURN s.date AS date, s.channel AS channel")
    check("SlackThread has date + channel", bool(slack_date) and slack_date[0]["date"] and slack_date[0]["channel"] == "#risk-alerts",
          str(slack_date))

    posted = q("MATCH (p:Person {id:'mila'})-[:POSTED]->(s:SlackThread {id:'1759000100.000200'}) RETURN p.id AS id")
    check("mapped Slack author posted as Mila", bool(posted), str(posted))

    auto_person = q("MATCH (p:Person {id:'UN0AAA1'}) RETURN p.id AS id, p.team AS team, p.active AS active")
    check("unmapped Slack author materialized as Person", bool(auto_person) and auto_person[0]["team"] is None,
          str(auto_person))

    system_events = q("MATCH (s:SlackThread {id:'1759000200.000300'}) RETURN s.id AS id")
    check("channel_join system event skipped", not system_events, str(system_events))

    jira_mapped = q("MATCH (t:Ticket {id:'NJT-7'})-[:REFERENCES]->(f:Function) RETURN f.name AS name")
    check("mapped Jira ticket REFERENCES settleTrade", [r["name"] for r in jira_mapped] == ["settleTrade"],
          str(jira_mapped))

    jira_label = q("MATCH (t:Ticket {id:'NJT-8'})-[:REFERENCES]->(f:Function) RETURN f.name AS name")
    check("label-fallback Jira ticket REFERENCES signColdWalletTransaction",
          [r["name"] for r in jira_label] == ["signColdWalletTransaction"], str(jira_label))

    ticket_date = q("MATCH (t:Ticket {id:'NJT-7'}) RETURN t.date AS date, t.status AS status")
    check("Jira date truncated to YYYY-MM-DD", bool(ticket_date) and ticket_date[0]["date"] == "2026-06-14",
          str(ticket_date))

    ledger = q("MATCH (s:SlackThread {id:'1759000000.000100'})-[:LED_TO]->(t:Ticket) RETURN t.id AS id")
    check("mapped Slack thread LED_TO NJT-7", ledger and ledger[0]["id"] == "NJT-7", str(ledger))


def test_compliance_paths() -> None:
    print("\n[N2] Data-driven compliance blocking (names never in the old hardcoded set)")
    orchestrator = agents.GovernanceOrchestrator()

    blast = tools.assess_blast_radius("reportRegulator")
    check("reportRegulator is compliance-critical via compliance_rules",
          blast.get("compliance_critical") is True, str(blast.get("compliance_critical")))
    sim = orchestrator.simulate_pr(pr_id="PR-N101", target_function="reportRegulator", repo="nova_risk")
    check("PR-N101 reportRegulator -> BLOCKED", sim["decision"] == "BLOCKED", sim["decision"])

    blast2 = tools.assess_blast_radius("freezeAccount")
    check("freezeAccount inline flag overridden to false by compliance_rules",
          blast2.get("compliance_critical") is False, str(blast2.get("compliance_critical")))
    sim2 = orchestrator.simulate_pr(pr_id="PR-N102", target_function="freezeAccount", repo="nova_risk")
    check("PR-N102 freezeAccount -> AUTO_APPROVED (override path)", sim2["decision"] == "AUTO_APPROVED",
          sim2["decision"])

    blast3 = tools.assess_blast_radius("signColdWalletTransaction")
    check("signColdWalletTransaction critical via Decision D-N001 (mapping rules)",
          blast3.get("compliance_critical") is True and "D-N001" in blast3.get("compliance_decisions", []),
          str(blast3.get("compliance_decisions")))
    sim3 = orchestrator.simulate_pr(pr_id="PR-N105", target_function="signColdWalletTransaction", repo="nova_wallet")
    check("PR-N105 signColdWalletTransaction -> BLOCKED", sim3["decision"] == "BLOCKED", sim3["decision"])


def test_memory_and_experts() -> None:
    print("\n[N3] Incident/playbook memory, verdicts, reviewer fallback")
    orchestrator = agents.GovernanceOrchestrator()

    sim = orchestrator.simulate_pr(pr_id="PR-N103", target_function="settleTrade", repo="nova_trade")
    check("PR-N103 settleTrade -> CONDITIONAL_APPROVAL (incident + playbook)",
          sim["decision"] == "CONDITIONAL_APPROVAL", sim["decision"])

    sim2 = orchestrator.simulate_pr(pr_id="PR-N104", target_function="generateStatement", repo="nova_wallet")
    check("PR-N104 generateStatement -> AUTO_APPROVED (no signal)", sim2["decision"] == "AUTO_APPROVED",
          sim2["decision"])
    check("PR-N104 reviewer is None (no active expert, no crash)", sim2["assigned_reviewer"] is None,
          str(sim2["assigned_reviewer"]))
    stale = sim2["fixer_action"]["action_result"].get("flagged_stale_docs", [])
    check("PR-N104 flagged_stale_docs empty (function has no Doc)", stale == [], str(stale))


def test_cross_tenant() -> None:
    print("\n[N4] Cross-tenant bridge on unseen data")
    orchestrator = agents.GovernanceOrchestrator()
    sim = orchestrator.simulate_pr(pr_id="PR-N106", target_function="evaluateCreditRisk", repo="nova_risk")
    cross = sim["consolidator_findings"]["cross_tenant_data"]
    bridges = cross.get("bridges", [])
    check("PR-N106 has_cross_tenant_risk", cross.get("has_cross_tenant_risk") is True, str(cross))
    check("bridge is nova_trade via matchOrders",
          any(b.get("foreign_tenant") == "nova_trade" and b.get("bridged_function") == "matchOrders"
              for b in bridges),
          str([(b.get("foreign_tenant"), b.get("bridged_function")) for b in bridges]))
    check("PR-N106 verdict is a valid decision", sim["decision"] in ALLOWED_DECISIONS, sim["decision"])


def test_api_tenants() -> None:
    print("\n[N5] /api/tenants tenant discovery on unseen data")
    payload = api.get_tenants()
    ids = sorted(t["id"] for t in payload["tenants"])
    check("discovers all 3 unseen tenants", ids == EXPECTED_TENANTS, str(ids))
    names = {t["id"]: t["name"] for t in payload["tenants"]}
    check("display name comes from company file", names.get("nova_trade") == "Nova Trading Core",
          str(names.get("nova_trade")))
    fns = {t["id"]: t["functions"] for t in payload["tenants"]}
    check("per-tenant function lists are populated", all(fns.get(t) for t in EXPECTED_TENANTS), str(fns))


def cleanup() -> None:
    print("\nCleaning up isolated gencheck_* graphs (dev demo untouched)...")
    graph_names = [f"{PREFIX}_knowledge", f"{PREFIX}_agent_state"] + \
                  [f"{PREFIX}_memory_{t}" for t in EXPECTED_TENANTS]
    for name in graph_names:
        try:
            client().select_graph(name).delete()
        except Exception:
            pass
    print("Cleanup done.")


def main() -> int:
    print("=" * 72)
    print("NexusGuard unseen-company validation (rev1 backend-generalization)")
    print("=" * 72)
    print(f"\nSeeding unseen company into isolated '{PREFIX}' graphs...")
    seed.seed_all(input_path=str(UNSEEN_COMPANY))

    try:
        test_normalization()
        test_compliance_paths()
        test_memory_and_experts()
        test_cross_tenant()
        test_api_tenants()
    finally:
        cleanup()

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
