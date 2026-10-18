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
    repo: str = Field(default="acme_checkout", description="Tenant repository (e.g. acme_checkout, acme_auth)")


class ResetResponse(BaseModel):
    status: str
    message: str


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
    return {
        "tenants": [
            {
                "id": "acme_checkout",
                "name": "Acme Checkout & Billing (Primary Demo)",
                "functions": ["applyDiscount", "calculateTotal", "checkout", "refundOrder"]
            },
            {
                "id": "acme_auth",
                "name": "Acme Auth & Identity (Multi-Tenant Isolation)",
                "functions": ["verifyJwtToken", "rotateSigningKey", "invalidateSessions", "enforceMfaPolicy"]
            },
            {
                "id": "acme_data",
                "name": "Acme Data Governance & Compliance (GDPR & Cryptography)",
                "functions": ["hardDeleteAccount", "encryptPiiField", "exportUserData", "auditLogEvent"]
            }
        ]
    }


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
def get_graph(function: str = Query(default="applyDiscount"), repo: str = Query(default="acme_checkout")):
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
def tool_memories(function: str = Query(default="applyDiscount"), repo: str = Query(default="acme_checkout")):
    return tools.get_memory_context(function, repo=repo)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
