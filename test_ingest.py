"""Unit tests for ingest.py (no FalkorDB required).

Validates:
  1. Slack normalization (ts -> id/date, channel lookup, author/mention mapping,
     text mention parsing fallback, subtype filtering).
  2. Jira normalization (REST envelope -> tickets[], label fallback, ISO dates).
  3. Merge behavior (no duplicate ids, unknown Slack users materialized as Persons,
     compliance_rules override of inline compliance_critical flags, decision_rules).
  4. Validation rejects malformed input with a clear error list.
  5. normalize_inputs() end-to-end on a tiny synthetic dataset written to a temp dir.

Run:
    python test_ingest.py
Exit code is non-zero if any assertion fails.
"""
import json
import sys
import tempfile
from pathlib import Path

import ingest

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    if not condition:
        failures.append(label)
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")


def sample_company() -> dict:
    return {
        "tenants": ["tn", "other_tn"],
        "tenant_names": {"tn": "Tenant N"},
        "teams": [
            {"id": "team-n", "name": "Team N", "lead": "lead-n", "repo": "tn"},
            {"id": "team-o", "name": "Team O", "lead": "lead-o", "repo": "other_tn"},
        ],
        "people": [
            {"id": "lead-n", "name": "Lead N", "active": True, "team": "team-n"},
            {"id": "lead-o", "name": "Lead O", "active": True, "team": "team-o"},
            {"id": "sam", "name": "Sam", "active": True, "team": "team-n"},
        ],
        "functions": [
            {"name": "doWork", "file": "a.py", "owner_team": "team-n", "calls": [],
             "repo": "tn", "compliance_critical": True},
            {"name": "helper", "file": "b.py", "owner_team": "team-o", "calls": ["doWork"], "repo": "other_tn"},
        ],
        "commits": [{"person": "sam", "function": "doWork", "count": 2, "last": "2026-01-02"}],
        "pull_requests": [
            {"id": "PR-X1", "title": "T", "date": "2026-01-03", "state": "open", "repo": "tn",
             "author": "sam", "reviewers": [], "modifies": ["doWork"]},
        ],
        "slack": [],
        "tickets": [{"id": "TK-9", "title": "Existing", "status": "done", "date": "2026-01-01", "references": ["doWork"]}],
        "decisions": [],
        "docs": [],
        "incidents": [],
        "procedures": [],
    }


def test_slack_normalization() -> None:
    print("\n[1] Slack normalization")
    slack_raw = {
        "users": [
            {"id": "UAAA", "name": "sam", "real_name": "Sam S"},
            {"id": "UBBB", "name": "lead-n", "real_name": "Lead N"},
        ],
        "channels": [{"id": "C001", "name": "eng"}],
        "messages": [
            {"ts": "1760000000.000100", "user": "UAAA", "channel": "C001",
             "text": "We should not delete doWork <@UBBB>!"},
            {"ts": "1760000100.000200", "user": "UAAA", "channel": "C001",
             "text": "joining now", "subtype": "channel_join"},
            {"ts": "1760000200.000300", "user": "UBBB", "channel": "C001",
             "text": "bare mention @UCCC here"},
        ],
    }
    mapping = {
        "slack_authors": {"1760000000.000100": "sam"},
        "slack_mentions": {"1760000000.000100": ["lead-n"]},
        "slack_to_functions": {"1760000000.000100": ["doWork"]},
        "slack_to_tickets": {"1760000000.000100": "TK-9"},
    }
    out = ingest.normalize_slack(slack_raw, mapping)
    check("system subtypes filtered", len(out) == 2, f"got {len(out)}")
    first = out[0]
    check("id is ts", first["id"] == "1760000000.000100")
    check("date parsed (UTC)", first["date"] == "2025-10-09", first["date"])
    check("channel #-prefixed from id lookup", first["channel"] == "#eng", str(first["channel"]))
    check("author mapped to internal id", first["author"] == "sam", str(first["author"]))
    check("mentions from mapping", first["mentions"] == ["lead-n"], str(first["mentions"]))
    check("about from mapping", first["about"] == ["doWork"])
    check("led_to_ticket from mapping", first["led_to_ticket"] == "TK-9")
    second = out[1]
    check("bare mentions parsed when unmapped", second["mentions"] == ["UCCC"], str(second["mentions"]))
    check("unmapped slack id kept as author", second["author"] == "UBBB", str(second["author"]))

    # timestamp with millisecond fraction (real Slack values)
    frac = ingest.normalize_slack(
        {"users": [], "channels": [], "messages": [{"ts": "1355517523.000005", "user": "U1", "text": "hi"}]})
    check("fractional ts parsed", frac and frac[0]["date"] == "2012-12-14", str(frac))


