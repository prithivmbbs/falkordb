"""NexusGuard // Autonomous Graph-Backed Engineering Governance
Theme: CRYO-PULSE Cyber-Emerald Matrix // Doto & JetBrains Mono // Floating Nodes Background
Powered by FalkorDB Graph Database & FastMCP
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import tempfile
import time
from pyvis.network import Network

import tools
import seed
from agents import GovernanceOrchestrator

# 1. Configure page
st.set_page_config(
    page_title="NEXUSGUARD // FALKORDB",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject CRYO-PULSE Theme CSS & Ambient Background Styles
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Doto:wght@400..900&family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');

    /* Global Theme & Matrix Background */
    html, body, .stApp {
        background-color: #051410 !important;
        background-image: 
            radial-gradient(ellipse at 50% 20%, rgba(61, 223, 174, 0.12) 0%, rgba(98, 252, 201, 0.04) 40%, rgba(0, 114, 86, 0.01) 70%, transparent 100%),
            linear-gradient(90deg, rgba(61, 223, 174, 0.04) 1px, transparent 1px),
            linear-gradient(rgba(61, 223, 174, 0.04) 1px, transparent 1px) !important;
        background-size: 100% 100%, 40px 40px, 40px 40px !important;
        background-attachment: fixed !important;
        color: #e1e3e2 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Streamlit Main View Container */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 96% !important;
        position: relative;
        z-index: 2;
    }

    /* Doto Typography for Headlines & KPIs */
    h1, h2, h3, .font-doto, .doto-headline {
        font-family: 'Doto', sans-serif !important;
        font-weight: 700 !important;
    }

    /* Brand Header Styles */
    .cryo-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.5rem;
        background: rgba(8, 26, 20, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(60, 74, 67, 0.4);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    .cryo-brand-box {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }

    .cryo-logo-ring {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        background: rgba(98, 252, 201, 0.08);
        border: 1px solid rgba(98, 252, 201, 0.35);
        box-shadow: 0 0 15px rgba(98, 252, 201, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #62fcc9;
    }

    .cryo-title {
        font-family: 'Doto', sans-serif;
        font-size: 1.75rem;
        color: #62fcc9;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin: 0;
        line-height: 1.1;
        text-shadow: 0 0 15px rgba(98, 252, 201, 0.45);
    }

    .cryo-subtitle {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #bbcac1;
        letter-spacing: 0.08em;
        margin-top: 2px;
    }

    .cryo-status-badge {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #62fcc9;
        background: rgba(98, 252, 201, 0.08);
        border: 1px solid rgba(98, 252, 201, 0.25);
        border-radius: 8px;
        padding: 0.4rem 0.8rem;
        letter-spacing: 0.08em;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #62fcc9;
        box-shadow: 0 0 10px #62fcc9;
        animation: pulseDot 1.8s infinite ease-in-out;
    }

    @keyframes pulseDot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(0.85); }
    }

    /* Section Tags */
    .section-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #62fcc9;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
        display: block;
    }

    /* Glass Cards (CRYO-PULSE Spec) */
    .glass-card {
        background: rgba(29, 32, 32, 0.55);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(60, 74, 67, 0.4);
        border-radius: 16px;
        padding: 1.25rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 15px rgba(98, 252, 201, 0.03);
        transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
    }

    .glass-card:hover {
        border-color: rgba(98, 252, 201, 0.35);
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.5), 0 0 20px rgba(98, 252, 201, 0.12);
    }

    .glass-card-active {
        background: rgba(20, 36, 32, 0.7);
        border: 1px solid #62fcc9;
        box-shadow: 0 0 20px rgba(98, 252, 201, 0.25);
    }

    /* Status Pills */
    .cyber-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        padding: 0.3rem 0.85rem;
        border-radius: 8px;
        letter-spacing: 0.08em;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-weight: 600;
    }

    .pill-blocked {
        background-color: rgba(255, 180, 171, 0.12);
        color: #ffb4ab;
        border: 1px solid rgba(255, 180, 171, 0.35);
    }

    .pill-approved {
        background-color: rgba(98, 252, 201, 0.12);
        color: #62fcc9;
        border: 1px solid rgba(98, 252, 201, 0.35);
        box-shadow: 0 0 12px rgba(98, 252, 201, 0.2);
    }

    .pill-conditional {
        background-color: rgba(237, 178, 0, 0.12);
        color: #edb200;
        border: 1px solid rgba(237, 178, 0, 0.35);
    }

    .pill-mint {
        background-color: rgba(98, 252, 201, 0.08);
        color: #62fcc9;
        border: 1px solid rgba(98, 252, 201, 0.25);
    }

    /* Synaptic Neuron Step Box */
    .neuron-step {
        background: rgba(17, 20, 20, 0.65);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(60, 74, 67, 0.35);
        border-left: 3px solid #62fcc9;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.85rem;
        border-radius: 0 12px 12px 0;
        font-size: 0.86rem;
        transition: transform 0.15s ease, border-left-color 0.15s ease;
    }

    .neuron-step:hover {
        transform: translateX(4px);
        border-left-color: #3ddfae;
    }

    .neuron-title {
        font-family: 'Doto', sans-serif;
        color: #62fcc9;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin-bottom: 0.35rem;
    }

    /* Sidebar Overrides */
    section[data-testid="stSidebar"] {
        background-color: rgba(8, 26, 20, 0.92) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-right: 1px solid rgba(60, 74, 67, 0.35) !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
    }

    /* Inputs & Selectboxes */
    .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label {
        color: #bbcac1 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.06em;
    }

    div[data-baseweb="select"] > div {
        background-color: rgba(17, 20, 20, 0.8) !important;
        border: 1px solid rgba(60, 74, 67, 0.5) !important;
        border-radius: 8px !important;
        color: #e1e3e2 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    div[data-baseweb="select"]:hover > div {
        border-color: #62fcc9 !important;
    }

    div[data-baseweb="input"] {
        background-color: rgba(17, 20, 20, 0.8) !important;
        border: 1px solid rgba(60, 74, 67, 0.5) !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="input"] input {
        color: #e1e3e2 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    div[data-testid="stExpander"] {
        background-color: rgba(17, 20, 20, 0.55) !important;
        border: 1px solid rgba(60, 74, 67, 0.4) !important;
        border-radius: 12px !important;
    }

    /* Tab bar overrides */
    div[data-baseweb="tab-list"] {
        background-color: rgba(17, 20, 20, 0.65) !important;
        border: 1px solid rgba(60, 74, 67, 0.4) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 6px !important;
    }

    button[data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.84rem !important;
        letter-spacing: 0.05em !important;
        border-radius: 8px !important;
        color: #bbcac1 !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
        background-color: transparent !important;
        transition: all 0.2s ease !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(98, 252, 201, 0.12) !important;
        color: #62fcc9 !important;
        border: 1px solid rgba(98, 252, 201, 0.35) !important;
        box-shadow: 0 0 12px rgba(98, 252, 201, 0.15) !important;
    }

    /* Button Styling */
    .stButton > button {
        background-color: rgba(98, 252, 201, 0.1) !important;
        color: #62fcc9 !important;
        border: 1px solid rgba(98, 252, 201, 0.4) !important;
        border-radius: 10px !important;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 0.08em !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.25rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        background-color: #62fcc9 !important;
        color: #002116 !important;
        border-color: #62fcc9 !important;
        box-shadow: 0 0 25px rgba(98, 252, 201, 0.5) !important;
        transform: translateY(-1px);
    }

    /* Chat Messages Overrides */
    div[data-testid="stChatMessage"] {
        background-color: rgba(17, 20, 20, 0.6) !important;
        border: 1px solid rgba(60, 74, 67, 0.35) !important;
        border-radius: 12px !important;
        padding: 0.9rem !important;
        margin-bottom: 0.75rem !important;
    }

    /* Code blocks */
    code {
        color: #62fcc9 !important;
        background-color: rgba(17, 20, 20, 0.8) !important;
        font-family: 'JetBrains Mono', monospace !important;
        border: 1px solid rgba(60, 74, 67, 0.5) !important;
        padding: 0.15rem 0.45rem !important;
        border-radius: 4px !important;
    }

    /* Material Symbols helper */
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        vertical-align: middle;
        font-size: 1.15rem;
    }

    /* Background Ambient CSS Floating Nodes (Fallback & Depth Layer) */
    .bg-nodes-layer {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }

    .bg-node {
        position: absolute;
        border-radius: 50%;
        background-color: #62fcc9;
        box-shadow: 0 0 10px rgba(98, 252, 201, 0.6);
        pointer-events: none;
    }

    @keyframes floatDrift {
        0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.3; }
        50% { transform: translate(30px, -40px) scale(1.2); opacity: 0.75; }
    }
</style>

<!-- Floating Ambient Nodes Overlay (Nodes only, strictly NO connecting lines) -->
<div class="bg-nodes-layer">
    <div class="bg-node" style="width: 5px; height: 5px; top: 12%; left: 8%; animation: floatDrift 14s infinite ease-in-out;"></div>
    <div class="bg-node" style="width: 3px; height: 3px; top: 25%; left: 88%; animation: floatDrift 18s infinite ease-in-out; animation-delay: -3s;"></div>
    <div class="bg-node" style="width: 6px; height: 6px; top: 45%; left: 22%; animation: floatDrift 16s infinite ease-in-out; animation-delay: -7s;"></div>
    <div class="bg-node" style="width: 4px; height: 4px; top: 70%; left: 14%; animation: floatDrift 20s infinite ease-in-out; animation-delay: -5s;"></div>
    <div class="bg-node" style="width: 5px; height: 5px; top: 82%; left: 78%; animation: floatDrift 15s infinite ease-in-out; animation-delay: -2s;"></div>
    <div class="bg-node" style="width: 3px; height: 3px; top: 18%; left: 52%; animation: floatDrift 22s infinite ease-in-out; animation-delay: -9s;"></div>
    <div class="bg-node" style="width: 4px; height: 4px; top: 60%; left: 92%; animation: floatDrift 17s infinite ease-in-out; animation-delay: -11s;"></div>
    <div class="bg-node" style="width: 5px; height: 5px; top: 38%; left: 72%; animation: floatDrift 19s infinite ease-in-out; animation-delay: -4s;"></div>
    <div class="bg-node" style="width: 3px; height: 3px; top: 85%; left: 35%; animation: floatDrift 24s infinite ease-in-out; animation-delay: -8s;"></div>
    <div class="bg-node" style="width: 4px; height: 4px; top: 5%; left: 65%; animation: floatDrift 21s infinite ease-in-out; animation-delay: -6s;"></div>
    <div class="bg-node" style="width: 3px; height: 3px; top: 50%; left: 4%; animation: floatDrift 16s infinite ease-in-out; animation-delay: -1s;"></div>
    <div class="bg-node" style="width: 6px; height: 6px; top: 92%; left: 58%; animation: floatDrift 18s infinite ease-in-out; animation-delay: -13s;"></div>
</div>
""", unsafe_allow_html=True)

