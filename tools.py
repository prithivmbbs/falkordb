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
    and associated Jira tickets.
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
    3. Auto-assigns the true domain expert reviewer to the PR.
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
    SET doc.is_stale = true,
        doc.flagged_reason = 'Flagged stale due to PR ' + $pr_id + ' modifying ' + $fn
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
        "assigned_reviewer": assigned_user or reviewer_name or "None",
        "flagged_stale_docs": pr_res[0]["flagged_stale_docs"] if pr_res else []
    }


def get_subgraph_for_visualization(function: str = "applyDiscount", repo: str = "acme_checkout") -> dict:
    """Extracts a clean, non-overlapping neighborhood subgraph around the target function.
    Adheres to the Perplexity AI Scholar's Parchment palette with concise labels and rich hover tooltips.
    """
    g_know = knowledge()
    g_mem = memory(repo)

    nodes = {}
    edges = []

    def add_node(node_id: str, label: str, group: str, title: str, color: str, size: int = 16, shape: str = "dot"):
        if node_id not in nodes:
            nodes[node_id] = {
                "id": str(node_id),
                "label": label,
                "group": group,
                "title": title,
                "color": color,
                "size": size,
                "shape": shape
            }

    def add_edge(from_id: str, to_id: str, label: str, title: str = ""):
        edges.append({
            "from": str(from_id),
            "to": str(to_id),
            "label": label,
            "title": title or label
        })

    # 1. Evaluated Target Function (Deep Teal anchor)
    target_id = f"fn_{function}"
    add_node(
        target_id,
        f"{function}()",
        "TargetFunction",
        f"<b>Target Function</b>: <code>{function}()</code><br/>Repository: {repo}",
        "#016a71",
        size=26,
        shape="dot"
    )

    # 2. Upstream Callers & Downstream Callees
    try:
        res_callers = g_know.query("""
            MATCH (c:Function)-[r:CALLS]->(fn:Function {name: $fn})
            RETURN c.name
        """, {"fn": function})
        for row in res_callers.result_set:
            c_name = row[0]
            c_id = f"fn_{c_name}"
            add_node(c_id, f"{c_name}()", "Caller", f"<b>Upstream Caller</b>: <code>{c_name}()</code>", "#27251e", size=15)
            add_edge(c_id, target_id, "CALLS")

        res_callees = g_know.query("""
            MATCH (fn:Function {name: $fn})-[r:CALLS]->(c:Function)
            RETURN c.name
        """, {"fn": function})
        for row in res_callees.result_set:
            c_name = row[0]
            c_id = f"fn_{c_name}"
            add_node(c_id, f"{c_name}()", "Callee", f"<b>Downstream Dependency</b>: <code>{c_name}()</code>", "#72706b", size=14)
            add_edge(target_id, c_id, "CALLS")
    except Exception:
        pass

    # 3. Key Experts (Top 2 ranked by recency-decay score)
    try:
        res_people = g_know.query("""
            MATCH (p:Person)-[r:KNOWS_ABOUT]->(fn:Function {name: $fn})
            RETURN p.name, p.active, r.score ORDER BY r.score DESC LIMIT 2
        """, {"fn": function})
        for row in res_people.result_set:
            p_name, active, score = row[0], row[1], row[2]
            p_id = f"person_{p_name}"
            status = "Active Expert" if active else "Departed"
            color = "#016a71" if active else "#92918b"
            add_node(
                p_id,
                f"👤 {p_name} ({'Active' if active else 'Departed'})",
                "Person",
                f"<b>{p_name}</b> ({status})<br/>Centrality Score: {round(float(score or 0), 2)}",
                color,
                size=18
            )
            add_edge(p_id, target_id, f"SCORE {round(float(score or 0), 1)}")
    except Exception:
        pass

    # 4. Living Contract Decisions
    try:
        res_dec = g_know.query("""
            MATCH (d:Decision)-[r:JUSTIFIES]->(fn:Function {name: $fn})
            RETURN d.id, d.summary
        """, {"fn": function})
        for row in res_dec.result_set:
            d_id, summary = row[0], row[1]
            node_id = f"dec_{d_id}"
            add_node(
                node_id,
                f"📜 {d_id}",
                "Decision",
                f"<b>Decision {d_id}</b><br/>{summary}",
                "#8a6100",
                size=18
            )
            add_edge(node_id, target_id, "JUSTIFIES")
    except Exception:
        pass

    # 5. Documentation
    try:
        res_docs = g_know.query("""
            MATCH (d:Doc)-[r:DESCRIBES]->(fn:Function {name: $fn})
            RETURN d.id, d.title
        """, {"fn": function})
        for row in res_docs.result_set:
            d_id, title = row[0], row[1]
            node_id = f"doc_{d_id}"
            add_node(
                node_id,
                f"📄 {d_id}",
                "Doc",
                f"<b>Doc {d_id}</b><br/>{title}",
                "#72706b",
                size=15
            )
            add_edge(node_id, target_id, "DESCRIBES")
    except Exception:
        pass

    # 6. Episodic Memory (Incidents) & Procedural Memory (Playbooks)
    try:
        res_mem = g_mem.query("""
            MATCH (inc:Incident)-[r:AFFECTED]->(fn:Function {name: $fn})
            OPTIONAL MATCH (proc:Procedure)-[r2:LEARNED_FROM]->(inc)
            RETURN inc.id, inc.loss_usd, inc.summary, proc.id, proc.title
        """, {"fn": function})
        for row in res_mem.result_set:
            inc_id, loss, summary, proc_id, proc_title = row[0], row[1], row[2], row[3], row[4]
            node_inc_id = f"inc_{inc_id}"
            loss_k = f"${int(loss/1000)}k" if loss else "$0"
            add_node(
                node_inc_id,
                f"⚠️ {inc_id} ({loss_k})",
                "Incident",
                f"<b>Incident {inc_id}</b><br/>Loss: ${loss:,}<br/>{summary}",
                "#b83a2b",
                size=20
            )
            add_edge(node_inc_id, target_id, "AFFECTED")

            if proc_id:
                node_proc_id = f"proc_{proc_id}"
                add_node(
                    node_proc_id,
                    f"📋 {proc_id}",
                    "Procedure",
                    f"<b>Playbook {proc_id}</b><br/>{proc_title}",
                    "#016a71",
                    size=17
                )
                add_edge(node_proc_id, node_inc_id, "LEARNED_FROM")
                add_edge(node_proc_id, target_id, "APPLIES_TO")
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


