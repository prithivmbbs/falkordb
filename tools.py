"""Tool logic for NexusGuard autonomous governance.
Provides fixed, parameterized, safe Cypher queries covering:
1. Blast radius calculation (Track 01)
2. True expert discovery & centrality (Track 03)
3. Decision provenance chain (Track 03)
4. Multi-tiered Agent Memory: Episodic, Semantic, Procedural (Track 02)
5. Scout-Agent risk finding logging (Track 02)
6. Autonomous PR governance action & doc staleness tagging (Track 01 & 02)
"""
try:
    from db import knowledge, memory, agent_state, rows
except ImportError:
    try:
        from files.db import knowledge, memory, agent_state, rows
    except ImportError:
        from graph.db import knowledge, memory, agent_state, rows

MAX_HOPS = 5


def _shortest_per_endpoint(paths: list[dict], end: int) -> list[dict]:
    """Keep the shortest path for each distinct caller/callee (index 0 or -1)."""
    best: dict[str, dict] = {}
    for r in paths:
        key = r["path"][end]
        if key not in best or r["hops"] < best[key]["hops"]:
            best[key] = r
    return sorted(best.values(), key=lambda r: r["hops"])


def assess_blast_radius(function: str, max_hops: int = MAX_HOPS) -> dict:
    """Evaluate blast radius: what breaks if this function changes or is deleted?
    Returns upstream callers, downstream callees, impacted teams, protecting decisions,
    associated Jira tickets, and data-driven compliance criticality.
    """
    hops = max(1, min(int(max_hops), MAX_HOPS))
    g = knowledge()
    p = {"n": function}

    found = rows(g.ro_query("MATCH (f:Function {name:$n}) RETURN f.name AS name, f.file AS file", p))
    if not found:
        known = rows(g.ro_query("MATCH (f:Function) RETURN f.name AS name ORDER BY name"))
        return {"error": f"Unknown function '{function}'", "known_functions": [k["name"] for k in known]}

    callers = rows(g.ro_query(
        f"MATCH q=(c:Function)-[:CALLS*1..{hops}]->(:Function {{name:$n}}) "
        "RETURN [x IN nodes(q) | x.name] AS path, length(q) AS hops LIMIT 200", p))
    callees = rows(g.ro_query(
        f"MATCH q=(:Function {{name:$n}})-[:CALLS*1..{hops}]->(c:Function) "
        "RETURN [x IN nodes(q) | x.name] AS path, length(q) AS hops LIMIT 200", p))
    callers = _shortest_per_endpoint(callers, 0)
    callees = _shortest_per_endpoint(callees, -1)

    affected = [c["path"][0] for c in callers]
    teams = rows(g.ro_query(
        "MATCH (t:Team)-[:OFFICIALLY_OWNS]->(f:Function) WHERE f.name IN $names "
        "RETURN t.name AS team, f.name AS function", {"names": affected + [function]}))
    decisions = rows(g.ro_query(
        "MATCH (d:Decision)-[:JUSTIFIES]->(:Function {name:$n}) "
        "RETURN d.id AS id, d.summary AS summary", p))
    tickets = rows(g.ro_query(
        "MATCH (t:Ticket)-[:REFERENCES]->(:Function {name:$n}) "
        "RETURN t.id AS id, t.title AS title, t.status AS status", p))

    # rev1 (backend-generalization): compliance criticality is data-driven, not a
    # hardcoded function-name set. A function is critical when it (or a Decision
    # that JUSTIFIES it) is flagged `compliance_critical` in the graph.
    fn_flag = rows(g.ro_query(
        "MATCH (f:Function {name:$n}) "
        "RETURN coalesce(f.compliance_critical, false) AS flag", p))
    critical_decisions = rows(g.ro_query(
        "MATCH (d:Decision)-[:JUSTIFIES]->(:Function {name:$n}) "
        "WHERE coalesce(d.compliance_critical, false) = true "
        "RETURN d.id AS id", p))
    compliance_critical = bool(fn_flag and fn_flag[0]["flag"]) or bool(critical_decisions)

    teams_affected: dict[str, list[str]] = {}
    for t in teams:
        teams_affected.setdefault(t["team"], []).append(t["function"])

    score = len(callers) + 3 * len(decisions) + 2 * len(tickets)
    risk_hint = "HIGH" if score >= 6 else "MEDIUM" if score >= 3 else "LOW"

    return {
        "function": function,
        "file": found[0]["file"],
        "callers": [{"function": c["path"][0], "hops": c["hops"],
                     "call_path": " -> ".join(c["path"])} for c in callers],
        "callees": [{"function": c["path"][-1], "hops": c["hops"],
                     "call_path": " -> ".join(c["path"])} for c in callees],
        "teams_affected": teams_affected,
        "protecting_decisions": decisions,
        "impacted_tickets": tickets,
        "compliance_critical": compliance_critical,
        "compliance_decisions": [d["id"] for d in critical_decisions],
        "risk_hint": risk_hint,
    }