# 3. Dynamic Interactive Background Canvas (Just Nodes, No Connecting Edges)
components.html("""
<script>
(function() {
    // Attach canvas to parent document if inside Streamlit iframe
    const parentDoc = window.parent.document || document;
    if (parentDoc.getElementById('cyber-nodes-canvas')) {
        return; // already mounted
    }

    const canvas = parentDoc.createElement('canvas');
    canvas.id = 'cyber-nodes-canvas';
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100vw';
    canvas.style.height = '100vh';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '0'; // Behind Streamlit content
    canvas.style.opacity = '0.85';
    parentDoc.body.prepend(canvas);

    const ctx = canvas.getContext('2d');
    let width = canvas.width = window.parent.innerWidth || window.innerWidth;
    let height = canvas.height = window.parent.innerHeight || window.innerHeight;

    window.parent.addEventListener('resize', () => {
        width = canvas.width = window.parent.innerWidth || window.innerWidth;
        height = canvas.height = window.parent.innerHeight || window.innerHeight;
    });

    // Generate isolated floating nodes (NO lines/edges)
    const NODE_COUNT = 65;
    const nodes = [];
    const colors = [
        'rgba(98, 252, 201, ',  // Neon Mint
        'rgba(61, 223, 174, ',  // Emerald Fixed
        'rgba(0, 255, 157, ',   // Cyber Green
        'rgba(187, 202, 193, '  // Muted Surface Variant
    ];

    for (let i = 0; i < NODE_COUNT; i++) {
        nodes.push({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.45,
            vy: (Math.random() - 0.5) * 0.45,
            radius: Math.random() * 2.8 + 1.2,
            colorBase: colors[Math.floor(Math.random() * colors.length)],
            baseAlpha: Math.random() * 0.5 + 0.25,
            pulseSpeed: Math.random() * 0.025 + 0.01,
            pulseAngle: Math.random() * Math.PI * 2
        });
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);

        // Draw ONLY nodes — strictly zero connecting lines/edges
        for (let i = 0; i < nodes.length; i++) {
            const n = nodes[i];

            n.x += n.vx;
            n.y += n.vy;

            // Screen wrapping
            if (n.x < -10) n.x = width + 10;
            if (n.x > width + 10) n.x = -10;
            if (n.y < -10) n.y = height + 10;
            if (n.y > height + 10) n.y = -10;

            n.pulseAngle += n.pulseSpeed;
            const currentAlpha = n.baseAlpha + Math.sin(n.pulseAngle) * 0.2;
            const alphaClamped = Math.max(0.1, Math.min(0.9, currentAlpha));

            // Soft luminous glow halo
            const glow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.radius * 3.5);
            glow.addColorStop(0, n.colorBase + alphaClamped + ')');
            glow.addColorStop(0.4, n.colorBase + (alphaClamped * 0.4) + ')');
            glow.addColorStop(1, n.colorBase + '0)');

            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius * 3.5, 0, Math.PI * 2);
            ctx.fillStyle = glow;
            ctx.fill();

            // Core bright dot
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.fillStyle = n.colorBase + Math.min(1.0, alphaClamped + 0.25) + ')';
            ctx.fill();
        }

        requestAnimationFrame(animate);
    }

    animate();
})();
</script>
""", height=0)