def test_jira_normalization() -> None:
    print("\n[2] Jira normalization")
    jira_raw = {
        "expand": "names,schema",
        "total": 2,
        "issues": [
            {"id": "10001", "key": "EX-1",
             "fields": {"summary": "Broken flow", "status": {"name": "Open"},
                        "created": "2026-01-17T12:34:00.000+0000", "labels": ["doWork"]}},
            {"id": "10002", "key": "EX-2",
             "fields": {"summary": "Unknown label", "status": {"name": "Done"},
                        "created": "2026-02-02T00:00:00.000+0000", "labels": ["nope"]}},
        ],
    }
    mapping = {}
    out = ingest.normalize_jira(jira_raw, mapping, known_functions={"doWork", "helper"})
    check("two issues imported", len(out) == 2, f"got {len(out)}")
    check("id is key", out[0]["id"] == "EX-1")
    check("title is summary", out[0]["title"] == "Broken flow")
    check("status is name", out[0]["status"] == "Open")
    check("date truncated", out[0]["date"] == "2026-01-17", str(out[0]["date"]))
    check("label fallback filters to known functions", out[0]["references"] == ["doWork"], str(out[0]["references"]))
    check("unknown label yields no references", out[1]["references"] == [], str(out[1]["references"]))

    # mapping takes precedence over labels
    out2 = ingest.normalize_jira(jira_raw, {"jira_to_functions": {"EX-1": ["helper"]}}, known_functions={"doWork"})
    check("mapping overrides labels", out2[0]["references"] == ["helper"], str(out2[0]["references"]))


def test_merge_and_compliance() -> None:
    print("\n[3] Merge, persons, compliance override")
    company = sample_company()
    slack_norm = [{
        "id": "1760000300.000400", "channel": "#eng", "date": "2026-10-10",
        "author": "UZZZ", "text": "hello", "mentions": ["lead-n"], "about": [], "led_to_ticket": None,
    }]
    jira_norm = [{"id": "TK-9", "title": "Duplicate", "status": "x", "date": "2026-01-01", "references": []},
                 {"id": "EX-3", "title": "New", "status": "Open", "date": "2026-01-18", "references": ["helper"]}]
    merged = ingest.merge(
        company, slack_norm, jira_norm,
        compliance={"compliance_critical_functions": ["helper"]},
        decision_rules=[{"id": "D-X", "summary": "s", "date": "2026-01-01", "justifies": ["helper"],
                         "decided_in_slack": [], "decided_in_ticket": []}],
    )
    check("existing ticket not duplicated", len([t for t in merged["tickets"] if t["id"] == "TK-9"]) == 1)
    check("new jira ticket merged", any(t["id"] == "EX-3" for t in merged["tickets"]))
    check("new slack thread merged", any(s["id"] == "1760000300.000400" for s in merged["slack"]))
    check("unknown slack author materialized as Person",
          any(p["id"] == "UZZZ" and p["active"] and p["team"] is None for p in merged["people"]))
    check("decision rule merged", any(d["id"] == "D-X" for d in merged["decisions"]))
    fn = {f["name"]: f for f in merged["functions"]}
    check("compliance override sets listed fn true", fn["helper"]["compliance_critical"] is True)
    check("compliance override clears unlisted fn", fn["doWork"]["compliance_critical"] is False)
    check("original company untouched (deep copy)", company["functions"][0]["compliance_critical"] is True)