def find_true_expert(function: str, limit: int = 5) -> dict:
    """Identify true graph-verified domain experts (commits, reviews, Slack mentions, recency)
    and compare against the official org-chart team owner.
    """
    limit = max(1, min(int(limit), 20))
    g = knowledge()
    p = {"n": function}

    owner = rows(g.ro_query(
        "MATCH (t:Team)-[:OFFICIALLY_OWNS]->(:Function {name:$n}) "
        "OPTIONAL MATCH (l:Person)-[:LEADS]->(t) "
        "RETURN t.id AS team_id, t.name AS team, l.id AS lead_id, l.name AS lead", p))
    if not owner:
        return {"error": f"Unknown function '{function}'"}
    owner = owner[0]

    experts = rows(g.ro_query(
        "MATCH (p:Person)-[k:KNOWS_ABOUT]->(:Function {name:$n}) "
        "OPTIONAL MATCH (p)-[:MEMBER_OF]->(tm:Team) "
        "RETURN p.id AS id, p.name AS name, p.active AS active, tm.name AS team, "
        "k.score AS score, k.commits AS commits, k.reviews AS reviews, "
        "k.mentions AS mentions, k.last_activity AS last_activity "
        f"ORDER BY k.score DESC LIMIT {limit}", p))

    active = [e for e in experts if e["active"]]
    top3_ids = [e["id"] for e in experts[:3]]
    lead_row = next((e for e in experts if e["id"] == owner["lead_id"]), None)

    return {
        "function": function,
        "official_owner": {"team": owner["team"], "lead": owner["lead"],
                           "lead_knowledge_score": lead_row["score"] if lead_row else 0},
        "ranked_experts": experts,
        "recommended_reviewer": active[0] if active else None,
        "departed_experts": [e["name"] for e in experts if not e["active"]],
        "owner_knowledge_gap": owner["lead_id"] not in top3_ids,
    }


def get_decision_chain(function: str) -> dict:
    """Retrieve decision provenance: why does this code exist?
    Traces decisions, executive Slack promises, and Jira tickets.
    """
    g = knowledge()
    p = {"n": function}

    # Trace decisions that justify this function
    decisions = rows(g.ro_query(
        "MATCH (d:Decision)-[:JUSTIFIES]->(:Function {name:$n}) "
        "OPTIONAL MATCH (d)-[:DECIDED_IN]->(s:SlackThread) "
        "OPTIONAL MATCH (d)-[:DECIDED_IN]->(t:Ticket) "
        "RETURN d.id AS decision_id, d.summary AS summary, d.date AS decision_date, "
        "s.id AS slack_id, s.channel AS slack_channel, s.author AS slack_author, "
        "s.date AS slack_date, s.text AS slack_text, "
        "t.id AS ticket_id, t.title AS ticket_title, t.status AS ticket_status", p))

    # Trace direct Slack threads about this function
    direct_slack = rows(g.ro_query(
        "MATCH (s:SlackThread)-[:ABOUT]->(:Function {name:$n}) "
        "OPTIONAL MATCH (s)-[:LED_TO]->(t:Ticket) "
        "RETURN s.id AS slack_id, s.channel AS channel, s.author AS author, "
        "s.date AS date, s.text AS text, t.id AS ticket_id, t.title AS ticket_title", p))

    return {
        "function": function,
        "justifying_decisions": decisions,
        "related_conversations": direct_slack,
        "has_contractual_promise": any("contract" in str(d).lower() or "promise" in str(d).lower() for d in decisions + direct_slack)
    }