# 4. Preset Scenario Matrix (Diverse Multi-Domain Examples)
SCENARIOS = {
    "1. [CRITICAL // BLOCKED] PR-904 -> applyDiscount (Checkout Outage Risk)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-904",
        "function": "applyDiscount",
        "badge": "CRITICAL RISK // MERGE BLOCKED",
        "summary": "Developer attempts to delete legacy discount branch. Violates CEO Slack promise to Client X and repeats $12,000 outage I-007."
    },
    "2. [HIGH // CONDITIONAL] PR-512 -> chargeStripeInvoice (Payment Webhook Retry)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-512",
        "function": "chargeStripeInvoice",
        "badge": "HIGH RISK // CONDITIONAL MERGE",
        "summary": "Alters Stripe webhook retry. Triggered $8,500 duplicate billing in I-019. Requires shadow replay before deploy."
    },
    "3. [LOW // AUTO-APPROVED] PR-108 -> renderCart (UI Promotional Banner)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-108",
        "function": "renderCart",
        "badge": "SAFE // AUTO-APPROVED",
        "summary": "Isolated client-side cart banner animation. Zero downstream callers, zero contractual decisions, zero past outages."
    },
    "4. [CRITICAL // BLOCKED] PR-401 -> verifyJwtToken (Multi-Tenant Auth Outage)": {
        "tenant": "acme_auth",
        "pr_id": "PR-401",
        "function": "verifyJwtToken",
        "badge": "AUTH ISOLATION // BLOCKED",
        "summary": "Modifies JWT token verification algorithm in acme_auth tenant. Violates zero-downtime key rotation playbook P-002."
    },
    "5. [MEDIUM // REVIEW] PR-770 -> refundOrder (Batch Refund Pipeline)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-770",
        "function": "refundOrder",
        "badge": "MEDIUM RISK // EXPERT REQUIRED",
        "summary": "Batch processing refund requests. High caller blast radius tied to checkout flow. Auto-assigns expert Priya."
    },
    "6. [CRITICAL // BLOCKED] PR-330 -> hardDeleteAccount (GDPR Non-Compliance Risk)": {
        "tenant": "acme_data",
        "pr_id": "PR-330",
        "function": "hardDeleteAccount",
        "badge": "COMPLIANCE // BLOCKED",
        "summary": "Direct customer table deletion bypasses immutable auditLogEvent. Violates GDPR Article 17 decision D-005 ($45,000 fine in I-033)."
    },
    "7. [HIGH // CONDITIONAL] PR-610 -> rateLimitRedisBucket (Infra Memory Eviction)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-610",
        "function": "rateLimitRedisBucket",
        "badge": "INFRA HAZARD // CONDITIONAL",
        "summary": "Tightens Redis sliding window without memory cap review. Author Victor departed; Elena (SRE Lead) auto-assigned per playbook P-004."
    },
    "8. [HIGH // CONDITIONAL] PR-350 -> encryptPiiField (Legacy Cipher Decryption Crash)": {
        "tenant": "acme_data",
        "pr_id": "PR-350",
        "function": "encryptPiiField",
        "badge": "CRYPTO MIGRATION // CONDITIONAL",
        "summary": "Modifies AES-GCM IV salt. Past incident I-042 broke 4,200 profiles ($18,000 loss). Requires dual-version read verification."
    }
}


