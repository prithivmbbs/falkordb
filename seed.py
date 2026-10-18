"""Rebuilds your graphs from company.json. Safe to re-run any time.
Populates the knowledge graph and the multi-tenant memory graphs.

Run:
    python seed.py                               # uses ./company.json
    python seed.py --input other/company.json    # any company; auto-detects
                                                 # slack_export.json / jira_export.json /
                                                 # integration_mapping.json /
                                                 # compliance_rules.json siblings
Env:
    COMPANY_JSON      default input path (alternative to --input)
    INGEST_INPUT_DIR  folder to search for the optional export files (default: the
                      folder containing company.json)
"""
import argparse
import json
import os
import sys
from pathlib import Path

try:
    from db import client, knowledge, memory, agent_state, PREFIX, REPO
    from scoring import compute_knows_about
except ImportError:
    try:
        from files.db import client, knowledge, memory, agent_state, PREFIX, REPO
        from files.scoring import compute_knows_about
    except ImportError:
        from graph.db import client, knowledge, memory, agent_state, PREFIX, REPO
        from graph.scoring import compute_knows_about

try:
    import ingest
except ImportError:
    try:
        from files import ingest
    except ImportError:
        from graph import ingest

# Resilient data path lookup
DATA_CANDIDATES = [
    Path(__file__).resolve().parent / "company.json",
    Path(__file__).resolve().parent / "files" / "company.json",
    Path(__file__).resolve().parent / "data" / "company.json",
    Path(__file__).resolve().parent.parent / "files" / "company.json",
    Path(__file__).resolve().parent.parent / "data" / "company.json",
]
DATA = next((p for p in DATA_CANDIDATES if p.exists()), Path("company.json"))


def resolve_input_path(input_path: str = None) -> Path:
    """Resolve the company input path: explicit arg > COMPANY_JSON env > bundled default."""
    candidate = input_path or os.getenv("COMPANY_JSON")
    if candidate:
        p = Path(candidate).expanduser()
        if p.exists() or p.is_absolute():
            return p
        # Allow paths relative to this module's directory as a fallback.
        alt = Path(__file__).resolve().parent / p
        return alt if alt.exists() else p
    return DATA


def ingest_dir(company_path: Path) -> Path:
    """Folder searched for slack_export / jira_export / mapping / compliance siblings."""
    env_dir = os.getenv("INGEST_INPUT_DIR")
    if env_dir:
        p = Path(env_dir).expanduser()
        if not p.exists() and not p.is_absolute():
            alt = Path(__file__).resolve().parent / p
            if alt.exists():
                return alt
        return p
    return Path(company_path).parent


def reset(g):
    try:
        g.delete()
    except Exception:
        pass  # graph did not exist yet


def load_nodes(g, label, key, items, props):
    if not items:
        return
    keys = [key] + props
    rows_ = [{k: i.get(k) for k in keys} for i in items]
    sets = ", ".join(f"n.{p}=r.{p}" for p in props)
    q = f"UNWIND $rows AS r MERGE (n:{label} {{{key}:r.{key}}})"
    if sets:
        q += f" SET {sets}"
    g.query(q, {"rows": rows_})


def load_edges(g, rel, fl, fk, tl, tk, pairs, props=()):
    if not pairs:
        return
    sets = (" SET " + ", ".join(f"e.{p}=r.{p}" for p in props)) if props else ""
    g.query(
        f"UNWIND $rows AS r MATCH (a:{fl} {{{fk}:r.a}}), (b:{tl} {{{tk}:r.b}}) "
        f"MERGE (a)-[e:{rel}]->(b){sets}", {"rows": pairs})


def make_indexes(g, pairs):
    for label, prop in pairs:
        try:
            g.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
        except Exception as e:
            pass


