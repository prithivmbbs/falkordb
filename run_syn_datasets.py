"""Run every synthetic dataset in syn_data_sets/ through seed + a smoke simulation.

Usage (from falkordb/):
    python run_syn_datasets.py

Each dataset gets its own GRAPH_PREFIX (syn_<name>) so the dev demo graphs are untouched.
Exits non-zero if any dataset fails to seed or simulate.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYN = ROOT / "syn_data_sets"
VENV_PY = Path("/tmp/opencode/venv/bin/python")
if not VENV_PY.exists():
    VENV_PY = Path(sys.executable)

datasets = sorted(p for p in SYN.iterdir() if p.is_dir() and (p / "company.json").exists())

failures = []


def run(cmd, env, label):
    print(f"\n--- {label} ---")
    print(" ".join(cmd))
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(ROOT))
    if r.stdout:
        print(r.stdout[-2000:])
    if r.stderr:
        print("STDERR:", r.stderr[-2000:])
    return r.returncode, r


for ds in datasets:
    name = ds.name
    prefix = f"syn_{name}"
    company_path = ds / "company.json"
    data = json.loads(company_path.read_text())
    tenants = data.get("tenants") or []
    first_tenant = tenants[0] if tenants else "default"
    # pick first PR + function
    prs = data.get("pull_requests") or []
    smoke_pr = prs[0]["id"] if prs else None
    smoke_fn = (prs[0].get("modifies") or [None])[0] if prs else None
    smoke_repo = prs[0].get("repo") if prs else None
    if not smoke_fn:
        smoke_fn = (data.get("functions") or [{}])[0].get("name")
    if not smoke_repo:
        smoke_repo = first_tenant

    env = dict(os.environ)
    env["GRAPH_PREFIX"] = prefix
    env["REPO_NAME"] = first_tenant
    env["COMPANY_JSON"] = str(company_path)
    env["INGEST_INPUT_DIR"] = str(ds)
    env["FALKOR_HOST"] = env.get("FALKOR_HOST", "localhost")
    env["FALKOR_PORT"] = env.get("FALKOR_PORT", "6379")

    rc, _ = run([str(VENV_PY), "seed.py"], env, f"{name}: seed")
    if rc != 0:
        failures.append((name, "seed", rc))
        continue

    if smoke_pr and smoke_fn:
        smoke_code = (
            "import os, json\n"
            "from agents import GovernanceOrchestrator\n"
            "o = GovernanceOrchestrator()\n"
            f"sim = o.simulate_pr(pr_id={smoke_pr!r}, target_function={smoke_fn!r}, repo={smoke_repo!r})\n"
            "print('DECISION:', sim['decision'])\n"
            "print('REVIEWER:', sim['assigned_reviewer'])\n"
            "print('RISK:', sim['risk_level'])\n"
        )
        rc, _ = run([str(VENV_PY), "-c", smoke_code], env, f"{name}: smoke simulate {smoke_pr}/{smoke_fn}")
        if rc != 0:
            failures.append((name, "simulate", rc))

print("\n" + "=" * 72)
if failures:
    print(f"RESULT: {len(failures)} FAILURE(S)")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("RESULT: ALL DATASETS SEEDED + SIMULATED SUCCESSFULLY")
sys.exit(0)