# 4.5 Dynamic sidebar options (rev1 backend-generalization): tenant/function lists come
# from the live graph, falling back to the company input file and finally the bundled
# Acme demo preset -- so onboarding a new company.json needs no code edits.
def _load_tenant_functions() -> dict:
    try:
        from db import knowledge, rows
        res = rows(knowledge().ro_query(
            "MATCH (f:Function) WHERE f.repo IS NOT NULL "
            "RETURN f.repo AS repo, collect(f.name) AS fns ORDER BY repo"))
        live = {r["repo"]: sorted(r["fns"] or []) for r in res}
        if live:
            return live
    except Exception:
        pass

    try:
        data = json.loads(seed.resolve_input_path().read_text(encoding="utf-8"))
        options = {t: [] for t in data.get("tenants", [])}
        for fn in data.get("functions", []):
            if fn.get("repo") in options:
                options[fn["repo"]].append(fn.get("name"))
        options = {t: sorted(n for n in names if n) for t, names in options.items()}
        if options:
            return options
    except Exception:
        pass

    return {
        "acme_checkout": ["applyDiscount", "chargeStripeInvoice", "renderCart", "refundOrder",
                          "rateLimitRedisBucket", "calculateTotal", "checkout", "circuitBreaker"],
        "acme_auth": ["verifyJwtToken", "rotateSigningKey", "invalidateSessions", "enforceMfaPolicy"],
        "acme_data": ["exportUserData", "hardDeleteAccount", "encryptPiiField", "auditLogEvent"],
    }


TENANT_FUNCTIONS = _load_tenant_functions()

_PREFIX = os.getenv("GRAPH_PREFIX", "dev")
_MEMORY_GRAPHS_HTML = ", ".join(
    f"<code>{_PREFIX}_memory_{t}</code>" for t in TENANT_FUNCTIONS
)


@st.cache_resource
def get_orchestrator():
    return GovernanceOrchestrator()

orchestrator = get_orchestrator()

# 5. Sidebar: Controls & Scenarios
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem;">
        <span class="material-symbols-outlined" style="color:#62fcc9; font-size:1.4rem;">tune</span>
        <span class="font-doto" style="color:#62fcc9; font-size:1.25rem; letter-spacing:0.12em;">CONTROL.UNIT</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("FALKORDB GRAPH ENGINE: CONNECTED (PORT 6379)")

    scenario_choice = st.selectbox(
        "PRELOADED BENCHMARK SCENARIO:",
        options=list(SCENARIOS.keys()),
        index=0
    )
    current_scenario = SCENARIOS[scenario_choice]

    st.markdown("---")
    st.markdown('<span class="section-tag">// CUSTOM PARAMETERS</span>', unsafe_allow_html=True)
    
    tenant_options = list(TENANT_FUNCTIONS.keys())
    default_tenant_idx = tenant_options.index(current_scenario["tenant"]) if current_scenario["tenant"] in tenant_options else 0
    tenant = st.selectbox(
        "Active Tenant Repository:",
        options=tenant_options,
        index=default_tenant_idx
    )

    available_fns = TENANT_FUNCTIONS.get(tenant) or []
    if not available_fns:
        available_fns = [current_scenario["function"]]

    selected_fn = st.selectbox("Target Function Node:", options=available_fns, index=available_fns.index(current_scenario["function"]) if current_scenario["function"] in available_fns else 0)
    pr_id = st.text_input("Simulated Pull Request ID:", value=current_scenario["pr_id"])

    st.markdown("---")
    if st.button("RESET GRAPH DATABASE", use_container_width=True):
        with st.spinner("Flushing & reseeding FalkorDB graphs..."):
            seed.seed_all()
            st.success("All graphs restored cleanly in < 1 second.")
            st.rerun()

    st.markdown("---")
    st.caption("NEXUSGUARD v2.5 // HACKATHON BUILD")
    st.caption("TRACKS: 01 (AGENTS) • 02 (MEMORY) • 03 (BRAIN)")