def get_memory_context(function: str, repo: str = None) -> dict:
    """Retrieve multi-tier agent memory for this function:
    1. Episodic: past outages, financial losses, and regressions (from memory graph).
    2. Procedural: safe migration playbooks and sequential checklists (from memory graph).
    3. Semantic: official runbooks and documentation (from knowledge graph).
    """
    g_mem = memory(repo)
    g_know = knowledge()
    p = {"n": function}

    # 1. Episodic Memory (Incidents)
    incidents = rows(g_mem.ro_query(
        "MATCH (inc:Incident)-[:AFFECTED]->(:Function {name:$n}) "
        "OPTIONAL MATCH (inc)-[:CAUSED_BY]->(pr:PullRequest) "
        "RETURN inc.id AS incident_id, inc.date AS date, inc.loss_usd AS loss_usd, "
        "inc.summary AS summary, pr.id AS caused_by_pr, pr.title AS pr_title", p))

    # 2. Procedural Memory (Playbooks & Safe Migration Steps)
    procedures = rows(g_mem.ro_query(
        "MATCH (proc:Procedure)-[:APPLIES_TO]->(:Function {name:$n}) "
        "OPTIONAL MATCH (proc)-[:LEARNED_FROM]->(inc:Incident) "
        "RETURN proc.id AS procedure_id, proc.title AS title, proc.steps AS steps, "
        "inc.id AS learned_from_incident", p))

    # 3. Semantic Memory (Runbooks & Documentation)
    docs = rows(g_know.ro_query(
        "MATCH (d:Doc)-[:DESCRIBES]->(:Function {name:$n}) "
        "RETURN d.id AS doc_id, d.title AS title, d.last_updated AS last_updated, "
        "coalesce(d.is_stale, false) AS is_stale", p))

    return {
        "function": function,
        "episodic_memory": {
            "incidents_count": len(incidents),
            "past_incidents": incidents
        },
        "procedural_memory": {
            "playbooks_count": len(procedures),
            "playbooks": procedures
        },
        "semantic_memory": {
            "docs_count": len(docs),
            "governing_docs": docs
        }
    }


