"""FastAPI Backend Server for NexusGuard Autonomous Governance.

Exposes REST endpoints for the Web Dashboard:
- /api/simulate: Triggers Scout-Agent and Fixer-Agent workflow
- /api/graph: Returns PyVis/NetworkX graph nodes and edges
- /api/reset: Deterministically reseeds the FalkorDB graphs
- /api/tenants: Lists available repositories
- /api/tools/*: Direct FastMCP tool execution
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import os
from pathlib import Path

import tools
import seed
from agents import GovernanceOrchestrator

app = FastAPI(
    title="NexusGuard API",
    description="Autonomous Graph-Backed Engineering Governance Engine powered by FalkorDB",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = GovernanceOrchestrator()


class SimulatePRRequest(BaseModel):
    pr_id: str = Field(default="PR-904", description="Pull Request ID")
    function: str = Field(default="applyDiscount", description="Target function modified by the PR")
    repo: Optional[str] = Field(default=None, description="Tenant repository (defaults to the deployment's REPO_NAME)")


class ResetResponse(BaseModel):
    status: str
    message: str


def _humanize(tenant_id: str) -> str:
    return tenant_id.replace("_", " ").replace("-", " ").title()


def _tenant_names_from_input() -> dict:
    """Optional cosmetic display names declared in the company input file."""
    try:
        data = json.loads(Path(seed.resolve_input_path()).read_text(encoding="utf-8"))
        return data.get("tenant_names") or {}
    except Exception:
        return {}


def _fallback_tenants() -> list[dict]:
    """company.json / env fallback when the live graph has no tenants yet."""
    names = _tenant_names_from_input()
    try:
        data = json.loads(Path(seed.resolve_input_path()).read_text(encoding="utf-8"))
        functions_by_repo: dict[str, list[str]] = {}
        for fn in data.get("functions", []):
            functions_by_repo.setdefault(fn.get("repo"), []).append(fn.get("name"))
        tenants = data.get("tenants") or []
        if tenants:
            return [{
                "id": tenant,
                "name": names.get(tenant, _humanize(tenant)),
                "functions": sorted(n for n in functions_by_repo.get(tenant, []) if n),
            } for tenant in tenants]
    except Exception:
        pass
    repo = os.getenv("REPO_NAME", "acme_checkout")
    return [{"id": repo, "name": _humanize(repo), "functions": []}]


@app.get("/")
def root():
    return {
        "system": "NexusGuard",
        "description": "FalkorDB Autonomous Engineering Governance Engine",
        "endpoints": [
            "/api/simulate",
            "/api/graph",
            "/api/tenants",
            "/api/reset",
            "/api/tools/blast-radius",
            "/api/tools/expert",
            "/api/tools/decision-chain",
            "/api/tools/memories",
            "/api/tools/blackboard",
            "/api/tools/cross-tenant",
            "/api/tools/consolidate",
            "/docs"
        ]
    }


@app.get("/health")
def health():
    try:
        from db import client
        conn = client().select_graph("dev_knowledge")
        test = conn.query("RETURN 1 AS ok")
        return {"status": "healthy", "falkordb": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/api/tenants")
def get_tenants():
    """Tenant discovery (rev1 backend-generalization): derived from the live knowledge
    graph (distinct Function.repo), falling back to the company input file / env when
    the graph is empty. Works for any ingested company with no code edits."""
    tenants: list[dict] = []
    try:
        from db import knowledge
        from db import rows as db_rows

        g = knowledge()
        repos = db_rows(g.ro_query(
            "MATCH (f:Function) WHERE f.repo IS NOT NULL "
            "RETURN DISTINCT f.repo AS repo ORDER BY repo"))
        names = _tenant_names_from_input()
        for record in repos:
            repo = record["repo"]
            fns = db_rows(g.ro_query(
                "MATCH (f:Function {repo:$repo}) RETURN f.name AS name ORDER BY f.name",
                {"repo": repo}))
            tenants.append({
                "id": repo,
                "name": names.get(repo, _humanize(repo)),
                "functions": [f["name"] for f in fns],
            })
    except Exception:
        tenants = []

    if not tenants:
        tenants = _fallback_tenants()
    return {"tenants": tenants}


@app.post("/api/simulate")
def simulate_pr(req: SimulatePRRequest):
    """Triggers the full two-agent governance workflow:
    1. Scout-Agent computes blast radius, provenance, and episodic memory.
    2. Fixer-Agent checks centrality, procedural playbooks, and executes governance action.
    """
    try:
        result = orchestrator.simulate_pr(
            pr_id=req.pr_id,
            target_function=req.function,
            repo=req.repo
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph")
def get_graph(function: str = Query(default="applyDiscount"), repo: Optional[str] = Query(default=None)):
    """Returns nodes and edges formatted for PyVis / NetworkX / interactive graph canvas."""
    try:
        return tools.get_subgraph_for_visualization(function=function, repo=repo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
def reset_database():
    """Resets and re-seeds all FalkorDB graphs deterministically in < 1 second."""
    try:
        seed.seed_all()
        return {"status": "success", "message": "All graphs successfully re-seeded from company.json"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Tool Inspection Endpoints (Mapping FastMCP tools directly to REST)
@app.get("/api/tools/blast-radius")
def tool_blast_radius(function: str = Query(default="applyDiscount"), max_hops: int = Query(default=5)):
    return tools.assess_blast_radius(function, max_hops=max_hops)


@app.get("/api/tools/expert")
def tool_find_expert(function: str = Query(default="applyDiscount"), limit: int = Query(default=5)):
    return tools.find_true_expert(function, limit=limit)


@app.get("/api/tools/decision-chain")
def tool_decision_chain(function: str = Query(default="applyDiscount")):
    return tools.get_decision_chain(function)


@app.get("/api/tools/memories")
def tool_memories(function: str = Query(default="applyDiscount"), repo: Optional[str] = Query(default=None)):
    return tools.get_memory_context(function, repo=repo)


@app.get("/api/tools/blackboard")
def tool_blackboard(session_id: str = Query(..., description="Blackboard session ID to retrieve")):
    """Track 02: Retrieves all coordination tokens for an active Blackboard session."""
    return tools.get_blackboard_session(session_id)


@app.get("/api/tools/cross-tenant")
def tool_cross_tenant(
    function: str = Query(default="verifyJwtToken", description="Function changing in the primary tenant"),
    primary_tenant: Optional[str] = Query(default=None, description="Primary tenant repository (defaults to the deployment's REPO_NAME)"),
):
    """Track 02: Evaluates cross-tenant dependencies across isolated memory graphs."""
    primary_tenant = primary_tenant or os.getenv("REPO_NAME", "acme_checkout")
    return tools.query_cross_tenant_memory(function, primary_tenant)


class ConsolidateRequest(BaseModel):
    repo: Optional[str] = Field(default=None, description="Tenant repository memory graph (defaults to the deployment's REPO_NAME)")
    function: str = Field(..., description="Target function the new learning applies to")
    incident_id: str = Field(..., description="New incident ID to consolidate")
    summary: str = Field(..., description="Incident summary")
    loss_usd: int = Field(default=0, description="Financial loss in USD")
    playbook_title: str = Field(default="Auto-learned playbook", description="Procedure title")
    playbook_steps: List[str] = Field(default_factory=list, description="Ordered procedure steps")


@app.post("/api/tools/consolidate")
def tool_consolidate(req: ConsolidateRequest):
    """Track 02: Dynamically learns a new incident + playbook into the tenant memory graph."""
    return tools.consolidate_new_learning(
        repo=req.repo or os.getenv("REPO_NAME", "acme_checkout"),
        function=req.function,
        incident_id=req.incident_id,
        summary=req.summary,
        loss_usd=req.loss_usd,
        playbook_title=req.playbook_title,
        playbook_steps=req.playbook_steps,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
