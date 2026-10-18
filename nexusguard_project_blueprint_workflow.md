# NexusGuard: Autonomous Graph-Backed Engineering Governance
**FalkorDB Hackathon Blueprint & Remote Execution Guide**

---

## 1. Executive Summary & Viability Assessment

**Is this buildable by Sunday?**
**Yes—100%.** The secret to winning with this scope in a weekend is **ruthlessly faking the external webhook plumbing** (do not waste time setting up live GitHub, Slack, or Jira OAuth apps) and **investing 100% of your engineering effort into the FalkorDB graph mechanics, MCP tool execution, and visual explainability.**

By using a deterministic graph seeding script (`seed.py`) alongside a "Simulate Commit / PR" button in your dashboard, a single unified application satisfies **all three hackathon tracks simultaneously**:
* **Track 01 (Agents That Act on Connected Data):** Uses FastMCP tools to run `shortestPath` and centrality algorithms, blocking dangerous PRs, flagging stale documentation, and auto-tagging true domain experts directly in the graph.
* **Track 02 (Agent Memory & Coordination):** Implements explicit **Episodic** (past incidents), **Semantic** (runbooks), and **Procedural** (migration steps) memory in FalkorDB, coordinated via a shared graph Blackboard (`dev_agent_state`) across three specialized agents (`Scout-Agent`, `Consolidator-Agent`, and `Fixer-Agent`) with multi-tenant isolation (`acme_checkout`, `acme_auth`, `acme_data`).
* **Track 03 (Company Brain):** Connects code, Jira tickets, and Slack messages in one graph, contrasts the formal org chart against true graph-calculated expertise, traces code decisions back to executive Slack promises, and renders everything in a CRYO-PULSE Cyber-Emerald theme with ambient floating nodes.

---

## 2. Refined Problem Statement (For README & Pitch)