def write_risk_finding(pr_id: str, function: str, risk_level: str, summary: str) -> dict:
    """Scout-Agent writes its risk assessment finding directly into the graph.
    Shared across agents so Fixer-Agent can act on it.
    """
    from datetime import datetime, timezone
    g_know = knowledge()
    p = {
        "pr_id": pr_id,
        "fn": function,
        "level": risk_level.upper(),
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Update PR node risk level and write an AgentFinding node
    q = """
    MATCH (pr:PullRequest {id:$pr_id})
    SET pr.risk_level = $level
    MERGE (af:AgentFinding {pr_id:$pr_id, function:$fn})
    SET af.risk_level = $level,
        af.summary = $summary,
        af.agent = 'Scout-Agent',
        af.updated_at = $timestamp
    MERGE (af)-[r:EVALUATED]->(pr)
    RETURN pr.id AS pr_id, pr.risk_level AS risk_level, af.summary AS summary
    """
    res = rows(g_know.query(q, p))
    return {
        "status": "recorded",
        "pr_id": pr_id,
        "function": function,
        "risk_level": risk_level.upper(),
        "summary": summary,
        "result": res[0] if res else {}
    }


def block_or_approve_pr(pr_id: str, function: str, decision: str, reviewer_name: str = "", risk_level: str = "HIGH") -> dict:
    """Fixer-Agent autonomous governance action:
    1. Sets PR state (e.g. BLOCKED, APPROVED).
    2. Flags connected documentation as is_stale = true.
    3. Links the true domain expert reviewer when one exists (skipped otherwise).
    """
    decision = decision.upper()
    g_know = knowledge()
    p = {
        "pr_id": pr_id,
        "fn": function,
        "decision": decision,
        "level": risk_level.upper(),
        "reviewer": reviewer_name
    }

    q = """
    MATCH (pr:PullRequest {id:$pr_id})
    SET pr.state = $decision,
        pr.risk_level = $level
    WITH pr
    OPTIONAL MATCH (doc:Doc)-[:DESCRIBES]->(:Function {name:$fn})
    FOREACH (d IN CASE WHEN doc IS NULL THEN [] ELSE [doc] END |
        SET d.is_stale = true,
            d.flagged_reason = 'Flagged stale due to PR ' + $pr_id + ' modifying ' + $fn
    )
    RETURN pr.id AS pr_id, pr.state AS new_state, pr.risk_level AS risk_level,
           collect(doc.title) AS flagged_stale_docs
    """
    pr_res = rows(g_know.query(q, p))

    # Link assigned reviewer if provided
    assigned_user = None
    if reviewer_name:
        assign_q = """
        MATCH (pr:PullRequest {id:$pr_id})
        MATCH (p:Person) WHERE p.name = $reviewer OR p.id = $reviewer
        MERGE (p)-[r:ASSIGNED_REVIEWER]->(pr)
        RETURN p.name AS assigned_to
        """
        rev_res = rows(g_know.query(assign_q, p))
        if rev_res:
            assigned_user = rev_res[0]["assigned_to"]

    return {
        "action": "completed",
        "pr_id": pr_id,
        "status": decision,
        "risk_level": risk_level.upper(),
        "assigned_reviewer": assigned_user or reviewer_name,
        "flagged_stale_docs": pr_res[0]["flagged_stale_docs"] if pr_res else []
    }


def get_subgraph_for_visualization(function: str = "applyDiscount", repo: str = None) -> dict:
    """Extracts nodes and edges formatted for PyVis / NetworkX / interactive web dashboards.
    Highlights blast radius paths, true experts, and decision provenance.
    """
    g_know = knowledge()
    g_mem = memory(repo)
    p = {"n": function}

    # Fetch knowledge nodes and edges connected to or around the target function
    know_res = g_know.query("""
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
    """)

    # Futuristic Cyber & Jade Green palette for nodes
    COLOR_MAP = {
        "Function": "#00FF9D",     # Jade Green
        "Person": "#10B981",       # Emerald
        "Team": "#38BDF8",         # Sky Blue
        "PullRequest": "#F59E0B",  # Amber
        "Doc": "#A78BFA",          # Violet
        "Ticket": "#EC4899",       # Pink
        "SlackThread": "#06B6D4",   # Cyan
        "Decision": "#FBBF24",     # Gold
        "Incident": "#EF4444",     # Red
        "Procedure": "#34D399",    # Light Jade
        "AgentFinding": "#F43F5E"  # Rose
    }

    nodes = {}
    edges = []

    def extract_node(node):
        if not node:
            return
        node_id = str(node.id)
        labels = getattr(node, "labels", ["Unknown"])
        primary_label = labels[0] if labels else "Unknown"
        props = getattr(node, "properties", {})
        title = props.get("name") or props.get("id") or props.get("title") or props.get("summary") or node_id
        
        # Determine specific icon/color
        color = COLOR_MAP.get(primary_label, "#94A3B8")
        if primary_label == "Person" and not props.get("active", True):
            color = "#64748B"  # Gray for departed experts
        elif primary_label == "Function" and props.get("name") == function:
            color = "#EF4444"  # Highlighted target in red

        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": f"{primary_label}: {title}",
                "group": primary_label,
                "title": f"<b>{primary_label}</b>: {title}<br/>" + "<br/>".join(f"{k}: {v}" for k, v in props.items()),
                "color": color,
                "properties": props
            }

    for record in know_res.result_set:
        n, r, m = record[0], record[1], record[2]
        extract_node(n)
        if m:
            extract_node(m)
        if r and n and m:
            rel_type = getattr(r, "relation", "RELATED_TO")
            edges.append({
                "from": str(n.id),
                "to": str(m.id),
                "label": rel_type,
                "title": rel_type
            })

    # Fetch memory graph nodes (Incidents & Procedures)
    try:
        mem_res = g_mem.query("MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m")
        for record in mem_res.result_set:
            n, r, m = record[0], record[1], record[2]
            # Use negative IDs for memory nodes to prevent collision
            if n:
                mem_n_id = f"mem_{n.id}"
                labels = getattr(n, "labels", ["Memory"])
                primary_label = labels[0] if labels else "Memory"
                props = getattr(n, "properties", {})
                title = props.get("id") or props.get("title") or props.get("summary") or mem_n_id
                nodes[mem_n_id] = {
                    "id": mem_n_id,
                    "label": f"{primary_label}: {title}",
                    "group": primary_label,
                    "title": f"<b>[Memory] {primary_label}</b>: {title}",
                    "color": COLOR_MAP.get(primary_label, "#14B8A6"),
                    "properties": props
                }
            if r and n and m:
                mem_m_id = f"mem_{m.id}"
                if mem_m_id in nodes:
                    edges.append({
                        "from": f"mem_{n.id}",
                        "to": mem_m_id,
                        "label": getattr(r, "relation", "MEMORY_REL"),
                        "title": getattr(r, "relation", "MEMORY_REL")
                    })
    except Exception:
        pass

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }


