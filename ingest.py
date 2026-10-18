"""Ingestion & normalization layer for NexusGuard JSON inputs (rev1 backend-generalization).

Takes the documented JSON inputs and produces a single normalized company document
that ``seed.py`` already understands -- no graph schema changes required:

    company.json               authoritative internal format (generalized)
    slack_export.json          raw Slack workspace export (flat JSON, dir, or .zip)
    jira_export.json           Jira REST ``/rest/api/3/search`` response
    integration_mapping.json   bridge from raw Slack/Jira ids to internal graph ids
    compliance_rules.json      optional override of inline compliance_critical flags

Contracts and examples: ``docs/json_contracts.md`` and ``docs/examples/``.
This module is dependency-free (stdlib only) and does not touch FalkorDB, so the
normalizers can be unit-tested without a running database (see ``test_ingest.py``).
"""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Input file discovery (siblings of company.json, or INGEST_INPUT_DIR if set)
# ---------------------------------------------------------------------------
SLACK_EXPORT_NAMES = ("slack_export.json", "slack_export.zip")
JIRA_EXPORT_NAMES = ("jira_export.json",)
MAPPING_FILE_NAMES = ("integration_mapping.json",)
COMPLIANCE_FILE_NAMES = ("compliance_rules.json",)

# Slack subtypes that carry no text/context we can attach to the graph.
_IGNORED_SLACK_SUBTYPES = {
    "channel_join", "channel_leave", "channel_topic", "channel_purpose",
    "channel_name", "channel_archive", "channel_unarchive", "message_deleted",
}

_SLACK_MENTION_RE = re.compile(r"<@([A-Z][A-Z0-9_]*)(?:\|[^>]+)?>")
_SLACK_BARE_MENTION_RE = re.compile(r"(?<!<)@([A-Z][A-Z0-9_]{1,})")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


