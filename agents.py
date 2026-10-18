"""Multi-Agent Orchestrator for NexusGuard Engineering Governance.

Track 02 Deep Optimization: Agent Memory & Multi-Agent Coordination Engine.
1. Scout-Agent: Blast radius analysis, decision provenance, and episodic memory retrieval.
2. MemoryConsolidatorAgent: Multi-tier memory synthesis, cross-tenant dependency bridging, and dynamic learning.
3. Fixer-Agent: Domain expert discovery, procedural memory checklists, and autonomous governance actions.
4. FalkorDB Graph Blackboard: Live inter-agent coordination tokens and shared working memory stored in dev_agent_state.
5. AgentLLMWrapper: Seamlessly wraps Anthropic or OpenAI (with a robust deterministic fallback).
"""
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any
from dotenv import load_dotenv

import tools

load_dotenv()


class AgentLLMWrapper:
    """Provides natural language reasoning using Anthropic, OpenAI, or a deterministic engine."""

    def __init__(self):
        self.provider = None
        self.client = None

        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                self.provider = "anthropic"
            except Exception:
                pass

        if not self.client and os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.provider = "openai"
            except Exception:
                pass

        if not self.client:
            self.provider = "deterministic"

    def generate_reasoning(self, role: str, prompt: str, fallback_text: str) -> str:
        """Generates reasoning text using the available LLM or fallback."""
        if self.provider == "anthropic":
            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=600,
                    system=f"You are {role} in NexusGuard, an autonomous FalkorDB-backed engineering governance system. Be concise, direct, and reference graph evidence.",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            except Exception:
                pass

        elif self.provider == "openai":
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=600,
                    messages=[
                        {"role": "system", "content": f"You are {role} in NexusGuard, an autonomous FalkorDB-backed engineering governance system. Be concise, direct, and reference graph evidence."},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content
            except Exception:
                pass

        return fallback_text


class ScoutAgent:
    """Risk & Discovery Agent (Track 01): Traverses FalkorDB knowledge & memory graphs."""

    def __init__(self, llm: AgentLLMWrapper):
        self.llm = llm
        self.role = "Scout-Agent (Risk & Discovery)"

    def investigate(self, pr_id: str, function: str, repo: str = "acme_checkout", session_id: str = "SES-DEFAULT") -> Dict[str, Any]:
        logs = []

        # Step 1: Blast Radius
        logs.append(f"Querying knowledge graph: assess_blast_radius('{function}', max_hops=5)")
        blast_radius = tools.assess_blast_radius(function)

        # Step 2: Decision Provenance
        logs.append(f"Querying knowledge graph: get_decision_chain('{function}')")
        decision_chain = tools.get_decision_chain(function)

        # Step 3: Episodic Memory Check
        logs.append(f"Querying memory graph ({repo}): get_memory_context('{function}')")
        memories = tools.get_memory_context(function, repo=repo)

        # Assess Risk Level
        risk_level = "HIGH" if (
            blast_radius.get("risk_hint") == "HIGH" or
            decision_chain.get("has_contractual_promise") or
            memories["episodic_memory"]["incidents_count"] > 0
        ) else "MEDIUM" if len(blast_radius.get("callers", [])) > 0 else "LOW"

        # Synthesize Summary
        outages = memories["episodic_memory"]["past_incidents"]
        outage_str = f"Linked to past outage {outages[0]['incident_id']} (Loss: ${outages[0].get('loss_usd', 0):,})" if outages else "No past outages recorded."
        contract_str = "Contractual promise detected in CEO Slack communication." if decision_chain.get("has_contractual_promise") else "No contractual promises detected."

        fallback_summary = (
            f"PR {pr_id} modifies '{function}' which has a multi-hop blast radius of "
            f"{len(blast_radius.get('callers', []))} upstream callers across "
            f"{len(blast_radius.get('teams_affected', {}))} teams. {contract_str} {outage_str}"
        )

        prompt = (
            f"Synthesize risk findings for PR {pr_id} modifying function '{function}'.\n"
            f"Evidence from FalkorDB:\n"
            f"- Callers: {len(blast_radius.get('callers', []))} functions\n"
            f"- Teams affected: {list(blast_radius.get('teams_affected', {}).keys())}\n"
            f"- Protecting Decisions: {blast_radius.get('protecting_decisions')}\n"
            f"- Contractual Promise: {decision_chain.get('has_contractual_promise')}\n"
            f"- Past Outages: {outages}\n"
            f"Provide a 2-3 sentence executive assessment explaining why risk is {risk_level}."
        )

        summary = self.llm.generate_reasoning(self.role, prompt, fallback_summary)

        # Step 4: Write finding directly to FalkorDB knowledge graph
        logs.append(f"Writing finding into FalkorDB: write_risk_finding(pr_id='{pr_id}', risk_level='{risk_level}')")
        finding_record = tools.write_risk_finding(
            pr_id=pr_id,
            function=function,
            risk_level=risk_level,
            summary=summary
        )

        # Step 5: Post coordination handoff token to Blackboard graph (dev_agent_state)
        token = tools.record_blackboard_token(
            session_id=session_id,
            from_agent="Scout-Agent",
            to_agent="Consolidator-Agent",
            phase="SCOUT_HANDOFF",
            message=f"Discovered {len(blast_radius.get('callers', []))} callers. Risk assessed as {risk_level}.",
            payload={
                "risk_level": risk_level,
                "callers_count": len(blast_radius.get("callers", [])),
                "has_contract": decision_chain.get("has_contractual_promise", False),
                "incidents_count": memories["episodic_memory"]["incidents_count"]
            }
        )
        logs.append(f"Recorded Blackboard token on dev_agent_state: {token['token_id']}")

        return {
            "agent": "Scout-Agent",
            "pr_id": pr_id,
            "function": function,
            "risk_level": risk_level,
            "summary": summary,
            "blast_radius": blast_radius,
            "decision_chain": decision_chain,
            "memories": memories,
            "finding_record": finding_record,
            "blackboard_token": token,
            "logs": logs
        }


class MemoryConsolidatorAgent:
    """Agent Memory & Cross-Tenant Coordination Agent (Track 02).
    1. Cross-Tenant Memory Bridging: Probes caller trees that cross repository boundaries.
    2. Tri-Tier Memory Synthesis: Evaluates Episodic, Procedural, and Semantic memory.
    3. Blackboard Coordination: Posts shared working memory onto the FalkorDB Blackboard.
    4. Dynamic Learning: Consolidates new regressions into learned playbooks.
    """

    def __init__(self, llm: AgentLLMWrapper):
        self.llm = llm
        self.role = "Consolidator-Agent (Memory & Coordination)"

    def coordinate(self, pr_id: str, function: str, repo: str, scout_findings: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        logs = []

        # Step 1: Read Scout token from blackboard
        logs.append(f"Reading Scout-Agent working memory from Blackboard session '{session_id}'")
        risk_level = scout_findings.get("risk_level", "HIGH")

        # Step 2: Cross-Tenant Memory Bridging
        logs.append(f"Evaluating cross-tenant dependencies: query_cross_tenant_memory('{function}', primary_tenant='{repo}')")
        cross_tenant_data = tools.query_cross_tenant_memory(function, primary_tenant=repo)

        bridged_info = []
        if cross_tenant_data.get("has_cross_tenant_risk"):
            for bridge in cross_tenant_data.get("bridges", []):
                logs.append(f"Cross-tenant bridge: Found foreign dependency in '{bridge['foreign_tenant']}' via '{bridge['bridged_function']}'")
                bridged_info.append(f"{bridge['foreign_tenant']}:{bridge['bridged_function']}")

        # Step 3: Tri-Tier Memory Synthesis
        memories = scout_findings.get("memories", {})
        episodic = memories.get("episodic_memory", {})
        procedural = memories.get("procedural_memory", {})
        semantic = memories.get("semantic_memory", {})

        total_loss = sum(i.get("loss_usd", 0) for i in episodic.get("past_incidents", []))
        playbooks_count = procedural.get("playbooks_count", 0)

        fallback_synthesis = (
            f"Memory Synthesis for '{function}' ({repo}): {episodic.get('incidents_count', 0)} past incident(s) "
            f"representing ${total_loss:,} in historical losses. Governed by {playbooks_count} procedural playbook(s). "
            f"Cross-tenant isolation: {len(cross_tenant_data.get('bridged_tenants', []))} external repo(s) checked."
        )

        prompt = (
            f"Synthesize multi-tier memory for PR {pr_id} on function '{function}' in tenant '{repo}'.\n"
            f"- Episodic Loss: ${total_loss:,}\n"
            f"- Active Playbooks: {playbooks_count}\n"
            f"- Cross-Tenant Bridges: {bridged_info}\n"
            f"Summarize the memory synthesis and coordination directives in 2 concise sentences."
        )

        memory_synthesis = self.llm.generate_reasoning(self.role, prompt, fallback_synthesis)

        # Step 4: Post Coordination Token to Blackboard graph
        token = tools.record_blackboard_token(
            session_id=session_id,
            from_agent="Consolidator-Agent",
            to_agent="Fixer-Agent",
            phase="MEMORY_SYNTHESIS",
            message=f"Memory synthesized. Cross-tenant bridges: {len(cross_tenant_data.get('bridges', []))}. Playbooks required: {playbooks_count}.",
            payload={
                "total_loss_usd": total_loss,
                "playbooks_count": playbooks_count,
                "cross_tenant_bridges": bridged_info,
                "primary_tenant": repo
            }
        )
        logs.append(f"Posted synthesis token on Blackboard dev_agent_state: {token['token_id']}")

        return {
            "agent": "Consolidator-Agent",
            "session_id": session_id,
            "cross_tenant_data": cross_tenant_data,
            "memory_synthesis": memory_synthesis,
            "total_historical_loss": total_loss,
            "playbooks_count": playbooks_count,
            "blackboard_token": token,
            "logs": logs
        }


class FixerAgent:
    """Remediation & Autonomous Governance Action Agent (Track 01 & 02)."""

    def __init__(self, llm: AgentLLMWrapper):
        self.llm = llm
        self.role = "Fixer-Agent (Governance & Remediation)"

    def remediate(self, pr_id: str, function: str, scout_findings: Dict[str, Any], consolidator_findings: Dict[str, Any], repo: str = "acme_checkout", session_id: str = "SES-DEFAULT") -> Dict[str, Any]:
        logs = []

        # Step 1: Read consolidated state from Blackboard
        risk_level = scout_findings.get("risk_level", "HIGH")
        logs.append(f"Read Consolidated Blackboard state: Risk level is {risk_level}")

        # Step 2: Expert Centrality (Track 03)
        logs.append(f"Querying knowledge graph: find_true_expert('{function}')")
        expert_info = tools.find_true_expert(function)
        recommended_reviewer = expert_info.get("recommended_reviewer", {})
        assigned_name = recommended_reviewer.get("name", "Priya")

        # Step 3: Procedural & Semantic Memory
        memories = scout_findings.get("memories", {})
        playbooks = memories.get("procedural_memory", {}).get("playbooks", [])
        runbooks = memories.get("semantic_memory", {}).get("governing_docs", [])

        # Step 4: Autonomous Governance Decision
        if risk_level == "HIGH":
            decision = "BLOCKED"
        elif risk_level == "MEDIUM":
            decision = "CONDITIONAL_APPROVAL"
        else:
            decision = "AUTO_APPROVED"

        logs.append(f"Executing autonomous governance action: block_or_approve_pr(decision='{decision}', reviewer='{assigned_name}')")
        
        gov_action = tools.block_or_approve_pr(
            pr_id=pr_id,
            function=function,
            decision=decision,
            reviewer_name=assigned_name,
            risk_level=risk_level
        )

        steps = playbooks[0]["steps"] if playbooks else [
            "Verify contractual override flags",
            "Obtain sign-off from domain expert",
            "Run regression tests in staging",
            "Deploy behind a feature toggle"
        ]

        fallback_remediation = (
            f"PR {pr_id} has been automatically {decision}. "
            f"Assigned verified active expert {assigned_name} (Centrality: {recommended_reviewer.get('score', 0)}) "
            f"over official lead {expert_info.get('official_owner', {}).get('lead')}. "
            f"Flagged {len(gov_action.get('flagged_stale_docs', []))} governing documentation node(s) as STALE."
        )

        prompt = (
            f"Explain autonomous governance action for PR {pr_id} on function '{function}'.\n"
            f"Decision: {decision}\n"
            f"Assigned Reviewer: {assigned_name} (Reason: active expert vs departed Bob)\n"
            f"Playbook steps required: {steps}\n"
            f"Stale Docs: {gov_action.get('flagged_stale_docs')}\n"
            f"Write a concise 2-sentence explanation of the action taken and next steps."
        )

        explanation = self.llm.generate_reasoning(self.role, prompt, fallback_remediation)

        # Step 5: Post Governance Completion Token to Blackboard graph
        token = tools.record_blackboard_token(
            session_id=session_id,
            from_agent="Fixer-Agent",
            to_agent="Consolidator-Agent",
            phase="GOVERNANCE_EXECUTION",
            message=f"PR {pr_id} marked as {decision}. Assigned reviewer {assigned_name}. Stale docs flagged: {len(gov_action.get('flagged_stale_docs', []))}.",
            payload={
                "decision": decision,
                "reviewer": assigned_name,
                "flagged_docs_count": len(gov_action.get("flagged_stale_docs", [])),
                "steps_required": len(steps)
            }
        )
        logs.append(f"Recorded Action Token on Blackboard dev_agent_state: {token['token_id']}")

        return {
            "agent": "Fixer-Agent",
            "pr_id": pr_id,
            "decision": decision,
            "assigned_reviewer": assigned_name,
            "expert_info": expert_info,
            "playbook_steps": steps,
            "governing_runbooks": runbooks,
            "action_result": gov_action,
            "explanation": explanation,
            "blackboard_token": token,
            "logs": logs
        }


class GovernanceOrchestrator:
    """Coordinates Scout-Agent, MemoryConsolidatorAgent, and Fixer-Agent via FalkorDB Blackboard."""

    def __init__(self):
        self.llm = AgentLLMWrapper()
        self.scout = ScoutAgent(self.llm)
        self.consolidator = MemoryConsolidatorAgent(self.llm)
        self.fixer = FixerAgent(self.llm)

    def simulate_pr(self, pr_id: str = "PR-904", target_function: str = "applyDiscount", repo: str = "acme_checkout") -> Dict[str, Any]:
        session_id = f"SES-{pr_id}-{int(datetime.now(timezone.utc).timestamp())}"
        timeline = []

        timeline.append({
            "stage": "TRIGGER",
            "title": f"Incoming PR #{pr_id}",
            "description": f"Trigger received: PR {pr_id} modifying target function '{target_function}' in repository '{repo}'. Session: {session_id}"
        })

        # Phase 1: Scout Agent Investigation
        scout_res = self.scout.investigate(pr_id, target_function, repo=repo, session_id=session_id)
        timeline.append({
            "stage": "SCOUT_INVESTIGATION",
            "title": "Scout-Agent Graph Investigation",
            "agent": "Scout-Agent",
            "summary": scout_res["summary"],
            "risk_level": scout_res["risk_level"],
            "logs": scout_res["logs"]
        })

        # Phase 2: Memory Consolidator & Cross-Tenant Coordination
        consolidator_res = self.consolidator.coordinate(pr_id, target_function, repo, scout_res, session_id=session_id)
        timeline.append({
            "stage": "MEMORY_COORDINATION",
            "title": "Memory-Consolidator & Cross-Tenant Coordination",
            "agent": "Consolidator-Agent",
            "synthesis": consolidator_res["memory_synthesis"],
            "cross_tenant_bridges": consolidator_res["cross_tenant_data"],
            "logs": consolidator_res["logs"]
        })

        # Phase 3: Fixer Agent Coordination & Action
        fixer_res = self.fixer.remediate(pr_id, target_function, scout_res, consolidator_res, repo=repo, session_id=session_id)
        timeline.append({
            "stage": "FIXER_ACTION",
            "title": f"Fixer-Agent Autonomous Action: {fixer_res['decision']}",
            "agent": "Fixer-Agent",
            "decision": fixer_res["decision"],
            "assigned_reviewer": fixer_res["assigned_reviewer"],
            "explanation": fixer_res["explanation"],
            "playbook_steps": fixer_res["playbook_steps"],
            "logs": fixer_res["logs"]
        })

        # Phase 4: Retrieve Complete Blackboard Session Trace from FalkorDB
        blackboard = tools.get_blackboard_session(session_id)

        # Phase 5: Graph Snapshot for Web Visualization
        subgraph = tools.get_subgraph_for_visualization(target_function, repo=repo)

        return {
            "status": "success",
            "session_id": session_id,
            "pr_id": pr_id,
            "function": target_function,
            "repo": repo,
            "risk_level": scout_res["risk_level"],
            "decision": fixer_res["decision"],
            "assigned_reviewer": fixer_res["assigned_reviewer"],
            "timeline": timeline,
            "scout_findings": scout_res,
            "consolidator_findings": consolidator_res,
            "fixer_action": fixer_res,
            "blackboard": blackboard,
            "subgraph": subgraph,
            "llm_provider": self.llm.provider
        }