def test_validation() -> None:
    print("\n[4] Validation")
    good = sample_company()
    check("valid sample company passes", ingest.validate_company(good) == [], str(ingest.validate_company(good))[:200])

    bad = sample_company()
    bad["tenants"] = []
    bad["functions"][0]["repo"] = "ghost_repo"
    bad["functions"][0]["owner_team"] = "ghost_team"
    bad["commits"].append({"person": "ghost", "function": "ghost_fn", "count": 1, "last": "2026-01-01"})
    bad["pull_requests"][0]["author"] = "ghost"
    bad["pull_requests"][0]["modifies"] = ["ghost_fn"]
    bad["tickets"][0]["references"] = ["ghost_fn"]
    errors = ingest.validate_company(bad)
    check("malformed input rejected", len(errors) >= 7, f"{len(errors)} errors")
    joined = "\n".join(errors)
    check("error mentions tenants", "tenants" in joined)
    check("error mentions unknown person", "unknown person 'ghost'" in joined.replace("references unknown person", "references unknown person"))
    check("error mentions unknown function", "ghost_fn" in joined)


def test_normalize_inputs_end_to_end() -> None:
    print("\n[5] normalize_inputs() end-to-end")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "company.json").write_text(json.dumps(sample_company()), encoding="utf-8")
        (tmp_path / "slack_export.json").write_text(json.dumps({
            "users": [{"id": "UAAA", "name": "sam"}],
            "channels": [{"id": "C001", "name": "eng"}],
            "messages": [{"ts": "1760000000.000100", "user": "UAAA", "channel": "C001",
                          "text": "mapped: <@UBBB> should review."}],
        }), encoding="utf-8")
        (tmp_path / "jira_export.json").write_text(json.dumps({
            "issues": [{"id": "1", "key": "EX-7", "fields": {
                "summary": "Label fallback", "status": {"name": "Open"},
                "created": "2026-03-01T00:00:00.000+0000", "labels": ["helper"]}}],
        }), encoding="utf-8")
        (tmp_path / "integration_mapping.json").write_text(json.dumps({
            "slack_authors": {"1760000000.000100": "sam"},
            "slack_mentions": {"1760000000.000100": ["lead-n"]},
            "slack_to_functions": {"1760000000.000100": ["doWork"]},
            "slack_to_tickets": {"1760000000.000100": "EX-7"},
            "decision_rules": [{"id": "D-Y", "summary": "s", "date": "2026-01-01",
                                "justifies": ["helper"], "decided_in_slack": [], "decided_in_ticket": []}],
        }), encoding="utf-8")
        (tmp_path / "compliance_rules.json").write_text(json.dumps(
            {"compliance_critical_functions": ["doWork"]}), encoding="utf-8")

        merged, summary = ingest.normalize_inputs(tmp_path / "company.json")
        check("slack imported", summary["slack"]["used"] and summary["slack"]["imported"] == 1, str(summary["slack"]))
        check("jira imported", summary["jira"]["used"] and summary["jira"]["imported"] == 1, str(summary["jira"]))
        check("compliance used", summary["compliance"]["used"])
        check("merged validated (no exception)", True)
        check("slack about linked to doWork",
              any(s["id"] == "1760000000.000100" and s["about"] == ["doWork"] for s in merged["slack"]))
        check("jira label fallback linked to helper",
              any(t["id"] == "EX-7" and t["references"] == ["helper"] for t in merged["tickets"]))
        check("decision rule from mapping merged", any(d["id"] == "D-Y" for d in merged["decisions"]))
        check("slack_to_tickets resolves (no validation abort)", True)

        out = ingest.write_normalized(merged, tmp_path / "normalized.json")
        check("write_normalized produces a file", out.exists())

        # invalid dataset must abort with a clear error list
        (tmp_path / "company.json").write_text(json.dumps({"tenants": [], "functions": []}), encoding="utf-8")
        try:
            ingest.normalize_inputs(tmp_path / "company.json")
            check("invalid dataset raises IngestValidationError", False)
        except ingest.IngestValidationError as exc:
            check("invalid dataset raises IngestValidationError", True)
            check("error list is human-readable", len(exc.errors) >= 2, f"{len(exc.errors)} errors")


def main() -> int:
    print("=" * 72)
    print("NexusGuard ingest unit tests (rev1 backend-generalization)")
    print("=" * 72)
    test_slack_normalization()
    test_jira_normalization()
    test_merge_and_compliance()
    test_validation()
    test_normalize_inputs_end_to_end()

    print("\n" + "=" * 72)
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