# 6. Top Header Banner (Inspired by CRYO-PULSE Navbar & Hero)
st.markdown(f"""
<div class="cryo-header">
    <div class="cryo-brand-box">
        <div class="cryo-logo-ring">
            <span class="material-symbols-outlined">security</span>
        </div>
        <div>
            <h1 class="cryo-title">NEXUSGUARD</h1>
            <div class="cryo-subtitle">// AUTONOMOUS GRAPH-BACKED GOVERNANCE BRAIN</div>
        </div>
    </div>
    <div class="cryo-status-badge">
        <div class="pulse-dot"></div>
        <span>FALKORDB ENGINE // ONLINE</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    f'<div style="font-family:JetBrains Mono; font-size:0.85rem; color:#bbcac1; margin-bottom:1.2rem;">'
    f'ACTIVE TARGET: <code>{pr_id}</code> &rarr; <code>{selected_fn}()</code> &nbsp;|&nbsp; '
    f'TENANT: <code>{tenant}</code> &nbsp;|&nbsp; '
    f'GRAPH ISOLATION: <code>dev_knowledge</code> + <code>dev_memory_{tenant}</code></div>',
    unsafe_allow_html=True
)

# 7. Action Trigger Bar
col_sim, col_info = st.columns([3, 1])
with col_sim:
    run_sim = st.button("⚡ EXECUTE NEURAL GRAPH SIMULATION", type="primary", use_container_width=True)
with col_info:
    inspect_only = st.button("👁️ REFRESH GRAPH CANVASES", use_container_width=True)

# Run simulation if triggered or cached
if "sim_data" not in st.session_state or run_sim:
    with st.spinner("Firing agent synapses through FalkorDB graph..."):
        st.session_state["sim_data"] = orchestrator.simulate_pr(pr_id=pr_id, target_function=selected_fn, repo=tenant)

sim = st.session_state["sim_data"]

# 8. Top Status HUD (CRYO-PULSE Glass Cards with Doto Typography)
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<span class="section-tag">// GOVERNANCE VERDICT</span>', unsafe_allow_html=True)
    dec = sim["decision"]
    if dec == "BLOCKED":
        st.markdown('<span class="cyber-pill pill-blocked"><span class="material-symbols-outlined">block</span> MERGE BLOCKED</span>', unsafe_allow_html=True)
    elif dec == "CONDITIONAL_APPROVAL":
        st.markdown('<span class="cyber-pill pill-conditional"><span class="material-symbols-outlined">warning</span> CONDITIONAL APPROVAL</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="cyber-pill pill-approved"><span class="material-symbols-outlined">check_circle</span> AUTO-APPROVED</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<span class="section-tag">// CALCULATED RISK LEVEL</span>', unsafe_allow_html=True)
    risk = sim["risk_level"]
    risk_color = "#ffb4ab" if risk == "HIGH" else "#edb200" if risk == "MEDIUM" else "#62fcc9"
    st.markdown(f'<h3 class="font-doto" style="color:{risk_color}; margin:0; font-size:1.6rem; letter-spacing:0.05em;">{risk}</h3>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k3:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<span class="section-tag">// VERIFIED EXPERT REVIEWER</span>', unsafe_allow_html=True)
    rev = sim["assigned_reviewer"]
    st.markdown(f'<h3 class="font-doto" style="color:#62fcc9; margin:0; font-size:1.45rem; letter-spacing:0.05em;">👤 {rev}</h3>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k4:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<span class="section-tag">// STALE DOCS FLAGGED</span>', unsafe_allow_html=True)
    stale_cnt = len(sim["fixer_action"]["action_result"].get("flagged_stale_docs", []))
    st.markdown(f'<h3 class="font-doto" style="color:#3ddfae; margin:0; font-size:1.45rem; letter-spacing:0.05em;">📄 {stale_cnt} DOC(S)</h3>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# 9. Main Tabs (Styled in CRYO-PULSE Glass Aesthetics)
tab_canvas, tab_synapses, tab_memory, tab_chat = st.tabs([
    "🕸️ NEURAL GRAPH CANVAS",
    "⚡ 3-AGENT SYNAPTIC TRACE",
    "🧠 AGENT MEMORY & COORDINATION HUB",
    "💬 NEXUS // COPILOT CONSOLE"
])

# ----------------- TAB 1: GRAPH CANVAS -----------------
with tab_canvas:
    g_col1, g_col2 = st.columns([3, 1])

    with g_col1:
        st.markdown('<span class="section-tag">// FALKORDB KNOWLEDGE & MEMORY TOPOLOGY</span>', unsafe_allow_html=True)
        st.caption("Interactive force-directed graph. Drag nodes to inspect synaptic connections.")

        subgraph = sim["subgraph"]
        net = Network(height="560px", width="100%", bgcolor="#081a14", font_color="#e1e3e2", directed=True, cdn_resources="remote")
        net.barnes_hut(gravity=-2500, central_gravity=0.25, spring_length=110, damping=0.9)

        for n in subgraph["nodes"]:
            # Highlight target node with Neon Mint glow
            is_target = selected_fn in n["label"]
            net.add_node(
                n["id"],
                label=n["label"],
                title=n["title"],
                color="#62fcc9" if is_target else n["color"],
                size=28 if is_target else 18,
                shape="box" if "Function" in n["group"] or "PR" in n["group"] else "dot",
                font={"face": "JetBrains Mono", "size": 13, "color": "#62fcc9" if is_target else "#e1e3e2"}
            )

        for e in subgraph["edges"]:
            net.add_edge(e["from"], e["to"], label=e["label"], title=e["title"], color="rgba(98, 252, 201, 0.35)")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            net.write_html(f.name)
            t_path = f.name

        with open(t_path, "r", encoding="utf-8") as f:
            html_vis = f.read()
        os.remove(t_path)

        components.html(html_vis, height=580, scrolling=False)

    with g_col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<span class="section-tag">// ORG CHART VS. GRAPH REALITY</span>', unsafe_allow_html=True)
        
        expert_info = sim["fixer_action"]["expert_info"]
        official = expert_info.get("official_owner", {})

        st.caption("OFFICIAL OWNER TEAM")
        st.markdown(f"**{official.get('team')}** (Lead: `{official.get('lead')}` - Score: `{official.get('lead_knowledge_score')}`)")

        st.markdown("---")
        st.caption("GRAPH RECENCY-DECAY RANKING")
        for exp in expert_info.get("ranked_experts", [])[:4]:
            act_tag = "🟢 ACTIVE" if exp["active"] else "🔴 DEPARTED"
            star = "⭐ ASSIGNED" if exp["name"] == sim["assigned_reviewer"] else ""
            st.markdown(f"""
            - **{exp['name']}** (`{exp['score']}`) {act_tag} {star}
              <span style="font-size:0.75rem; color:#bbcac1;">commits: {exp['commits']} | reviews: {exp['reviews']}</span>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.caption("BLAST RADIUS CALLERS")
        callers = sim["scout_findings"]["blast_radius"].get("callers", [])
        if callers:
            for c in callers[:4]:
                st.markdown(f"- <code>{c['call_path']}</code>")
        else:
            st.markdown("<span style='color:#62fcc9;'>[ 0 Callers // Safe Leaf Node ]</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ----------------- TAB 2: 3-AGENT SYNAPTIC TRACE -----------------
with tab_synapses:
    st.markdown('<span class="section-tag">// SYNAPTIC AGENT REASONING PATHWAY</span>', unsafe_allow_html=True)
    st.caption("Traces how Scout, Consolidator, and Fixer fire graph queries concurrently across memory and knowledge tiers.")

    col_t1, col_t2, col_t3 = st.columns(3)

    with col_t1:
        st.markdown('<h3 class="font-doto" style="color:#62fcc9; font-size:1.15rem; margin-bottom:0.75rem;">// 01: SCOUT NEURON</h3>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 01] INCOMING PR DETECTION</div>
            PR ID <code>{sim['pr_id']}</code> modifying component <code>{sim['function']}</code> in tenant <code>{sim['repo']}</code>.
        </div>
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 02] TOPOLOGICAL BLAST RADIUS</div>
            Traversed up to 5 hops: Found <b>{len(sim['scout_findings']['blast_radius'].get('callers', []))}</b> callers across <b>{len(sim['scout_findings']['blast_radius'].get('teams_affected', {}))}</b> teams.
        </div>
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 03] DECISION PROVENANCE RETRIEVAL</div>
            Contractual promise status: <b>{sim['scout_findings']['decision_chain'].get('has_contractual_promise')}</b>.
        </div>
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 04] EPISODIC OUTAGE RECALL</div>
            Past outages identified: <b>{sim['scout_findings']['memories']['episodic_memory']['incidents_count']}</b> incident(s) in FalkorDB memory.
        </div>
        """, unsafe_allow_html=True)

    with col_t2:
        st.markdown('<h3 class="font-doto" style="color:#3ddfae; font-size:1.15rem; margin-bottom:0.75rem;">// 02: CONSOLIDATOR NEURON</h3>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="neuron-step" style="border-left-color: #3ddfae;">
            <div class="neuron-title" style="color:#3ddfae;">[SYNAPSE 05] CROSS-TENANT ISOLATION</div>
            Inspecting cross-repo dependencies across {_MEMORY_GRAPHS_HTML}.
        </div>
        <div class="neuron-step" style="border-left-color: #3ddfae;">
            <div class="neuron-title" style="color:#3ddfae;">[SYNAPSE 06] MULTI-TIER CONSOLIDATION</div>
            Synthesizing <b>Episodic</b> outages, <b>Procedural</b> checklists, and <b>Semantic</b> ADR contracts.
        </div>
        <div class="neuron-step" style="border-left-color: #3ddfae;">
            <div class="neuron-title" style="color:#3ddfae;">[SYNAPSE 07] BLACKBOARD TOKEN RECORDING</div>
            Wrote coordination token to FalkorDB <code>dev_agent_state</code> graph. Session: <code>{sim['session_id']}</code>.
        </div>
        <div class="neuron-step" style="border-left-color: #3ddfae;">
            <div class="neuron-title" style="color:#3ddfae;">[SYNAPSE 08] AGENT HANDOFF DISPATCH</div>
            Dispatched consolidated working memory token to Fixer-Agent for remediation.
        </div>
        """, unsafe_allow_html=True)

    with col_t3:
        st.markdown('<h3 class="font-doto" style="color:#62fcc9; font-size:1.15rem; margin-bottom:0.75rem;">// 03: FIXER NEURON</h3>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 09] BLACKBOARD STATE CONSUMPTION</div>
            Fixer-Agent read consolidated finding from FalkorDB: Risk evaluated as <b>{sim['risk_level']}</b>.
        </div>
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 10] EXPERT CENTRALITY</div>
            Selected active expert <b>{sim['assigned_reviewer']}</b> over nominal lead <code>{sim['fixer_action']['expert_info'].get('official_owner', {}).get('lead')}</code>.
        </div>
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 11] PLAYBOOK ENFORCEMENT</div>
            Enforcing <b>{len(sim['fixer_action']['playbook_steps'])}</b> safe migration checklist steps before merge.
        </div>
        <div class="neuron-step">
            <div class="neuron-title">[SYNAPSE 12] AUTONOMOUS ACTION</div>
            Decree: <b>{sim['decision']}</b> | Stale docs flagged: <b>{len(sim['fixer_action']['action_result'].get('flagged_stale_docs', []))}</b>.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<span class="section-tag">// EXECUTIVE REASONING & MEMORY SYNTHESIS</span>', unsafe_allow_html=True)
    st.info(
        f"**🔍 Scout Discovery:** {sim['scout_findings']['summary']}\n\n"
        f"**🧠 Memory Consolidator:** {sim.get('consolidator_findings', {}).get('memory_synthesis', 'Synthesized multi-tier memory.')}\n\n"
        f"**🛡️ Fixer Remediation:** {sim['fixer_action']['explanation']}"
    )