class IngestValidationError(ValueError):
    """Raised when the normalized company document fails validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("Company input validation failed:\n  - " + "\n  - ".join(errors))


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def _read_json(path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_company(path) -> dict:
    """Load and type-check the authoritative company document."""
    data = _read_json(path)
    if not isinstance(data, dict):
        raise IngestValidationError([f"{path}: company document must be a JSON object"])
    return data


def load_mapping(path) -> dict:
    """Load the optional integration mapping (raw ids -> internal graph ids)."""
    data = _read_json(path)
    if not isinstance(data, dict):
        raise IngestValidationError([f"{path}: integration_mapping must be a JSON object"])
    return data


def load_compliance(path) -> dict:
    """Load the optional compliance rules file."""
    data = _read_json(path)
    if not isinstance(data, dict):
        raise IngestValidationError([f"{path}: compliance_rules must be a JSON object"])
    return data


def load_jira(path) -> dict:
    """Load a Jira export. Accepts the REST search envelope or a bare issue array."""
    data = _read_json(path)
    if isinstance(data, list):
        return {"issues": data}
    if not isinstance(data, dict):
        raise IngestValidationError([f"{path}: jira export must be a JSON object or array"])
    return data


def load_slack(path) -> dict:
    """Load a Slack export into ``{"users": [...], "channels": [...], "messages": [...]}``.

    Accepted shapes:
      * flat JSON export: ``{"users": [...], "channels": [...], "messages": [...]}``
      * a directory of a raw workspace export (users.json/channels.json/<channel>/<day>.json)
      * a ``.zip`` of the raw workspace export
    """
    p = Path(path)
    if p.is_dir():
        return _load_slack_export_dir(p)
    if p.suffix.lower() == ".zip":
        return _load_slack_export_zip(p)
    data = _read_json(p)
    if isinstance(data, list):
        return {"users": [], "channels": [], "messages": data}
    if not isinstance(data, dict):
        raise IngestValidationError([f"{path}: slack export must be an object, array, directory, or zip"])
    return {
        "users": data.get("users") or [],
        "channels": data.get("channels") or [],
        "messages": data.get("messages") or [],
    }


def _annotate_channel(messages, folder_name: str) -> list[dict]:
    annotated = []
    for msg in messages or []:
        if isinstance(msg, dict):
            msg.setdefault("_channel_folder", folder_name)
            annotated.append(msg)
    return annotated


def _load_slack_export_dir(root: Path) -> dict:
    users = _read_json(root / "users.json") if (root / "users.json").exists() else []
    channels = _read_json(root / "channels.json") if (root / "channels.json").exists() else []
    messages: list[dict] = []
    for channel_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for day_file in sorted(channel_dir.glob("*.json")):
            try:
                day_messages = _read_json(day_file)
            except Exception:
                continue
            if isinstance(day_messages, list):
                messages.extend(_annotate_channel(day_messages, channel_dir.name))
    return {"users": users, "channels": channels, "messages": messages}


def _load_slack_export_zip(path: Path) -> dict:
    users: list = []
    channels: list = []
    messages: list[dict] = []
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if "users.json" in names:
            users = json.loads(zf.read("users.json"))
        if "channels.json" in names:
            channels = json.loads(zf.read("channels.json"))
        for name in names:
            parts = name.split("/")
            if len(parts) == 2 and parts[1].endswith(".json") and parts[0] != "__MACOSX":
                try:
                    day_messages = json.loads(zf.read(name))
                except Exception:
                    continue
                if isinstance(day_messages, list):
                    messages.extend(_annotate_channel(day_messages, parts[0]))
    return {"users": users, "channels": channels, "messages": messages}


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------
def _dedupe(items) -> list:
    out = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def _ts_to_date(ts) -> Optional[str]:
    try:
        return datetime.fromtimestamp(float(str(ts)), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def _clean_channel(name) -> Optional[str]:
    if not name:
        return None
    name = str(name).strip()
    return name if name.startswith("#") else f"#{name}"


def normalize_slack(slack_raw: dict, mapping: Optional[dict] = None) -> list[dict]:
    """Convert raw Slack messages into the internal ``slack[]`` shape.

    Mapping keys (all optional, keyed by message ``ts``):
      ``slack_authors[ts]``       -> internal person id for the author
      ``slack_mentions[ts]``      -> internal person ids mentioned
      ``slack_to_functions[ts]``  -> internal function names the thread is about
      ``slack_to_tickets[ts]``    -> internal ticket id the thread led to

    ``id`` is the message ``ts`` (unique per workspace). Unknown authors keep the
    raw Slack user id; ``merge()`` materializes them as Person nodes so no data
    is lost. Messages with no mapping import in degraded mode (empty about/
    mentions/led_to_ticket).
    """
    mapping = mapping or {}
    channel_name_by_id = {
        c.get("id"): c.get("name") for c in (slack_raw.get("channels") or []) if isinstance(c, dict)
    }
    map_authors = mapping.get("slack_authors") or {}
    map_mentions = mapping.get("slack_mentions") or {}
    map_functions = mapping.get("slack_to_functions") or {}
    map_tickets = mapping.get("slack_to_tickets") or {}

    normalized: list[dict] = []
    seen: set[str] = set()
    for msg in slack_raw.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        if msg.get("subtype") in _IGNORED_SLACK_SUBTYPES:
            continue
        ts = msg.get("ts")
        text = msg.get("text")
        if not ts or text is None:
            continue
        ts = str(ts)
        if ts in seen:
            continue
        date = _ts_to_date(ts)
        if not date:
            continue
        seen.add(ts)

        channel_raw = msg.get("_channel_folder") or msg.get("channel")
        channel = _clean_channel(channel_name_by_id.get(channel_raw, channel_raw))

        raw_author = msg.get("user") or msg.get("bot_id")
        author = map_authors.get(ts) or raw_author

        if ts in map_mentions:
            mentions = list(map_mentions.get(ts) or [])
        else:
            mentions = _SLACK_MENTION_RE.findall(text) + _SLACK_BARE_MENTION_RE.findall(text)
        mentions = [m for m in _dedupe(mentions) if m != author]

        normalized.append({
            "id": ts,
            "channel": channel,
            "date": date,
            "author": author,
            "text": text,
            "mentions": mentions,
            "about": _dedupe(map_functions.get(ts) or []),
            "led_to_ticket": map_tickets.get(ts),
        })
    return normalized


def normalize_jira(jira_raw: dict, mapping: Optional[dict] = None,
                   known_functions: Optional[set] = None) -> list[dict]:
    """Convert a Jira search export into the internal ``tickets[]`` shape.

    ``id`` is the issue key, ``references`` comes from
    ``integration_mapping.jira_to_functions[key]`` when present, otherwise from
    issue labels filtered to names of known functions.
    """
    mapping = mapping or {}
    known = set(known_functions or set())
    map_functions = mapping.get("jira_to_functions") or {}

    normalized: list[dict] = []
    seen: set[str] = set()
    for issue in jira_raw.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        key = issue.get("key") or issue.get("id")
        if not key or key in seen:
            continue
        seen.add(str(key))
        key = str(key)
        fields = issue.get("fields") or {}
        status = fields.get("status")
        status_name = status.get("name") if isinstance(status, dict) else status

        created = str(fields.get("created") or "")
        date = created[:10] if _ISO_DATE_RE.match(created) else None

        references = list(map_functions.get(key) or [])
        if not references:
            labels = fields.get("labels") or []
            references = [str(label) for label in labels if str(label) in known]

        normalized.append({
            "id": key,
            "title": fields.get("summary") or key,
            "status": str(status_name) if status_name else "unknown",
            "date": date,
            "references": _dedupe(references),
        })
    return normalized


# ---------------------------------------------------------------------------
# Merge + validation
# ---------------------------------------------------------------------------
def merge(company: dict, slack_norm: Optional[list] = None, jira_norm: Optional[list] = None,
          compliance: Optional[dict] = None, decision_rules: Optional[list] = None) -> dict:
    """Merge normalized Slack/Jira output (and compliance overrides) into the company doc.

    - Slack threads / Jira tickets already present by ``id`` are not duplicated.
    - Unknown Slack authors/mentions are materialized as Person nodes
      (id = raw Slack user id, active=true, team=null), so no data is lost.
    - ``compliance`` (if present) *overrides* the inline ``compliance_critical``
      flags for the keys it defines; absent keys keep the inline flags.
    """
    merged = json.loads(json.dumps(company))  # stdlib deep copy

    people = merged.setdefault("people", [])
    people_ids = {p.get("id") for p in people}

    def ensure_person(pid):
        if pid and pid not in people_ids:
            people.append({"id": pid, "name": pid, "active": True, "team": None})
            people_ids.add(pid)

    existing_slack = {s.get("id") for s in merged.setdefault("slack", [])}
    for thread in slack_norm or []:
        if thread.get("id") in existing_slack:
            continue
        merged["slack"].append(thread)
        existing_slack.add(thread.get("id"))
        ensure_person(thread.get("author"))
        for mention in thread.get("mentions", []):
            ensure_person(mention)

    existing_tickets = {t.get("id") for t in merged.setdefault("tickets", [])}
    for ticket in jira_norm or []:
        if ticket.get("id") in existing_tickets:
            continue
        merged["tickets"].append(ticket)
        existing_tickets.add(ticket.get("id"))

    existing_decisions = {d.get("id") for d in merged.setdefault("decisions", [])}
    for rule in decision_rules or []:
        if rule.get("id") and rule["id"] not in existing_decisions:
            merged["decisions"].append(rule)
            existing_decisions.add(rule["id"])

    if compliance:
        if "compliance_critical_functions" in compliance:
            critical = set(compliance.get("compliance_critical_functions") or [])
            for fn in merged.setdefault("functions", []):
                fn["compliance_critical"] = fn.get("name") in critical
        if "compliance_critical_decisions" in compliance:
            critical = set(compliance.get("compliance_critical_decisions") or [])
            for decision in merged.get("decisions", []):
                decision["compliance_critical"] = decision.get("id") in critical

    return merged


def validate_company(data: dict) -> list[str]:
    """Validate the normalized company document; returns a list of error strings.

    Empty list == valid. Missing optional fields default sensibly (empty lists,
    null, false); structural references (repo/team/person/function/ticket/...)
    must resolve so seeding cannot silently drop edges.
    """
    errors: list[str] = []

    tenants = data.get("tenants") or []
    if not tenants:
        errors.append("'tenants' must be a non-empty list of repository ids")
    tenant_ids = set(tenants)

    team_ids = {t.get("id") for t in data.get("teams", []) if t.get("id")}
    person_ids = {p.get("id") for p in data.get("people", []) if p.get("id")}
    function_names = {f.get("name") for f in data.get("functions", []) if f.get("name")}
    ticket_ids = {t.get("id") for t in data.get("tickets", []) if t.get("id")}
    slack_ids = {s.get("id") for s in data.get("slack", []) if s.get("id")}
    incident_ids = {i.get("id") for i in data.get("incidents", []) if i.get("id")}

    if not data.get("functions"):
        errors.append("'functions' must be a non-empty list")

    for team in data.get("teams", []):
        if not team.get("id"):
            errors.append("team entry missing 'id'")
        if team.get("lead") and team["lead"] not in person_ids:
            errors.append(f"team '{team.get('id')}' lead '{team['lead']}' is not a known person")
        if team.get("repo") not in tenant_ids:
            errors.append(f"team '{team.get('id')}' repo '{team.get('repo')}' is not in tenants")

    for person in data.get("people", []):
        if not person.get("id"):
            errors.append("person entry missing 'id'")
        if person.get("team") and person["team"] not in team_ids:
            errors.append(f"person '{person.get('id')}' team '{person.get('team')}' is not a known team")

    for fn in data.get("functions", []):
        name = fn.get("name")
        if not name:
            errors.append("function entry missing 'name'")
        if fn.get("repo") not in tenant_ids:
            errors.append(f"function '{name}' repo '{fn.get('repo')}' is not in tenants")
        if fn.get("owner_team") not in team_ids:
            errors.append(f"function '{name}' owner_team '{fn.get('owner_team')}' is not a known team")
        for callee in fn.get("calls") or []:
            if callee not in function_names:
                errors.append(f"function '{name}' calls unknown function '{callee}'")

    for commit in data.get("commits", []):
        if commit.get("person") not in person_ids:
            errors.append(f"commit references unknown person '{commit.get('person')}'")
        if commit.get("function") not in function_names:
            errors.append(f"commit references unknown function '{commit.get('function')}'")

    for pr in data.get("pull_requests", []):
        if not pr.get("id"):
            errors.append("pull_request entry missing 'id'")
        if pr.get("author") and pr["author"] not in person_ids:
            errors.append(f"PR '{pr.get('id')}' author '{pr['author']}' is not a known person")
        for reviewer in pr.get("reviewers") or []:
            if reviewer not in person_ids:
                errors.append(f"PR '{pr.get('id')}' reviewer '{reviewer}' is not a known person")
        for fn_name in pr.get("modifies") or []:
            if fn_name not in function_names:
                errors.append(f"PR '{pr.get('id')}' modifies unknown function '{fn_name}'")

    for thread in data.get("slack", []):
        if thread.get("author") and thread["author"] not in person_ids:
            errors.append(f"slack '{thread.get('id')}' author '{thread['author']}' is not a known person")
        for mention in thread.get("mentions") or []:
            if mention not in person_ids:
                errors.append(f"slack '{thread.get('id')}' mentions unknown person '{mention}'")
        for fn_name in thread.get("about") or []:
            if fn_name not in function_names:
                errors.append(f"slack '{thread.get('id')}' is about unknown function '{fn_name}'")
        if thread.get("led_to_ticket") and thread["led_to_ticket"] not in ticket_ids:
            errors.append(f"slack '{thread.get('id')}' led_to_ticket '{thread['led_to_ticket']}' is unknown")

    for ticket in data.get("tickets", []):
        if not ticket.get("id"):
            errors.append("ticket entry missing 'id'")
        for fn_name in ticket.get("references") or []:
            if fn_name not in function_names:
                errors.append(f"ticket '{ticket.get('id')}' references unknown function '{fn_name}'")

    for decision in data.get("decisions", []):
        if not decision.get("id"):
            errors.append("decision entry missing 'id'")
        for fn_name in decision.get("justifies") or []:
            if fn_name not in function_names:
                errors.append(f"decision '{decision.get('id')}' justifies unknown function '{fn_name}'")
        for slack_id in decision.get("decided_in_slack") or []:
            if slack_id not in slack_ids:
                errors.append(f"decision '{decision.get('id')}' decided_in_slack '{slack_id}' is unknown")
        for ticket_id in decision.get("decided_in_ticket") or []:
            if ticket_id not in ticket_ids:
                errors.append(f"decision '{decision.get('id')}' decided_in_ticket '{ticket_id}' is unknown")

    for doc in data.get("docs", []):
        if not doc.get("id"):
            errors.append("doc entry missing 'id'")
        if doc.get("repo") and doc["repo"] not in tenant_ids:
            errors.append(f"doc '{doc.get('id')}' repo '{doc['repo']}' is not in tenants")
        for fn_name in doc.get("describes") or []:
            if fn_name not in function_names:
                errors.append(f"doc '{doc.get('id')}' describes unknown function '{fn_name}'")

    for incident in data.get("incidents", []):
        if not incident.get("id"):
            errors.append("incident entry missing 'id'")
        if incident.get("repo") and incident["repo"] not in tenant_ids:
            errors.append(f"incident '{incident.get('id')}' repo '{incident['repo']}' is not in tenants")
        # caused_by_pr intentionally not validated: historical PRs may predate the export.
        for fn_name in incident.get("affected") or []:
            if fn_name not in function_names:
                errors.append(f"incident '{incident.get('id')}' affects unknown function '{fn_name}'")

    for procedure in data.get("procedures", []):
        if not procedure.get("id"):
            errors.append("procedure entry missing 'id'")
        if procedure.get("repo") and procedure["repo"] not in tenant_ids:
            errors.append(f"procedure '{procedure.get('id')}' repo '{procedure['repo']}' is not in tenants")
        if procedure.get("learned_from") and procedure["learned_from"] not in incident_ids:
            errors.append(f"procedure '{procedure.get('id')}' learned_from unknown incident '{procedure['learned_from']}'")
        for fn_name in procedure.get("applies_to") or []:
            if fn_name not in function_names:
                errors.append(f"procedure '{procedure.get('id')}' applies_to unknown function '{fn_name}'")

    return errors


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def find_input_files(input_dir) -> dict:
    """Locate the optional sibling input files inside ``input_dir``."""
    base = Path(input_dir)

    def first(names):
        for name in names:
            candidate = base / name
            if candidate.exists():
                return candidate
        return None

    return {
        "slack": first(SLACK_EXPORT_NAMES),
        "jira": first(JIRA_EXPORT_NAMES),
        "mapping": first(MAPPING_FILE_NAMES),
        "compliance": first(COMPLIANCE_FILE_NAMES),
    }


def normalize_inputs(company_path, input_dir=None, write_to=None) -> tuple[dict, dict]:
    """Load company.json + optional sibling exports and return ``(merged, summary)``.

    Raises ``IngestValidationError`` (with a clear error list) when the merged
    document fails validation, so callers can abort seeding.
    """
    company_path = Path(company_path)
    company = load_company(company_path)
    search_dir = Path(input_dir) if input_dir else company_path.parent

    found = find_input_files(search_dir)
    mapping = load_mapping(found["mapping"]) if found["mapping"] else {}

    slack_norm = []
    if found["slack"]:
        slack_norm = normalize_slack(load_slack(found["slack"]), mapping)

    known_functions = {f.get("name") for f in company.get("functions", []) if f.get("name")}
    jira_norm = []
    if found["jira"]:
        jira_norm = normalize_jira(load_jira(found["jira"]), mapping, known_functions)

    compliance = load_compliance(found["compliance"]) if found["compliance"] else None
    decision_rules = list(mapping.get("decision_rules") or [])

    merged = merge(company, slack_norm, jira_norm, compliance, decision_rules=decision_rules)

    errors = validate_company(merged)
    if errors:
        raise IngestValidationError(errors)

    if write_to:
        write_normalized(merged, write_to)

    original_people = {p.get("id") for p in company.get("people", [])}
    summary = {
        "company_path": str(company_path),
        "input_dir": str(search_dir),
        "slack": {
            "used": bool(found["slack"]),
            "path": str(found["slack"]) if found["slack"] else None,
            "imported": len(slack_norm),
        },
        "jira": {
            "used": bool(found["jira"]),
            "path": str(found["jira"]) if found["jira"] else None,
            "imported": len(jira_norm),
        },
        "mapping": {
            "used": bool(found["mapping"]),
            "path": str(found["mapping"]) if found["mapping"] else None,
        },
        "compliance": {
            "used": bool(found["compliance"]),
            "path": str(found["compliance"]) if found["compliance"] else None,
        },
        "decision_rules_imported": len(decision_rules),
        "new_people": len([p for p in merged.get("people", []) if p.get("id") not in original_people]),
        "tenants": {
            tenant: len([f for f in merged.get("functions", []) if f.get("repo") == tenant])
            for tenant in merged.get("tenants", [])
        },
    }
    return merged, summary


def write_normalized(company: dict, out_path) -> Path:
    """Persist the normalized company document (debug / reproducibility aid)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(company, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def format_summary(summary: dict) -> str:
    """Human-readable ingestion summary printed by ``seed.py``."""
    lines = ["Ingestion summary:"]
    lines.append(f"  company input : {summary['company_path']}")
    lines.append(f"  search dir    : {summary['input_dir']}")
    if summary["slack"]["used"]:
        lines.append(f"  slack export  : {summary['slack']['path']} -> {summary['slack']['imported']} SlackThread(s)")
    if summary["jira"]["used"]:
        lines.append(f"  jira export   : {summary['jira']['path']} -> {summary['jira']['imported']} Ticket(s)")
    if summary["mapping"]["used"]:
        lines.append(f"  mapping       : {summary['mapping']['path']} -> {summary['decision_rules_imported']} decision rule(s)")
    if summary["compliance"]["used"]:
        lines.append(f"  compliance    : {summary['compliance']['path']} (overrides inline compliance flags)")
    if summary.get("new_people"):
        lines.append(f"  new persons   : {summary['new_people']} (materialized from raw Slack ids)")
    if summary.get("tenants"):
        per_tenant = ", ".join(f"{t} ({n} fn)" for t, n in summary["tenants"].items())
        lines.append(f"  tenants       : {per_tenant}")
    return "\n".join(lines)