# ============================================================================
# TRACK 02: ADVANCED AGENT MEMORY & COORDINATION ENGINE
# ============================================================================

def record_blackboard_token(session_id: str, from_agent: str, to_agent: str, phase: str, message: str, payload: dict = None) -> dict:
    """Writes an active coordination token and working-memory payload to the FalkorDB Blackboard graph.
    Enables asynchronous multi-agent coordination without hidden in-memory state.
    """
    import json
    from datetime import datetime, timezone
    g_state = agent_state()
    token_id = f"tok_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload or {})

    p = {
        "sid": session_id,
        "tid": token_id,
        "fa": from_agent,
        "ta": to_agent,
        "ph": phase,
        "msg": message,
        "ts": timestamp,
        "pl": payload_str
    }

    q = """
    MERGE (s:Session {id:$sid})
    CREATE (t:CoordinationToken {
        id:$tid,
        from_agent:$fa,
        to_agent:$ta,
        phase:$ph,
        message:$msg,
        timestamp:$ts,
        payload:$pl
    })
    MERGE (s)-[r:COORDINATED]->(t)
    RETURN t.id AS token_id, t.from_agent AS from_agent, t.to_agent AS to_agent, t.phase AS phase
    """
    res = rows(g_state.query(q, p))
    return {
        "session_id": session_id,
        "token_id": token_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "phase": phase,
        "message": message,
        "timestamp": timestamp,
        "recorded": bool(res)
    }


def get_blackboard_session(session_id: str) -> dict:
    """Retrieves all coordination tokens and working-memory handoffs for an active session."""
    import json
    g_state = agent_state()
    p = {"sid": session_id}
    q = """
    MATCH (s:Session {id:$sid})-[:COORDINATED]->(t:CoordinationToken)
    RETURN t.id AS id, t.from_agent AS from_agent, t.to_agent AS to_agent,
           t.phase AS phase, t.message AS message, t.timestamp AS timestamp, t.payload AS payload
    ORDER BY t.timestamp ASC
    """
    tokens = rows(g_state.ro_query(q, p))
    parsed_tokens = []
    for t in tokens:
        try:
            pl = json.loads(t.get("payload") or "{}")
        except Exception:
            pl = {}
        parsed_tokens.append({
            "id": t["id"],
            "from_agent": t["from_agent"],
            "to_agent": t["to_agent"],
            "phase": t["phase"],
            "message": t["message"],
            "timestamp": t["timestamp"],
            "payload": pl
        })
    return {
        "session_id": session_id,
        "token_count": len(parsed_tokens),
        "tokens": parsed_tokens
    }