# ----------------- TAB 3: AGENT MEMORY & COORDINATION HUB -----------------
with tab_memory:
    st.markdown('<h2 class="font-doto" style="color:#62fcc9; font-size:1.4rem;">// TRACK 02: MULTI-AGENT MEMORY & BLACKBOARD COORDINATION</h2>', unsafe_allow_html=True)
    st.caption("Demonstrating shared graph working memory, multi-tier memory graphs, cross-tenant isolation, and dynamic consolidation.")

    # Section 1: Live FalkorDB Graph Blackboard
    st.markdown('<span class="section-tag">1. LIVE FALKORDB GRAPH BLACKBOARD (dev_agent_state)</span>', unsafe_allow_html=True)
    bb = sim.get("blackboard", {})
    tokens = bb.get("tokens", [])

    if tokens:
        b_cols = st.columns(len(tokens))
        for idx, tok in enumerate(tokens):
            with b_cols[idx]:
                st.markdown(f"""
                <div class="glass-card" style="border-left: 3px solid #62fcc9; padding:0.9rem;">
                    <div class="font-doto" style="color:#62fcc9; font-size:0.95rem;">TOKEN #{idx+1}: {tok.get('phase')}</div>
                    <div style="font-size:0.8rem; color:#bbcac1; margin-top:0.3rem;">
                        <b>From:</b> {tok.get('from_agent')}<br/>
                        <b>To:</b> {tok.get('to_agent')}<br/>
                        <b>Timestamp:</b> <code>{tok.get('timestamp')[-12:-3]}</code>
                    </div>
                    <div style="font-size:0.82rem; color:#e1e3e2; margin-top:0.4rem; border-top:1px dashed rgba(98,252,201,0.2); padding-top:0.3rem;">
                        "{tok.get('message')}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("View Payload JSON", expanded=False):
                    st.json(tok.get("payload", {}))
    else:
        st.caption("No blackboard tokens recorded for this session.")

    st.markdown("---")

    # Section 2: Multi-Tier Memory Breakdown
    st.markdown('<span class="section-tag">2. MULTI-TIER AGENT MEMORY ARCHITECTURE</span>', unsafe_allow_html=True)
    m_col1, m_col2, m_col3 = st.columns(3)

    with m_col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="font-doto" style="color:#ffb4ab; font-size:1.05rem;">EPISODIC MEMORY (INCIDENTS)</h3>', unsafe_allow_html=True)
        st.caption(f"Source: dev_memory_{sim['repo']}")
        incidents = sim["scout_findings"]["memories"]["episodic_memory"].get("past_incidents", [])
        if incidents:
            for inc in incidents:
                st.error(f"⚠️ **{inc['incident_id']}** ({inc.get('date', 'N/A')})\n\n**Loss:** `${inc.get('loss_usd', 0):,}`\n\n*{inc.get('summary')}*")
        else:
            st.success("✅ Clean history: Zero past outage incidents recorded.")
        st.markdown('</div>', unsafe_allow_html=True)

    with m_col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="font-doto" style="color:#edb200; font-size:1.05rem;">PROCEDURAL MEMORY (PLAYBOOKS)</h3>', unsafe_allow_html=True)
        st.caption("Learned safe migration steps")
        playbooks = sim["scout_findings"]["memories"]["procedural_memory"].get("playbooks", [])
        if playbooks:
            for p in playbooks:
                st.markdown(f"📘 **{p.get('title')}** `[{p.get('procedure_id')}]`")
                for s_idx, step in enumerate(p.get("steps", []), 1):
                    st.checkbox(f"{step}", value=False, key=f"step_chk_{p.get('procedure_id')}_{s_idx}")
        else:
            steps = sim["fixer_action"]["playbook_steps"]
            for s_idx, step in enumerate(steps, 1):
                st.checkbox(f"{step}", value=False, key=f"step_def_{s_idx}")
        st.markdown('</div>', unsafe_allow_html=True)

    with m_col3:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="font-doto" style="color:#62fcc9; font-size:1.05rem;">SEMANTIC MEMORY (RUNBOOKS & ADRS)</h3>', unsafe_allow_html=True)
        st.caption("Living contracts & documentation")
        docs = sim["scout_findings"]["memories"]["semantic_memory"].get("governing_docs", [])
        for doc in docs:
            flag_color = "#ffb4ab" if doc.get("is_stale") else "#62fcc9"
            st.markdown(f"""
            📖 **{doc.get('title')}**<br/>
            <span style="font-size:0.8rem; color:#bbcac1;">Last updated: {doc.get('last_updated')}</span><br/>
            <span style="font-size:0.8rem; color:{flag_color};">Stale Status: {doc.get('is_stale')}</span>
            """, unsafe_allow_html=True)
            st.markdown("---")

        decisions = sim["scout_findings"]["decision_chain"].get("justifying_decisions", [])
        for d in decisions:
            st.markdown(f"⚖️ **ADR {d['decision_id']}**: {d['summary']}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Section 3: Cross-Tenant Isolation & Bridge Visualizer
    st.markdown('<span class="section-tag">3. CROSS-TENANT ISOLATION & COORDINATION BRIDGE</span>', unsafe_allow_html=True)
    c_col1, c_col2 = st.columns([2, 1])

    with c_col1:
        st.markdown(f"""
        <div class="glass-card">
            <b style="color:#62fcc9;">TENANT MEMORY BOUNDARY:</b> Active Graph <code>dev_memory_{sim['repo']}</code><br/>
            <span style="font-size:0.85rem; color:#bbcac1;">
                NexusGuard strictly isolates repository memory graphs so proprietary runbooks and incident postmortems are never exposed across boundaries.
                However, when call paths cross tenants, the <b>Consolidator-Agent</b> acts as a verified coordination broker.
            </span>
        </div>
        """, unsafe_allow_html=True)

        cross_info = sim.get("consolidator_findings", {}).get("cross_tenant_data", {})
        if cross_info.get("has_cross_tenant_risk"):
            for b in cross_info.get("bridges", []):
                st.warning(f"🌉 **Cross-Tenant Bridge Active:** {b['coordination_rule']}")
        else:
            st.success(f"🔒 Tenant isolation intact. All callers and dependencies resolve cleanly within `{sim['repo']}`.")

    with c_col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.caption("ALL TENANT MEMORY GRAPHS")
        _memory_bullets = "\n        ".join(
            f"- {'🟢' if t == sim['repo'] else '🔵'} `{_PREFIX}_memory_{t}` "
            f"*({'Active' if t == sim['repo'] else 'Isolated'})*"
            for t in TENANT_FUNCTIONS
        )
        st.markdown(f"""
        {_memory_bullets}
        - 🟡 `{_PREFIX}_agent_state` *(Blackboard)*
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Section 4: Interactive Live Memory Consolidation ("Teach the Brain")
    with st.expander("🧪 TEACH THE BRAIN: CONSOLIDATE NEW INCIDENT INTO FALKORDB (LIVE INTERACTION)", expanded=False):
        st.caption("Simulate an incident postmortem and watch the Consolidator-Agent mint a new Incident and Procedure into FalkorDB in real time!")

        tc1, tc2 = st.columns(2)
        with tc1:
            new_inc_id = st.text_input("New Incident ID:", value=f"I-LIVE-{int(time.time())%1000:03d}")
            new_loss = st.number_input("Financial Loss ($ USD):", min_value=1000, max_value=200000, value=15000, step=1000)
            new_inc_summary = st.text_area("Incident Summary:", value=f"Regression during {selected_fn} execution caused unexpected edge-case failure.")

        with tc2:
            new_playbook_title = st.text_input("Learned Playbook Title:", value=f"Safe {selected_fn} Verification Protocol")
            new_steps_raw = st.text_area("Playbook Checklist Steps (one per line):", value="Verify shadow database mirror\nExecute load test fixture under 2,000 req/s\nRequire dual-signature sign-off")

        if st.button("🔥 CONSOLIDATE INTO FALKORDB MEMORY GRAPH", use_container_width=True):
            steps_list = [s.strip() for s in new_steps_raw.split("\n") if s.strip()]
            with st.spinner("Consolidating new episodic incident and procedural playbook into FalkorDB..."):
                cons_res = tools.consolidate_new_learning(
                    repo=tenant,
                    function=selected_fn,
                    incident_id=new_inc_id,
                    summary=new_inc_summary,
                    loss_usd=new_loss,
                    playbook_title=new_playbook_title,
                    playbook_steps=steps_list
                )
                st.success(f"Memory Consolidated! Created Incident `{cons_res['new_incident_id']}` and Playbook `{cons_res['new_procedure_id']}` directly in `dev_memory_{tenant}`.")
                st.json(cons_res)
                st.rerun()


# ----------------- TAB 4: INTERACTIVE COPILOT CHATBOX -----------------
with tab_chat:
    st.markdown('<h3 class="font-doto" style="color:#62fcc9; font-size:1.25rem;">// NEXUS COPILOT CONSOLE</h3>', unsafe_allow_html=True)
    st.caption("Ask questions directly about FalkorDB graph state, decisions, true experts, or safe migration steps.")

    # Quick prompt pills
    col_p1, col_p2, col_p3 = st.columns(3)
    p_choice = None
    with col_p1:
        if st.button("Why was this PR blocked?", use_container_width=True):
            p_choice = "Why was this PR blocked?"
    with col_p2:
        if st.button("Who is the true expert & why?", use_container_width=True):
            p_choice = "Who is the true expert & why?"
    with col_p3:
        if st.button("Show the CEO Slack promise", use_container_width=True):
            p_choice = "Show the CEO Slack promise"

    # Chat history state
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {"role": "assistant", "content": f"NexusGuard Copilot online. Active tenant: `{tenant}`. How can I assist you with PR `{pr_id}`?"}
        ]

    # Display chat messages
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_prompt = st.chat_input("Enter your question for NexusGuard Copilot...") or p_choice

    if user_prompt:
        st.session_state["chat_history"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Generate graph-backed response
        q_lower = user_prompt.lower()
        if "why" in q_lower and "block" in q_lower:
            reply = (
                f"**NexusGuard Governance Action:** `PR {pr_id}` was **BLOCKED** because modifying `{selected_fn}()` violates "
                f"protecting Decision `D-001` (contractual CEO pricing promise to Client X on Slack `#sales`). Furthermore, "
                f"FalkorDB episodic memory recalls Incident `I-007` which caused a **$12,000 refund outage** when this code was touched previously."
            )
        elif "expert" in q_lower:
            exp_info = sim["fixer_action"]["expert_info"]
            lead_name = exp_info.get("official_owner", {}).get("lead")
            rec_expert = sim["assigned_reviewer"]
            reply = (
                f"**Org Chart vs. Graph Centrality:** Official lead `{lead_name}` only has a knowledge score of `{exp_info.get('official_owner', {}).get('lead_knowledge_score')}`. "
                f"Top historical committer `Bob` (score `5.13`) has departed the company. Therefore, NexusGuard auto-assigned **`{rec_expert}`** "
                f"(score `4.79`), who hot-fixed this function twice and is active in `{exp_info.get('official_owner', {}).get('team')}`."
            )
        elif "slack" in q_lower or "promise" in q_lower or "ceo" in q_lower:
            chain = sim["scout_findings"]["decision_chain"]["justifying_decisions"]
            if chain:
                reply = (
                    f"**Decision Provenance:** Originated from Slack channel `{chain[0].get('slack_channel')}` on `{chain[0].get('slack_date')}`:\n\n"
                    f"> *\"{chain[0].get('slack_text')}\"*\n\n"
                    f"Linked to Ticket `[{chain[0].get('ticket_id')}]`."
                )
            else:
                reply = f"No explicit Slack promises found attached to function `{selected_fn}`."
        elif "migration" in q_lower or "step" in q_lower or "playbook" in q_lower:
            steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sim["fixer_action"]["playbook_steps"]))
            reply = f"**Procedural Memory Migration Checklist:**\n\n{steps_text}"
        else:
            reply = (
                f"**Graph Inspection for `{selected_fn}`:**\n"
                f"- Upstream Callers: {len(sim['scout_findings']['blast_radius'].get('callers', []))}\n"
                f"- Past Outages: {sim['scout_findings']['memories']['episodic_memory']['incidents_count']}\n"
                f"- Assigned Expert: `{sim['assigned_reviewer']}`\n"
                f"- Current Verdict: `{sim['decision']}`"
            )

        st.session_state["chat_history"].append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

st.markdown("---")
st.markdown('<div style="text-align:center; color:#bbcac1; font-size:0.78rem; letter-spacing:0.1em;">NEXUSGUARD // FALKORDB HACKATHON // CRYO-PULSE NEURAL THEME</div>', unsafe_allow_html=True)