def seed_knowledge(d):
    g = knowledge()
    reset(g)
    load_nodes(g, "Team", "id", d.get("teams", []), ["name", "repo"])
    load_nodes(g, "Person", "id", d.get("people", []), ["name", "active", "left_on"])
    load_nodes(g, "Function", "name", d.get("functions", []), ["file", "repo", "compliance_critical"])
    load_nodes(g, "PullRequest", "id", d.get("pull_requests", []), ["title", "date", "state", "risk_level", "repo"])
    load_nodes(g, "SlackThread", "id", d.get("slack", []), ["channel", "date", "text"])
    load_nodes(g, "Ticket", "id", d.get("tickets", []), ["title", "status", "date"])
    load_nodes(g, "Decision", "id", d.get("decisions", []), ["summary", "date", "compliance_critical"])
    load_nodes(g, "Doc", "id", d.get("docs", []), ["title", "last_updated", "repo"])

    # Initialize Doc.is_stale = false
    g.query("MATCH (d:Doc) WHERE d.is_stale IS NULL SET d.is_stale = false")

    make_indexes(g, [("Person", "id"), ("Team", "id"), ("Function", "name"),
                     ("PullRequest", "id"), ("SlackThread", "id"), ("Ticket", "id"),
                     ("Decision", "id"), ("Doc", "id")])

    E = lambda a, b, **p: {"a": a, "b": b, **p}
    load_edges(g, "MEMBER_OF", "Person", "id", "Team", "id",
               [E(p["id"], p["team"]) for p in d.get("people", []) if p.get("team")])
    load_edges(g, "LEADS", "Person", "id", "Team", "id",
               [E(t["lead"], t["id"]) for t in d.get("teams", []) if t.get("lead")])
    load_edges(g, "OFFICIALLY_OWNS", "Team", "id", "Function", "name",
               [E(f["owner_team"], f["name"]) for f in d.get("functions", []) if f.get("owner_team")])
    load_edges(g, "CALLS", "Function", "name", "Function", "name",
               [E(f["name"], c) for f in d.get("functions", []) for c in f.get("calls", [])])
    load_edges(g, "COMMITTED", "Person", "id", "Function", "name",
               [E(c["person"], c["function"], count=c["count"], last=c["last"]) for c in d.get("commits", [])],
               ["count", "last"])
    load_edges(g, "AUTHORED", "Person", "id", "PullRequest", "id",
               [E(p["author"], p["id"]) for p in d.get("pull_requests", []) if p.get("author")])
    load_edges(g, "REVIEWED", "Person", "id", "PullRequest", "id",
               [E(r, p["id"]) for p in d.get("pull_requests", []) for r in p.get("reviewers", [])])
    load_edges(g, "MODIFIES", "PullRequest", "id", "Function", "name",
               [E(p["id"], f) for p in d.get("pull_requests", []) for f in p.get("modifies", [])])
    load_edges(g, "POSTED", "Person", "id", "SlackThread", "id",
               [E(s["author"], s["id"]) for s in d.get("slack", []) if s.get("author")])
    load_edges(g, "MENTIONED_IN", "Person", "id", "SlackThread", "id",
               [E(m, s["id"]) for s in d.get("slack", []) for m in s.get("mentions", [])])
    load_edges(g, "ABOUT", "SlackThread", "id", "Function", "name",
               [E(s["id"], f) for s in d.get("slack", []) for f in s.get("about", [])])
    load_edges(g, "LED_TO", "SlackThread", "id", "Ticket", "id",
               [E(s["id"], s["led_to_ticket"]) for s in d.get("slack", []) if s.get("led_to_ticket")])
    load_edges(g, "REFERENCES", "Ticket", "id", "Function", "name",
               [E(t["id"], f) for t in d.get("tickets", []) for f in t.get("references", [])])
    load_edges(g, "JUSTIFIES", "Decision", "id", "Function", "name",
               [E(x["id"], f) for x in d.get("decisions", []) for f in x.get("justifies", [])])
    load_edges(g, "DECIDED_IN", "Decision", "id", "SlackThread", "id",
               [E(x["id"], s) for x in d.get("decisions", []) for s in x.get("decided_in_slack", [])])
    load_edges(g, "DECIDED_IN", "Decision", "id", "Ticket", "id",
               [E(x["id"], t) for x in d.get("decisions", []) for t in x.get("decided_in_ticket", [])])
    load_edges(g, "DESCRIBES", "Doc", "id", "Function", "name",
               [E(x["id"], f) for x in d.get("docs", []) for f in x.get("describes", [])])

    n = compute_knows_about(g)
    print(f"Knowledge graph '{PREFIX}_knowledge' ready ({n} KNOWS_ABOUT edges computed)")


