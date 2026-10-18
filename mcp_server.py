"""NexusGuard FastMCP Server.
Exposes autonomous graph-backed engineering governance tools over Model Context Protocol (MCP).

Run standalone (stdio transport):
    python mcp_server.py
"""
import sys

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        from fastmcp import FastMCP
    except ImportError:
        FastMCP = None

try:
    import tools
except ImportError:
    try:
        from files import tools
    except ImportError:
        from mcp_server import tools

if FastMCP is None:
    raise ImportError(
        "Neither 'mcp' nor 'fastmcp' is installed in the current Python environment.\n"
        "Please run: pip install mcp (or pip install fastmcp)"
    )

mcp = FastMCP("nexusguard-provenance")


@mcp.tool()
def assess_blast_radius(function: str, max_hops: int = 5) -> dict:
    """Evaluate blast radius: what breaks if this function changes or is deleted?
    Returns upstream callers, downstream callees, impacted teams, protecting decisions,
    and associated Jira tickets.
    """
    return tools.assess_blast_radius(function, max_hops)


@mcp.tool()
def find_true_expert(function: str, limit: int = 5) -> dict:
    """Identify true graph-verified domain experts (commits, reviews, Slack mentions, recency decay)
    and compare against the official org-chart team owner.
    """
    return tools.find_true_expert(function, limit)


@mcp.tool()
def get_decision_chain(function: str) -> dict:
    """Retrieve decision provenance: why does this code exist?
    Traces decisions, executive Slack promises, and Jira tickets.
    """
    return tools.get_decision_chain(function)


@mcp.tool()
def get_memory_context(function: str, repo: str = "acme_checkout") -> dict:
    """Retrieve multi-tier agent memory for this function from a specific tenant repo:
    1. Episodic: past outages, financial losses, and regressions.
    2. Procedural: safe migration playbooks and sequential checklists.
    3. Semantic: official runbooks and documentation.
    """
    return tools.get_memory_context(function, repo=repo)


@mcp.tool()
def write_risk_finding(pr_id: str, function: str, risk_level: str, summary: str) -> dict:
    """Scout-Agent writes its risk assessment finding directly into the graph.
    Shared across agents so Fixer-Agent can act on it.
    """
    return tools.write_risk_finding(pr_id, function, risk_level, summary)


@mcp.tool()
def block_or_approve_pr(pr_id: str, function: str, decision: str, reviewer_name: str = "", risk_level: str = "HIGH") -> dict:
    """Fixer-Agent autonomous governance action:
    Sets PR status (BLOCKED / APPROVED), flags documentation as is_stale, and auto-assigns
    the true graph-verified domain expert.
    """
    return tools.block_or_approve_pr(pr_id, function, decision, reviewer_name, risk_level)


@mcp.tool()
def record_blackboard_token(session_id: str, from_agent: str, to_agent: str, phase: str, message: str, payload: dict = None) -> dict:
    """Track 02: Writes an active coordination token and working-memory payload to the FalkorDB Blackboard graph."""
    return tools.record_blackboard_token(session_id, from_agent, to_agent, phase, message, payload)


@mcp.tool()
def get_blackboard_session(session_id: str) -> dict:
    """Track 02: Retrieves all working-memory tokens and agent handoffs for an active session from FalkorDB."""
    return tools.get_blackboard_session(session_id)


@mcp.tool()
def query_cross_tenant_memory(function: str, primary_tenant: str) -> dict:
    """Track 02: Evaluates cross-tenant dependencies across isolated repository memory graphs."""
    return tools.query_cross_tenant_memory(function, primary_tenant)


@mcp.tool()
def consolidate_new_learning(repo: str, function: str, incident_id: str, summary: str, loss_usd: int, playbook_title: str, playbook_steps: list[str]) -> dict:
    """Track 02: Dynamically learns and consolidates a new incident and procedural playbook into FalkorDB memory."""
    return tools.consolidate_new_learning(repo, function, incident_id, summary, loss_usd, playbook_title, playbook_steps)


if __name__ == "__main__":
    mcp.run()