def query_cross_tenant_memory(function: str, primary_tenant: str) -> dict:
    """Track 02 Cross-Tenant Coordination:
    When a function changes in a primary tenant, assesses callers/callees that belong to
    DIFFERENT tenant repositories and pulls cross-tenant incidents/playbooks without
    breaking tenant isolation boundaries.
    """
    g_know = knowledge()
    p = {"n": function}

    # Find caller/callee functions and their assigned repository tenants
    q = """
    MATCH q=(c:Function)-[:CALLS*1..3]->(target:Function {name:$n})
    RETURN DISTINCT c.name AS name, c.repo AS repo
    """
    related_funcs = rows(g_know.ro_query(q, p))

    cross_tenant_bridges = []
    checked_repos = set()

    for item in related_funcs:
        repo = item.get("repo")
        func_name = item.get("name")
        if repo and repo != primary_tenant and repo not in checked_repos:
            checked_repos.add(repo)
            # Query isolated memory graph for foreign tenant
            foreign_mem = get_memory_context(func_name, repo=repo)
            foreign_incidents = foreign_mem["episodic_memory"]["past_incidents"]
            foreign_playbooks = foreign_mem["procedural_memory"]["playbooks"]
            
            if foreign_incidents or foreign_playbooks:
                cross_tenant_bridges.append({
                    "foreign_tenant": repo,
                    "bridged_function": func_name,
                    "cross_incidents": foreign_incidents,
                    "cross_playbooks": foreign_playbooks,
                    "coordination_rule": f"Cross-tenant dependency detected between {primary_tenant} and {repo} via function '{func_name}'."
                })

    return {
        "primary_tenant": primary_tenant,
        "target_function": function,
        "has_cross_tenant_risk": len(cross_tenant_bridges) > 0,
        "bridged_tenants": list(checked_repos),
        "bridges": cross_tenant_bridges
    }


def consolidate_new_learning(repo: str, function: str, incident_id: str, summary: str, loss_usd: int, playbook_title: str, playbook_steps: list[str]) -> dict:
    """Track 02 Dynamic Memory Consolidation:
    Learns from a new postmortem or incident by writing a new Incident and auto-derived
    Procedure directly into the tenant's FalkorDB memory graph.
    """
    from datetime import datetime, timezone
    g_mem = memory(repo)
    proc_id = f"P-AUTO-{int(datetime.now(timezone.utc).timestamp() % 10000):04d}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    p = {
        "inc_id": incident_id,
        "proc_id": proc_id,
        "fn": function,
        "summary": summary,
        "loss": int(loss_usd),
        "title": playbook_title,
        "steps": playbook_steps,
        "date": today
    }

    # 1. Create or Merge Function node in memory
    g_mem.query("MERGE (f:Function {name:$fn})", {"fn": function})

    # 2. Create Incident node & link to Function
    q_inc = """
    MERGE (i:Incident {id:$inc_id})
    SET i.date = $date,
        i.summary = $summary,
        i.loss_usd = $loss
    WITH i
    MATCH (f:Function {name:$fn})
    MERGE (i)-[r:AFFECTED]->(f)
    RETURN i.id AS inc_id
    """
    g_mem.query(q_inc, p)

    # 3. Create Procedure node & link to Incident and Function
    q_proc = """
    MERGE (p:Procedure {id:$proc_id})
    SET p.title = $title,
        p.steps = $steps
    WITH p
    MATCH (i:Incident {id:$inc_id})
    MERGE (p)-[r1:LEARNED_FROM]->(i)
    WITH p
    MATCH (f:Function {name:$fn})
    MERGE (p)-[r2:APPLIES_TO]->(f)
    RETURN p.id AS proc_id
    """
    g_mem.query(q_proc, p)

    # Verify new memory stats
    stats = get_memory_context(function, repo=repo)

    return {
        "status": "consolidated",
        "tenant_repo": repo,
        "target_function": function,
        "new_incident_id": incident_id,
        "new_procedure_id": proc_id,
        "learned_playbook_title": playbook_title,
        "updated_memory_stats": {
            "incidents": stats["episodic_memory"]["incidents_count"],
            "playbooks": stats["procedural_memory"]["playbooks_count"]
        }
    }


