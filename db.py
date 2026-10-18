"""FalkorDB connection helpers supporting both Docker and Cloud environments.
Reads configuration from .env with fallback support for both FALKOR_ and FALKORDB_ prefixes.
"""
import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

# Load .env from current directory or parent directory
env_path = Path(".env")
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

PREFIX = os.getenv("GRAPH_PREFIX", "dev")
REPO = os.getenv("REPO_NAME", "acme_checkout")

# Folder searched by ingest.py for optional Slack/Jira/mapping/compliance JSON files
# (default: the folder containing company.json). Consumed by seed.py's ingest_dir().
INGEST_INPUT_DIR = os.getenv("INGEST_INPUT_DIR", ".")


def _get_config(key, default=None):
    """Retrieve config from st.secrets if available (Streamlit Cloud), else os.environ."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


@lru_cache(maxsize=1)
def client():
    from falkordb import FalkorDB

    # 1. Direct connection URL support (e.g. falkor://default:pass@host:port or falkors://)
    url = _get_config("FALKORDB_URL", _get_config("FALKOR_URL"))
    if url:
        return FalkorDB.from_url(
            url,
            ssl_cert_reqs="none",
            ssl_check_hostname=False,
            socket_timeout=15.0,
            socket_connect_timeout=15.0
        )

    # 2. Key-value credentials
    host = _get_config("FALKOR_HOST", _get_config("FALKORDB_HOST", "localhost"))
    port = int(_get_config("FALKOR_PORT", _get_config("FALKORDB_PORT", "6379")))
    password = _get_config("FALKOR_PASSWORD", _get_config("FALKORDB_PASSWORD"))
    username = _get_config("FALKOR_USERNAME", _get_config("FALKORDB_USERNAME"))
    ssl_flag = str(_get_config("FALKOR_SSL", _get_config("FALKORDB_SSL", "false"))).lower() in ("true", "1", "yes")

    kwargs = {
        "host": host,
        "port": port,
        "ssl": ssl_flag,
        "socket_timeout": 15.0,
        "socket_connect_timeout": 15.0,
    }
    if ssl_flag:
        kwargs["ssl_cert_reqs"] = "none"
        kwargs["ssl_check_hostname"] = False
    if username:
        kwargs["username"] = username
    if password:
        kwargs["password"] = password

    return FalkorDB(**kwargs)


def knowledge():
    """Graph storing code, org chart, tickets, Slack messages, and decisions."""
    return client().select_graph(f"{PREFIX}_knowledge")


def memory(repo: str = None):
    """Graph storing episodic incidents and procedural runbooks per repository/tenant."""
    target_repo = repo or os.getenv("REPO_NAME", "acme_checkout")
    return client().select_graph(f"{PREFIX}_memory_{target_repo}")


def agent_state():
    """Graph storing agent findings, tasks, and coordination state."""
    return client().select_graph(f"{PREFIX}_agent_state")


def rows(result) -> list[dict]:
    """Convert a FalkorDB result set into a list of dicts keyed by RETURN aliases."""
    if not result or not hasattr(result, "header") or not hasattr(result, "result_set"):
        return []
    names = [h[1] if isinstance(h, (list, tuple)) else h for h in result.header]
    return [dict(zip(names, r)) for r in result.result_set]