def seed_memory_for_repo(d, repo_name: str):
    g = client().select_graph(f"{PREFIX}_memory_{repo_name}")
    reset(g)

    # Filter items specific to this tenant repo (fall back to the deployment's REPO)
    repo_functions = [f for f in d.get("functions", []) if (f.get("repo") or REPO) == repo_name]
    repo_prs = [pr for pr in d.get("pull_requests", []) if (pr.get("repo") or REPO) == repo_name]
    repo_incidents = [i for i in d.get("incidents", []) if (i.get("repo") or REPO) == repo_name]
    repo_procedures = [p for p in d.get("procedures", []) if (p.get("repo") or REPO) == repo_name]

    load_nodes(g, "Function", "name", repo_functions, [])
    load_nodes(g, "PullRequest", "id", repo_prs, ["title"])
    load_nodes(g, "Incident", "id", repo_incidents, ["date", "loss_usd", "summary"])
    load_nodes(g, "Procedure", "id", repo_procedures, ["title", "steps"])

    make_indexes(g, [("Function", "name"), ("PullRequest", "id"),
                     ("Incident", "id"), ("Procedure", "id")])

    E = lambda a, b: {"a": a, "b": b}
    load_edges(g, "CAUSED_BY", "Incident", "id", "PullRequest", "id",
               [E(i["id"], i["caused_by_pr"]) for i in repo_incidents if i.get("caused_by_pr")])
    load_edges(g, "AFFECTED", "Incident", "id", "Function", "name",
               [E(i["id"], f) for i in repo_incidents for f in i.get("affected", [])])
    load_edges(g, "LEARNED_FROM", "Procedure", "id", "Incident", "id",
               [E(p["id"], p["learned_from"]) for p in repo_procedures if p.get("learned_from")])
    load_edges(g, "APPLIES_TO", "Procedure", "id", "Function", "name",
               [E(p["id"], f) for p in repo_procedures for f in p.get("applies_to", [])])

    print(f"Memory graph '{PREFIX}_memory_{repo_name}' ready ({len(repo_incidents)} incidents, {len(repo_procedures)} playbooks)")


def seed_agent_state():
    g = agent_state()
    reset(g)
    make_indexes(g, [("Session", "id"), ("CoordinationToken", "id"), ("CoordinationToken", "phase")])
    print(f"Agent state graph '{PREFIX}_agent_state' ready (blackboard coordination workspace initialized)")


def load_company_data(path: Path) -> dict:
    """Load company.json directly, or run the ingestion layer when export siblings exist."""
    export_dir = ingest_dir(path)
    try:
        found = ingest.find_input_files(export_dir)
    except Exception:
        found = {}

    if any(found.values()):
        try:
            data, summary = ingest.normalize_inputs(path, input_dir=export_dir)
        except ingest.IngestValidationError as exc:
            print(f"\n[ABORT] Company input validation failed for {path}:\n")
            for err in exc.errors:
                print(f"  - {err}")
            raise SystemExit(1)
        print(ingest.format_summary(summary))
        return data

    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"Loaded {path} directly (no slack_export/jira_export/integration_mapping/compliance_rules found in {export_dir}).")
    return data


def seed_all(input_path: str = None):
    path = resolve_input_path(input_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot find company.json at '{path}'. Checked defaults: {[str(p) for p in DATA_CANDIDATES]} "
            f"(or pass --input / COMPANY_JSON)."
        )
    data = load_company_data(path)

    # 1. Seed Knowledge Graph
    seed_knowledge(data)

    # 2. Seed Multi-Tenant Memory Graphs (Track 02 isolation)
    tenants = data.get("tenants") or [REPO]
    for tenant in tenants:
        seed_memory_for_repo(data, tenant)

    # 3. Seed Agent Coordination State Graph (Track 02 Blackboard)
    seed_agent_state()

    print("\nAll FalkorDB multi-tenant and agent coordination graphs successfully seeded!")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Seed NexusGuard FalkorDB graphs from company.json "
                    "(auto-ingests sibling Slack/Jira exports when present)."
    )
    parser.add_argument(
        "--input", "-i", default=None,
        help="Path to company.json (default: COMPANY_JSON env, then ./company.json).",
    )
    args = parser.parse_args(argv)
    try:
        seed_all(input_path=args.input)
    except SystemExit as exc:
        sys.exit(exc.code)


if __name__ == "__main__":
    main()
