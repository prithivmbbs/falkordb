# Provenance: graph schema (the contract between both teammates)

Change this file first, then change code. Never rename a label or relationship without telling your teammate.

## Graphs (one FalkorDB instance)
| Graph name | Contents | Written by |
|---|---|---|
| `<PREFIX>_knowledge` | Code, people, commits, PRs, and company facts | `seed.py` |
| `<PREFIX>_memory_<REPO>` | Incidents, procedures, living ADRs (isolated per tenant) | `seed.py` / agents (`consolidate_new_learning`) |
| `<PREFIX>_agent_state` | Blackboard coordination tokens & working memory | agents (`record_blackboard_token`) |

`PREFIX` comes from `.env` (default: `dev`).

## Conventions
- Every node has a stable unique key: `id` (or `name` for `Function`).
- Dates are ISO strings: `2026-03-02`.
- Tools use `ro_query` (read-only) and fixed parameterized Cypher. Agents never write raw Cypher.
- Always cap variable-length paths: `[:CALLS*1..5]`.

## Knowledge graph
**Nodes**
| Label | Key | Properties |
|---|---|---|
| Person | id | name, active, left_on |
| Team | id | name |
| Function | name | file |
| PullRequest | id | title, date, state (open/merged) |
| SlackThread | id | channel, date, text |
| Ticket | id | title, status, date |
| Decision | id | summary, date |
| Doc | id | title, last_updated |

**Relationships**
```
(Person)-[:MEMBER_OF]->(Team)
(Person)-[:LEADS]->(Team)
(Team)-[:OFFICIALLY_OWNS]->(Function)
(Function)-[:CALLS]->(Function)
(Person)-[:COMMITTED {count, last}]->(Function)
(Person)-[:AUTHORED]->(PullRequest)
(Person)-[:REVIEWED]->(PullRequest)
(PullRequest)-[:MODIFIES]->(Function)
(Person)-[:POSTED]->(SlackThread)
(Person)-[:MENTIONED_IN]->(SlackThread)
(SlackThread)-[:ABOUT]->(Function)
(SlackThread)-[:LED_TO]->(Ticket)
(Ticket)-[:REFERENCES]->(Function)
(Decision)-[:JUSTIFIES]->(Function)
(Decision)-[:DECIDED_IN]->(SlackThread | Ticket)
(Doc)-[:DESCRIBES]->(Function)
(Person)-[:KNOWS_ABOUT {score, commits, reviews, mentions, last_activity}]->(Function)   <- COMPUTED by graph/scoring.py
```

## Memory graph (per repo)
**Nodes:** Incident(id, date, loss_usd, summary), Procedure(id, title, steps[]), plus stub Function(name) and PullRequest(id, title).
```
(Incident)-[:CAUSED_BY]->(PullRequest)
(Incident)-[:AFFECTED]->(Function)
(Procedure)-[:LEARNED_FROM]->(Incident)
(Procedure)-[:APPLIES_TO]->(Function)
```
Note: function and PR names are duplicated as stubs here because FalkorDB queries run inside one graph. Use the shared `id`/`name` to join results in Python.

## Agent state graph (dev_agent_state)
**Nodes:**
| Label | Key | Properties |
|---|---|---|
| Session | id | id, created_at |
| CoordinationToken | id | token_id, from_agent, to_agent, phase, message, timestamp, payload |

**Relationships:**
```
(Session)-[:COORDINATED]->(CoordinationToken)
```

## KNOWS_ABOUT score
```
score = (commits*1 + reviews*2 + mentions*0.5) * 0.5^(days_since_last_activity / 365)
```
Weights live in `scoring.py`.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
docker run -p 6379:6379 -p 3000:3000 -d --name falkordb falkordb/falkordb:latest
python seed.py            # builds knowledge, memory, and blackboard graphs
python test_tools.py      # runs automated tests for tools
python mcp_server.py      # starts the FastMCP server (stdio)
streamlit run app.py      # launches the CRYO-PULSE web dashboard
```
Open http://localhost:3000 and run `MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 50` to inspect the graphs.
