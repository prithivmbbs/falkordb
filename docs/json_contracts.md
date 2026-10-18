# NexusGuard JSON input contracts (onboarding a new company)

Dropping a new `company.json` (plus optional Slack/Jira exports) into a folder and running
`python seed.py --input <path>` is all it takes to onboard a company — **no code edits, no
API keys, no UI changes**. This document defines every input file.

## Input discovery

Given `seed.py --input path/to/company.json` (or `COMPANY_JSON=...`), the ingestion layer
(`ingest.py`) looks for these optional siblings in the same folder:

| File | Required | Purpose |
|---|---|---|
| `company.json` | ✅ | authoritative internal company graph document |
| `slack_export.json` (or `slack_export.zip`, or a raw-export directory) | optional | raw Slack data for provenance threads |
| `jira_export.json` | optional | raw Jira issue data for tickets |
| `integration_mapping.json` | optional | bridges raw Slack/Jira ids to internal graph ids |
| `compliance_rules.json` | optional | overrides inline `compliance_critical` flags |

`INGEST_INPUT_DIR` (env) overrides the search folder. If none of the optional files exist,
`company.json` is seeded directly (the original Acme flow, fully backward compatible).
If any exist, `ingest.normalize_inputs()` merges them and **validates** the result; seeding
aborts with a clear error list on validation failure.

---

## 1. `company.json` (authoritative, generalized)

```jsonc
{
  "tenants": ["<repo_id>", ...],            // required, non-empty
  "tenant_names": {"<repo_id>": "Display name"},  // optional, cosmetic (used by REST/UI)

  "teams": [
    {"id": "...", "name": "...", "lead": "<person_id or null>", "repo": "<repo_id>"}
  ],
  "people": [
    {"id": "...", "name": "...", "active": true, "team": "<team_id or null>", "left_on": "YYYY-MM-DD"}
  ],
  "functions": [
    {"name": "...", "file": "...", "owner_team": "<team_id>", "calls": ["<fn_name>", ...],
     "repo": "<repo_id>", "compliance_critical": true}   // flag optional, default false
  ],
  "commits": [
    {"person": "<person_id>", "function": "<fn_name>", "count": 1, "last": "YYYY-MM-DD"}
  ],
  "pull_requests": [
    {"id": "...", "title": "...", "date": "YYYY-MM-DD", "state": "open", "repo": "<repo_id>",
     "author": "<person_id>", "reviewers": ["<person_id>"], "modifies": ["<fn_name>"]}
  ],
  "slack": [                                 // may also be produced by the Slack normalizer
    {"id": "...", "channel": "#...", "date": "YYYY-MM-DD", "author": "<person_id or null>",
     "text": "...", "mentions": ["<person_id>"], "about": ["<fn_name>"],
     "led_to_ticket": "<ticket_id or null>"}
  ],
  "tickets": [
    {"id": "...", "title": "...", "status": "...", "date": "YYYY-MM-DD", "references": ["<fn_name>"]}
  ],
  "decisions": [
    {"id": "...", "summary": "...", "date": "YYYY-MM-DD", "justifies": ["<fn_name>"],
     "decided_in_slack": ["<slack_id>"], "decided_in_ticket": ["<ticket_id>"],
     "compliance_critical": true}            // flag optional, default false
  ],
  "docs": [
    {"id": "...", "title": "...", "last_updated": "YYYY-MM-DD", "describes": ["<fn_name>"], "repo": "<repo_id>"}
  ],
  "incidents": [
    {"id": "...", "date": "YYYY-MM-DD", "loss_usd": 0, "summary": "...", "repo": "<repo_id>",
     "caused_by_pr": "<pr_id or null>", "affected": ["<fn_name>"]}
  ],
  "procedures": [
    {"id": "...", "title": "...", "steps": ["..."], "repo": "<repo_id>",
     "learned_from": "<incident_id or null>", "applies_to": ["<fn_name>"]}
  ]
}
```

Rules enforced by `ingest.validate_company()`:

- `tenants` is non-empty; every `team.repo`, `function.repo`, `doc.repo`, `incident.repo`,
  `procedure.repo` is listed in `tenants`.
- `team.lead`, `person.team`, `function.owner_team`, `commit.person`, `pr.author`,
  `pr.reviewers`, `slack.author`, `slack.mentions` resolve to known nodes or null.
- `function.calls`, `commit.function`, `pr.modifies`, `slack.about`, `ticket.references`,
  `decision.justifies`, `doc.describes`, `incident.affected`, `procedure.applies_to`
  resolve to known function names.
- `decision.decided_in_slack` / `decided_in_ticket`, `slack.led_to_ticket`,
  `procedure.learned_from` resolve (can be null/empty).
- `incident.caused_by_pr` is **not** validated: historical PRs may predate the export.