def get_full_instance_graph(filter_mode: str = "all") -> dict:
    """Extracts the entire multi-tenant FalkorDB instance graph topology across all 5 graphs:
    - dev_knowledge (82 nodes, 202 edges)
    - dev_memory_acme_checkout (23 nodes, 12 edges)
    - dev_memory_acme_auth (8 nodes, 4 edges)
    - dev_memory_acme_data (10 nodes, 8 edges)
    - dev_agent_state (36 nodes, 27 edges)

    Supports filter_mode: 'all', 'knowledge', 'memory', or 'agent_state'.
    Returns nodes and edges formatted for PyVis with rich labels, colors, shapes, and group metadata.
    """
    try:
        import db
    except ImportError:
        from graph import db

    c = db.client()
    prefix = db.PREFIX

    # Define palette & shapes by node label
    STYLE_CONFIG = {
        "Function": {"color": "#0e7d8c", "shape": "dot", "size": 18},
        "Person": {"color": "#10b981", "shape": "dot", "size": 20},
        "Team": {"color": "#0284c7", "shape": "square", "size": 24},
        "Decision": {"color": "#f59e0b", "shape": "diamond", "size": 22},
        "PullRequest": {"color": "#ea580c", "shape": "triangle", "size": 18},
        "Ticket": {"color": "#ec4899", "shape": "dot", "size": 16},
        "SlackThread": {"color": "#06b6d4", "shape": "dot", "size": 16},
        "Doc": {"color": "#8b5cf6", "shape": "dot", "size": 16},
        "Incident": {"color": "#b83a2b", "shape": "triangleDown", "size": 24},
        "Procedure": {"color": "#059669", "shape": "hexagon", "size": 20},
        "Session": {"color": "#4338ca", "shape": "star", "size": 24},
        "CoordinationToken": {"color": "#9333ea", "shape": "dot", "size": 16},
        "AgentFinding": {"color": "#e11d48", "shape": "dot", "size": 18},
    }

    graphs_to_query = []
    if filter_mode in ["all", "knowledge"]:
        graphs_to_query.append(("knowledge", f"{prefix}_knowledge", "Knowledge Graph"))
    if filter_mode in ["all", "memory"]:
        for t in ["acme_checkout", "acme_auth", "acme_data"]:
            graphs_to_query.append((f"memory_{t}", f"{prefix}_memory_{t}", f"Memory ({t})"))
    if filter_mode in ["all", "agent_state"]:
        graphs_to_query.append(("agent_state", f"{prefix}_agent_state", "Agent State"))

    nodes = {}
    edges = []

    def _format_node(n, domain, domain_label):
        if not n:
            return None
        nid = f"{domain}_{n.id}"
        if nid in nodes:
            return nid

        labels = getattr(n, "labels", ["Entity"])
        plabel = labels[0] if labels else "Entity"
        props = getattr(n, "properties", {})
        title_str = props.get("name") or props.get("id") or props.get("title") or props.get("summary") or nid
        if len(str(title_str)) > 30:
            short_title = str(title_str)[:27] + "..."
        else:
            short_title = str(title_str)

        style = STYLE_CONFIG.get(plabel, {"color": "#64748b", "shape": "dot", "size": 16})
        color = style["color"]
        if plabel == "Person" and not props.get("active", True):
            color = "#94a3b8"  # gray for departed

        tooltip_lines = [f"<b>[{domain_label}] {plabel}</b>: {title_str}"]
        for k, v in props.items():
            if k not in ["name", "id", "title"]:
                val_str = str(v)
                if len(val_str) > 80:
                    val_str = val_str[:77] + "..."
                tooltip_lines.append(f"{k}: {val_str}")
        tooltip = "<br/>".join(tooltip_lines)

        nodes[nid] = {
            "id": nid,
            "label": f"{plabel}\n{short_title}",
            "group": plabel,
            "domain": domain,
            "domain_label": domain_label,
            "title": tooltip,
            "color": color,
            "shape": style["shape"],
            "size": style["size"],
            "properties": props
        }
        return nid

    for domain, g_name, domain_label in graphs_to_query:
        try:
            g = c.select_graph(g_name)
            res = g.query("MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m")
            for row in res.result_set:
                n, r, m = row[0], row[1], row[2]
                nid = _format_node(n, domain, domain_label)
                mid = _format_node(m, domain, domain_label) if m else None
                if r and nid and mid:
                    rel_name = getattr(r, "relation", "CONNECTED_TO")
                    edges.append({
                        "from": nid,
                        "to": mid,
                        "label": rel_name,
                        "title": f"[{domain_label}] {rel_name}",
                        "domain": domain
                    })
        except Exception:
            pass

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "filter_mode": filter_mode
    }