### The Problem: Context-Blind Code Reviews & Institutional Amnesia
Modern software teams ship faster than ever, but their AI code review tools only inspect Pull Request diffs in isolation. Standard LLM bots suffer from three fatal blind spots:
1. **Unseen Blast Radius:** A bot cannot see that modifying a seemingly simple function like `applyDiscount()` impacts a 4-hop downstream billing pipeline tied to critical enterprise tickets.
2. **Org Chart Illusion vs. Tribal Reality:** When a high-risk PR is opened, static rules request reviews from "Team-A" based on the company org chart. In reality, graph interaction history proves that **Bob** (who left the company last month) wrote the module, and **Priya** (who hot-fixed it twice during outages) is the only active engineer who truly understands it.
3. **Episodic & Decision Amnesia:** Generic bots do not remember that deleting a weird legacy `if-statement` in `applyDiscount()` caused a **$12,000 refund outage** six months ago. Nor can they trace that the `if-statement` only exists because the CEO promised "Client X" a custom pricing override in `#sales` on Slack on March 12 (which spawned Ticket #418).

### The Solution: NexusGuard
**NexusGuard** is an active, multi-tenant engineering governance engine powered by **FalkorDB** and **Model Context Protocol (MCP)**. Instead of offering vague "trust me bro" LLM summaries, NexusGuard treats the entire engineering organization—code call graphs, PR history, Slack threads, Jira tickets, runbooks, and incident post-mortems—as a living, interconnected knowledge graph.

When a developer pushes a commit or opens a PR:
1. **Scout-Agent** queries FalkorDB via MCP to compute the multi-hop blast radius, retrieves the historical decision chain (`Function -> Ticket -> SlackMessage`), and checks **Episodic Memory** for past financial or operational incidents linked to the modified code.
2. **Fixer-Agent** concurrently reads **Semantic Memory** (architecture runbooks) and **Procedural Memory** (step-by-step safe migration playbooks) from the same tenant graph.
3. **Autonomous Action & Explainability:** Rather than just answering questions, NexusGuard **acts**. It blocks high-risk merges, auto-assigns the true graph-verified expert (`Priya`), flags connected documentation as `STALE`, and renders the exact FalkorDB subgraph path in the UI to prove *why* the decision was made.

---

## 3. System Architecture & End-to-End Workflow

### End-to-End Execution Flow
```
[Developer / Demo Trigger: "Simulate PR #904 touching applyDiscount()"]
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │   FastAPI / Orchestrator  │
                     │ (Selects Tenant Graph:    │
                     │  acme_checkout/acme_auth) │
                     └─────────────┬─────────────┘
                                   │
            ┌──────────────────────┴──────────────────────┐
            ▼                                             ▼
┌───────────────────────┐                     ┌───────────────────────┐
│      SCOUT-AGENT      │                     │      FIXER-AGENT      │
│  (Risk & Discovery)   │                     │ (Remediation & Action)│
└───────────┬───────────┘                     └───────────┬───────────┘
            │ Calls via FastMCP                           │ Calls via FastMCP
            ▼                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastMCP Tool Server (Python)                    │
│  • assess_blast_radius()        • get_memory_context()              │
│  • find_true_expert()           • write_risk_finding()              │
│  • get_decision_chain()         • block_or_approve_pr()             │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ OpenCypher Queries
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FalkorDB (Multi-Tenant Instance)                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Graph 1: acme_checkout          Graph 2: acme_auth            │  │
│  │  • Company Brain Nodes           • Isolated Repo Context      │  │
│  │  • Episodic / Semantic / Procedural Memory Nodes              │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Runtime Workflow
1. **Event Ingestion (Keeping Knowledge Current):**
   A new PR (`PR #904`) modifies `applyDiscount()`. The ingestion hook creates `(:PR {id: 904})-[:MODIFIES]->(:Function {name: 'applyDiscount'})` in the `acme_checkout` graph and immediately marks any attached `(:Doc)` node as `stale = true`.
2. **Scout-Agent Investigation (Read + Write to Graph):**
   * Calls `assess_blast_radius('applyDiscount')`: Runs `shortestPath` up to 5 hops to find downstream impacted functions and active customer tickets.
   * Queries **Episodic Memory**: Discovers `(:Incident {loss: "$12k refund"})-[:CAUSED_BY]->(:Refactor {deleted: "applyDiscount"})`.
   * Calls `get_decision_chain('applyDiscount')`: Traverses `(:Function)-[:IMPLEMENTED_FOR]->(:Ticket {id: '#418'})-[:ORIGINATED_FROM]->(:SlackMsg {channel: '#sales', author: 'CEO'})`.
   * Writes a `(:RiskFinding {level: 'HIGH'})` node directly into the graph for the Fixer-Agent to pick up.
3. **Fixer-Agent Coordination & Governance Action (Read + Mutate Graph):**
   * Reads the `(:RiskFinding)` node written by Scout-Agent.
   * Queries **Semantic Memory** (Discount Logic Runbook) and **Procedural Memory** ("Safe Discount Migration Playbook" steps 1–4).
   * Calls `find_true_expert('applyDiscount')`: Computes developer centrality across commits, reviews, and hotfixes. Identifies that `Bob` (`status: 'departed'`) has the highest historical score, so it selects the highest active expert, `Priya` (`centrality_score: 14`), over generic `Team-A`.
   * Calls `block_or_approve_pr()`: Sets `PR.status = 'BLOCKED'`, links `(:PR)-[:ASSIGNED_REVIEWER]->(:Developer {name: 'Priya'})`, and outputs the exact Cypher path and safe migration checklist to the UI.

---

## 4. Unified FalkorDB Schema & Core Cypher Queries

### Graph Schema Design
* **Code & Repo Entities:**
  * `(:Function {name, file, repo})`
  * `(:PR {id, title, author, status, risk_level})`
  * `(:Doc {id, title, url, is_stale})`
* **Company Brain Entities (Track 03):**
  * `(:Developer {name, team, status, role})` — `status` is `'active'` or `'departed'`
  * `(:Ticket {id, title, priority})`
  * `(:SlackMsg {id, channel, author, text, timestamp, url})`
* **Agent Memory Entities (Track 02):**
  * **Episodic:** `(:Incident {id, date, loss, summary})-[:CAUSED_BY]->(:Refactor {id, deleted})-[:TARGETED]->(:Function)`
  * **Semantic:** `(:Runbook {id, title, rule_summary})-[:GOVERNS]->(:Function)`
  * **Procedural:** `(:Playbook {name})-[:HAS_STEP]->(:Step {order, instruction})`
  * **Coordination:** `(:AgentFinding {agent, risk_score, summary, timestamp})-[:ABOUT]->(:PR)`

### The 5 Essential Cypher Queries (Exposed via FastMCP)

#### 1. Blast Radius & Episodic Incident Check (`assess_blast_radius`)
```cypher
MATCH p = shortestPath((f:Function {name: $fn_name})-[*1..5]-(t:Ticket))
OPTIONAL MATCH (f)<-[:TARGETED]-(r:Refactor)<-[:CAUSED_BY]-(inc:Incident)
RETURN [n IN nodes(p) | coalesce(n.name, n.id, n.title)] AS dependency_path,
       t.id AS impacted_ticket,
       inc.id AS past_incident_id,
       inc.loss AS past_incident_loss,
       inc.date AS past_incident_date
```

#### 2. True Expert Discovery via Graph Degree Centrality (`find_true_expert`)
```cypher
MATCH (d:Developer)-[rel:AUTHORED|REVIEWED|FIXED]->(item)-[*0..2]->(f:Function {name: $fn_name})
WITH d, count(rel) AS score, collect( DISTINCT type(rel)) AS actions
RETURN d.name AS developer,
       d.team AS org_chart_team,
       d.status AS employment_status,
       score AS centrality_score,
       actions
ORDER BY score DESC
```

#### 3. Source Decision Provenance (`get_decision_chain`)
```cypher
MATCH path = (f:Function {name: $fn_name})-[:IMPLEMENTED_FOR]->(t:Ticket)-[:ORIGINATED_FROM]->(s:SlackMsg)
RETURN f.name AS function_name,
       t.id AS jira_ticket,
       t.title AS ticket_summary,
       s.author AS slack_author,
       s.channel AS slack_channel,
       s.date AS slack_date,
       s.text AS exact_quote,
       s.url AS source_link
```

#### 4. Semantic & Procedural Memory Retrieval (`get_agent_memories`)
```cypher
MATCH (f:Function {name: $fn_name})
OPTIONAL MATCH (rb:Runbook)-[:GOVERNS]->(f)
OPTIONAL MATCH (pb:Playbook {domain: 'discount_migration'})-[:HAS_STEP]->(st:Step)
WITH rb, st ORDER BY st.order ASC
RETURN rb.title AS semantic_runbook,
       rb.rule_summary AS semantic_rule,
       collect(st.order + '. ' + st.instruction) AS procedural_steps
```

#### 5. Autonomous Governance Action & Stale Doc Flagging (`block_or_approve_pr`)
```cypher
MATCH (pr:PR {id: $pr_id})-[:MODIFIES]->(f:Function {name: $fn_name})
OPTIONAL MATCH (doc:Doc)-[:DOCUMENTS]->(f)
MATCH (dev:Developer {name: $reviewer_name})
SET pr.status = $decision,
    pr.risk_level = $risk_level,
    doc.is_stale = true,
    doc.flagged_reason = 'Modified by ' + $pr_id
MERGE (pr)-[:ASSIGNED_REVIEWER]->(dev)
RETURN pr.id AS pr_id, pr.status AS new_status, dev.name AS assigned_to, doc.title AS stale_doc
```

---

## 5. Weekend Team Split & Hour-by-Hour Execution Plan

Divide responsibilities cleanly along the **FastMCP / API contract** so both teammates can build in parallel without merge conflicts.

* **Teammate A (Graph Architect & MCP Backend):** Owns FalkorDB setup, synthetic data seeding (`seed_graph.py`), OpenCypher queries, and the FastMCP server (`mcp_server.py`).
* **Teammate B (Agent Orchestrator & UI Frontend):** Owns the `Scout-Agent` + `Fixer-Agent` coordination loop, FastAPI endpoints, and the interactive dashboard (Subgraph visualizer + PR governance view).

### Phase 1: Foundation & Seeding (Saturday Morning – 4 Hours)
* **Together (30 mins):** Lock down the JSON response shapes for the 5 MCP tools above.
* **Teammate A:**
  * Provision the shared FalkorDB instance (FalkorDB Cloud or Docker + Tailscale).
  * Write `seed_graph.py` to populate two distinct tenant graphs: `acme_checkout` (contains the `applyDiscount`, `Bob`, `Priya`, `#sales` CEO Slack message, `$12k refund` incident, and runbooks) and `acme_auth` (contains a secondary auth flow to prove multi-tenant isolation).
* **Teammate B:**
  * Scaffold the web UI with a **Tenant Selector dropdown** (`acme_checkout` | `acme_auth`) and a **"Simulate Incoming PR #904"** trigger button.
  * Build the two-agent LangGraph / Python orchestration workflow using mock JSON data first.

### Phase 2: MCP Server & Multi-Agent Wiring (Saturday Afternoon – 5 Hours)
* **Teammate A:**
  * Build `mcp_server.py` using `fastmcp` wrapping the 5 parameterized Cypher queries.
  * Add a helper tool `record_scout_finding()` so `Scout-Agent` writes its risk assessment directly into FalkorDB and `Fixer-Agent` reads it back from FalkorDB (proving concurrent shared graph memory for Track 02).
* **Teammate B:**
  * Connect `Scout-Agent` and `Fixer-Agent` to the live FastMCP server.
  * Build the UI panel that shows live agent reasoning steps alongside the exact Cypher query executed at each step.

### Phase 3: Visual Explainability & "Company Brain" Features (Saturday Night – 4 Hours)
* **Teammate A:**
  * Create a `/graph-snapshot` endpoint that returns nodes and edges formatted for force-directed graph rendering, highlighting the `shortestPath` nodes in crimson red.
  * Test edge cases and ensure re-seeding takes `< 1 second` for clean demo resets.
* **Teammate B:**
  * Integrate an interactive graph canvas (`react-force-graph-2d` or `streamlit-agraph`).
  * Build the **"Org Chart vs. True Knowledge"** comparison card (showing `Team-A [Assigned]` vs `Bob [Departed - Score 19]` & `Priya [Active Expert - Score 14]`).
  * Add the clickable **"Decision Provenance"** badge (`Slack #sales (Mar 12) -> Ticket #418 -> applyDiscount()`) and the **"Stale Documentation Alert"** banner.

### Phase 4: Polish, Pitch & Submission (Sunday Morning to Afternoon)
* **Together:**
  * Run through the 3-minute demo script 3 times. Ensure the "Reset Demo Graph" button cleanly restores the initial state in one click.
  * Write the GitHub `README.md` clearly mapping your features to **Track 01**, **Track 02**, and **Track 03** so judges can grade every requirement effortlessly.
  * Record the demo video showing live graph mutations in FalkorDB and submit ahead of the deadline.

---

## 6. Remote Collaboration & Tooling Setup

### 1. Shared FalkorDB Setup (Choose One)
* **Option A: FalkorDB Cloud (Zero-Config Remote Access)**
  Sign up for a free cluster at [cloud.falkordb.com](https://cloud.falkordb.com) and share the credentials in a shared `.env` file.
* **Option B: Self-Hosted Docker + Tailscale (Unlimited Local Speed + Built-in UI)**
  Teammate A runs the official FalkorDB image (which bundles both the database on port `6379` and the FalkorDB Browser UI on port `3000`):
  ```bash
  docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
  ```
  Install [Tailscale](https://tailscale.com/) on both machines (`tailscale up`). Teammate B can now connect their Python code directly to Teammate A's Tailscale IP (`100.x.y.z:6379`) and open `http://100.x.y.z:3000` in their browser to visually inspect the live graph.

### 2. Standardized Repository Structure
```text
nexusguard/
├── .env.example          # FALKORDB_HOST, FALKORDB_PORT, LLM_API_KEY
├── pyproject.toml        # Managed via uv for instant reproducible installs
├── db.py                 # Multi-tenant FalkorDB connection manager
├── seed_graph.py         # Deterministic data generator for acme_checkout & acme_auth
├── mcp_server.py         # FastMCP server exposing the 5 graph tools
├── agents.py             # Scout-Agent & Fixer-Agent orchestration
├── api.py                # FastAPI server for UI triggers & graph snapshots
└── frontend/             # Next.js or Streamlit interactive dashboard
```

### 3. Fast Environment Bootstrap Commands
Run these commands to initialize your shared repo:
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize project and install all required dependencies
uv init nexusguard && cd nexusguard
uv add falkordb fastmcp langgraph langchain-openai fastapi uvicorn pydantic python-dotenv
```

### 4. Ready-to-Use `seed_graph.py` Starter Script
Drop this script into your repo so you and your teammate can immediately populate the exact hackathon scenario into FalkorDB:

```python
import os
from falkordb import FalkorDB
from dotenv import load_dotenv

load_dotenv()

def seed_all():
    db = FalkorDB(
        host=os.getenv("FALKORDB_HOST", "localhost"),
        port=int(os.getenv("FALKORDB_PORT", 6379)),
        password=os.getenv("FALKORDB_PASSWORD", None)
    )

    # 1. Seed Primary Tenant: acme_checkout
    g = db.select_graph("acme_checkout")
    g.query("MATCH (n) DETACH DELETE n")  # Clean slate

    seed_cypher = """
    // Code & Dependencies
    CREATE (fn1:Function {name: 'applyDiscount', file: 'pricing/discounts.py', repo: 'acme_checkout'})
    CREATE (fn2:Function {name: 'calculateCartTotal', file: 'checkout/cart.py', repo: 'acme_checkout'})
    CREATE (fn3:Function {name: 'chargeStripeInvoice', file: 'billing/stripe.py', repo: 'acme_checkout'})
    CREATE (fn1)-[:CALLS]->(fn2)-[:CALLS]->(fn3)

    // Documentation (To demonstrate Stale Doc flagging)
    CREATE (doc:Doc {id: 'DOC-102', title: 'Checkout Discount Logic & VIP Overrides', is_stale: false})
    CREATE (doc)-[:DOCUMENTS]->(fn1)

    // Decision Chain: Function -> Ticket -> Slack Message
    CREATE (t418:Ticket {id: 'TICKET-418', title: 'Custom 15% grace threshold for Client X', priority: 'CRITICAL'})
    CREATE (fn3)-[:IMPACTS]->(t418)
    CREATE (fn1)-[:IMPLEMENTED_FOR]->(t418)
    CREATE (slack:SlackMsg {
        id: 'MSG-991',
        channel: '#sales',
        author: 'CEO (Sarah)',
        date: 'Mar 12',
        text: 'Promised Client X we will keep the custom if-statement grace override in applyDiscount for Q2 renewal.',
        url: 'https://acme.slack.com/archives/C01SALES/p17102400'
    })
    CREATE (t418)-[:ORIGINATED_FROM]->(slack)

    // Developers: Org Chart vs True Graph Centrality
    CREATE (bob:Developer {name: 'Bob', team: 'Team-A (Checkout)', status: 'departed', role: 'Staff Eng'})
    CREATE (priya:Developer {name: 'Priya', team: 'Platform-SRE', status: 'active', role: 'Senior SRE'})
    CREATE (dave:Developer {name: 'Dave', team: 'Team-A (Checkout)', status: 'active', role: 'Junior Eng'})

    // Historical interactions proving Bob (left) and Priya (active) actually know applyDiscount
    CREATE (bob)-[:AUTHORED {commits: 18}]->(fn1)
    CREATE (priya)-[:FIXED {hotfixes: 2}]->(fn1)
    CREATE (priya)-[:REVIEWED]->(fn2)
    CREATE (dave)-[:AUTHORED {commits: 1}]->(fn3)

    // Track 02: Episodic Memory (Past Incident)
    CREATE (inc:Incident {id: 'INC-77', date: '2025-11-04', loss: '$12k refund', summary: 'Removed VIP discount guard clause'})
    CREATE (ref:Refactor {id: 'REF-19', deleted: 'applyDiscount'})
    CREATE (inc)-[:CAUSED_BY]->(ref)-[:TARGETED]->(fn1)

    // Track 02: Semantic Memory (Runbook)
    CREATE (rb:Runbook {
        id: 'RB-04',
        title: 'Pricing & Discount Governance Runbook',
        rule_summary: 'Any modification to applyDiscount requires shadow billing replay and SRE sign-off.'
    })
    CREATE (rb)-[:GOVERNS]->(fn1)

    // Track 02: Procedural Memory (Safe Migration Steps)
    CREATE (pb:Playbook {name: 'Safe Discount Migration Playbook', domain: 'discount_migration'})
    CREATE (s1:Step {order: 1, instruction: 'Verify Client X contract flag in feature store before altering branch.'})
    CREATE (s2:Step {order: 2, instruction: 'Run shadow invoice replay against last 1,000 checkout events.'})
    CREATE (s3:Step {order: 3, instruction: 'Require explicit approval from Priya (SRE) due to INC-77 history.'})
    CREATE (pb)-[:HAS_STEP]->(s1)
    CREATE (pb)-[:HAS_STEP]->(s2)
    CREATE (pb)-[:HAS_STEP]->(s3)

    // Active Incoming PR for Demo Trigger
    CREATE (pr:PR {id: 'PR-904', title: 'Refactor: Clean up legacy if-statement in applyDiscount', status: 'OPEN', risk_level: 'UNASSESSED'})
    CREATE (pr)-[:MODIFIES]->(fn1)
    """
    g.query(seed_cypher)

    # 2. Seed Secondary Tenant: acme_auth (Proves Multi-Tenant Isolation)
    g_auth = db.select_graph("acme_auth")
    g_auth.query("MATCH (n) DETACH DELETE n")
    g_auth.query("""
    CREATE (f:Function {name: 'verifyJwtToken', file: 'auth/jwt.py', repo: 'acme_auth'})
    CREATE (d:Developer {name: 'Alice', team: 'Security', status: 'active'})
    CREATE (d)-[:AUTHORED]->(f)
    """)

    print("Successfully seeded 'acme_checkout' and 'acme_auth' graphs in FalkorDB!")

if __name__ == "__main__":
    seed_all()
```