### Compliance-critical marking (replaces the old hardcoded set)

A function is treated as compliance-critical when either:

1. `functions[].compliance_critical == true`, or
2. any `Decision` with `compliance_critical == true` `JUSTIFIES` it, or
3. `compliance_rules.json` lists it (overrides inline flags).

If none of these apply, no function is compliance-critical (conservative: fewer false blocks).

---

## 2. `slack_export.json` (raw Slack data)

Accepted shapes:

- **Flat JSON** (recommended): `{"users": [...], "channels": [...], "messages": [...]}`
  where each message is a Slack message object.
- **Raw workspace export directory** (`users.json`, `channels.json`, one folder per channel
  with one JSON file per day — the standard Slack JSON export layout).
- **A `.zip` of that export.**

Normalizer mapping (Slack → internal `slack[]`):

| Internal field | Source |
|---|---|
| `id` | message `ts` (unique per workspace) |
| `channel` | channel name via `channels.json` lookup, `#`-prefixed |
| `date` | `ts` Unix timestamp → `YYYY-MM-DD` (UTC) |
| `author` | `integration_mapping.slack_authors[ts]`, else the raw Slack user id |
| `text` | message `text` |
| `mentions` | `integration_mapping.slack_mentions[ts]`, else parsed `<@U123>` / `@U123` from text |
| `about` | `integration_mapping.slack_to_functions[ts]` |
| `led_to_ticket` | `integration_mapping.slack_to_tickets[ts]` |

System subtypes (`channel_join`, `message_deleted`, …) are skipped. Messages with no mapping
still import, with empty `about`/`mentions`/`led_to_ticket` (degraded but non-fatal).
Slack users that appear but are not mapped are materialized as Person nodes
(`id` = Slack user id, `active: true`, `team: null`) so no data is lost.

Example: `docs/examples/slack_export.example.json`.

---

## 3. `jira_export.json` (raw Jira data)

Accepted shapes: the REST `GET /rest/api/3/search?jql=...` response (`{"issues": [...]}`)
or a bare array of issues.

Normalizer mapping (Jira → internal `tickets[]`):

| Internal field | Source |
|---|---|
| `id` | issue `key` |
| `title` | `fields.summary` |
| `status` | `fields.status.name` |
| `date` | `fields.created` → `YYYY-MM-DD` |
| `references` | `integration_mapping.jira_to_functions[key]`; if absent, `fields.labels` filtered to known function names |

Example: `docs/examples/jira_export.example.json`.

---

## 4. `integration_mapping.json` (the bridge)

Without it, Slack/Jira import as standalone nodes with no function/ticket links
(degraded but non-fatal).

```jsonc
{
  "slack_to_functions": {"<ts>": ["<fn_name>"]},
  "slack_to_tickets":   {"<ts>": "<ticket_id>"},
  "slack_mentions":     {"<ts>": ["<person_id>"]},
  "slack_authors":      {"<ts>": "<person_id>"},
  "jira_to_functions":  {"<issue_key>": ["<fn_name>"]},
  "jira_to_slack":      {"<issue_key>": ["<ts>"]},          // informational
  "decision_rules": [
    {"id": "...", "summary": "...", "date": "YYYY-MM-DD", "justifies": ["<fn_name>"],
     "decided_in_slack": ["<ts>"], "decided_in_ticket": ["<issue_key>"],
     "compliance_critical": false}
  ]
}
```

`decision_rules` are appended to `decisions[]` (skipped if the id already exists).

Example: `docs/examples/integration_mapping.example.json`.

---

## 5. `compliance_rules.json` (optional override)

```jsonc
{
  "compliance_critical_functions": ["<fn_name>", ...],
  "compliance_critical_decisions": ["<decision_id>", ...]
}
```

Each key, when present, **overrides** the inline flags from `company.json` for that node
type: listed names become `true`, all others `false`. Absent keys keep inline flags.
If neither the rules file nor inline flags mark anything, no function is compliance-critical.

Example: `docs/examples/compliance_rules.example.json`.

---

## 6. Non-Acme validation dataset

`unseen/` holds a complete, name-disjoint sample company (Nova, tenants `nova_trade` /
`nova_risk` / `nova_wallet`) built to exercise every generalization path:
`unseen/company_unseen.json` + `slack_export.json` + `jira_export.json` +
`integration_mapping.json` + `compliance_rules.json`.

```bash
# Isolated graphs (GRAPH_PREFIX), does not touch the Acme demo:
GRAPH_PREFIX=gencheck python test_unseen.py
```

## 7. Debug helper

`ingest.write_normalized(company, out_path)` writes the merged document for inspection:

```python
import ingest
merged, summary = ingest.normalize_inputs("unseen/company_unseen.json")
ingest.write_normalized(merged, "/tmp/normalized.json")
print(ingest.format_summary(summary))
```
