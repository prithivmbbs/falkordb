"""NexusGuard — Autonomous Graph-Backed Engineering Governance
Design: Scholar's Parchment Design System
Colors: Parchment (#faf8f5), Soft Paper (#fdfbfa), Ink (#27251e), Graphite (#72706b),
        Warm Mist (#d1d1cd), Deep Teal (#016a71), Risk Red (#b83a2b), Risk Amber (#8a6100)
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import tempfile
import textwrap
from pyvis.network import Network

import tools
import agents
from agents import GovernanceOrchestrator
import seed

# ──────────────────────────────────────────────────────────────
# 1. Page Configuration
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NexusGuard — Engineering Governance",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────────────────────
# 2. Scholar's Parchment CSS  (UI_SPEC §1, §7)
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..24,400,0,0');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..24,400,0,0');

    /* ── Design Tokens (§1.1) ── */
    :root {
        --color-parchment: #faf8f5;
        --color-soft-paper: #fdfbfa;
        --color-warm-mist: #d1d1cd;
        --color-ash: #92918b;
        --color-graphite: #6e6c66;
        --color-ink: #1e1c16;
        --color-deep-teal: #016a71;
        --color-risk-red: #b83a2b;
        --color-risk-amber: #8a6100;
        --font-sans: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        --font-display: 'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

        /* ── Glassmorphic Design Tokens ── */
        --glass-bg: rgba(255, 255, 255, 0.22);
        --glass-bg-hover: rgba(255, 255, 255, 0.34);
        --glass-border: rgba(255, 255, 255, 0.85);
        --glass-blur: blur(3.5px);
        --glass-shadow: 0 4px 20px rgba(39, 37, 30, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.9);
        --glass-shadow-hover: 0 8px 30px rgba(39, 37, 30, 0.07), inset 0 1px 0 rgba(255, 255, 255, 0.95);
    }

    /* ── Streamlit Material Icons Fix ── */
    [data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
        font-weight: normal !important;
        font-style: normal !important;
        line-height: 1 !important;
        display: inline-block !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        word-wrap: normal !important;
        white-space: nowrap !important;
        direction: ltr !important;
        -webkit-font-smoothing: antialiased !important;
    }

    /* ── Hide Streamlit chrome without killing the sidebar toggle (§2) ── */
    #MainMenu,
    div[data-testid="stToolbarActions"],
    div[data-testid="stToolbarRightCorner"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"] {
        display: none !important;
        height: 0px !important;
        visibility: hidden !important;
    }
    footer { visibility: hidden !important; display: none !important; }

    /* Keep header transparent and zero height, but keep sidebar collapsed toggle clickable */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0px !important;
        min-height: 0px !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        overflow: visible !important;
        z-index: 99999 !important;
        pointer-events: none !important;
    }

    div[data-testid="stToolbar"],
    div[data-testid="stToolbar"] * {
        background: transparent !important;
        height: 0px !important;
        min-height: 0px !important;
        visibility: visible !important;
        overflow: visible !important;
        pointer-events: none !important;
    }

    /* Style the sidebar expand button when sidebar is collapsed — perfectly centered */
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        visibility: visible !important;
        pointer-events: auto !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 12px !important;
        left: 14px !important;
        width: 32px !important;
        height: 32px !important;
        z-index: 999999 !important;
        background-color: var(--color-soft-paper) !important;
        border: 1px solid var(--color-warm-mist) !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
        padding: 0 !important;
        margin: 0 !important;
        box-sizing: border-box !important;
        line-height: 1 !important;
        color: var(--color-ink) !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }
    button[data-testid="stExpandSidebarButton"]:hover,
    [data-testid="stSidebarCollapsedControl"]:hover {
        background-color: var(--color-parchment) !important;
        border-color: var(--color-deep-teal) !important;
    }
    button[data-testid="stExpandSidebarButton"] span,
    [data-testid="stSidebarCollapsedControl"] span {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        height: 100% !important;
        line-height: 1 !important;
        color: var(--color-ink) !important;
        font-size: 1.15rem !important;
    }

    /* ── Page Canvas ── */
    html, body {
        background-color: var(--color-parchment) !important;
        color: var(--color-ink) !important;
        font-family: var(--font-sans) !important;
        font-weight: 400 !important;
        -webkit-font-smoothing: antialiased;
    }
    .stApp {
        background-color: transparent !important;
        color: var(--color-ink) !important;
        font-family: var(--font-sans) !important;
        font-weight: 400 !important;
        -webkit-font-smoothing: antialiased;
    }

    /* ── Main Container — fluid, evenly spread, responsive layout ── */
    div[data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    .block-container,
    .main .block-container {
        width: 100% !important;
        max-width: 1400px !important;
        padding-top: 0.75rem !important;
        padding-bottom: 3rem !important;
        padding-left: clamp(1.5rem, 3.5vw, 3.5rem) !important;
        padding-right: clamp(1.5rem, 3.5vw, 3.5rem) !important;
        margin-left: auto !important;
        margin-right: auto !important;
        box-sizing: border-box !important;
        position: relative;
        z-index: 2;
        transition: max-width 0.2s ease, padding 0.2s ease !important;
    }

    /* Ambient background iframe only — do not hide PyVis components */
    div[data-testid="stCustomComponentV1"]:has(iframe[height="0"]),
    iframe[height="0"] {
        display: none !important;
        height: 0px !important;
        min-height: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
        position: absolute !important;
    }

    /* ── Typography (§1.2) ── */
    h1, h2, h3, h4 {
        color: var(--color-ink) !important;
        font-family: var(--font-display) !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em !important;
    }

    /* ── Top Nav Bar Container & Links (§3, §7.5) ── */
    div[class*="st-key-nexus_top_bar"] {
        padding-top: 0.25rem;
        padding-bottom: 0.25rem;
    }
    div[class*="st-key-nexus_top_bar"] div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    div[class*="st-key-nexus_top_bar"] button {
        background-color: transparent !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 7px 14px !important;
        font-family: var(--font-display) !important;
        font-size: 0.875rem !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
        min-width: 0 !important;
    }
    div[class*="st-key-nexus_top_bar"] button p,
    div[class*="st-key-nexus_top_bar"] button span {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        font-family: var(--font-display) !important;
    }
    /* Inactive nav link: Graphite text, subtle hover */
    div[class*="st-key-nexus_top_bar"] button[kind="secondary"],
    div[class*="st-key-nexus_top_bar"] button[data-testid="stBaseButton-secondary"] {
        border-bottom: 2.5px solid transparent !important;
        background-color: transparent !important;
    }
    div[class*="st-key-nexus_top_bar"] button[kind="secondary"] *,
    div[class*="st-key-nexus_top_bar"] button[kind="secondary"] p,
    div[class*="st-key-nexus_top_bar"] button[kind="secondary"] span,
    div[class*="st-key-nexus_top_bar"] button[data-testid="stBaseButton-secondary"] * {
        color: var(--color-graphite) !important;
        font-weight: 600 !important;
    }
    div[class*="st-key-nexus_top_bar"] button[kind="secondary"]:hover,
    div[class*="st-key-nexus_top_bar"] button[data-testid="stBaseButton-secondary"]:hover {
        background-color: rgba(0, 0, 0, 0.035) !important;
    }
    div[class*="st-key-nexus_top_bar"] button[kind="secondary"]:hover *,
    div[class*="st-key-nexus_top_bar"] button[data-testid="stBaseButton-secondary"]:hover * {
        color: var(--color-ink) !important;
    }
    /* Active nav link: Deep-Teal text + 2.5px Deep-Teal underline + soft tint */
    div[class*="st-key-nexus_top_bar"] button[kind="primary"],
    div[class*="st-key-nexus_top_bar"] button[data-testid="stBaseButton-primary"] {
        background-color: rgba(1, 106, 113, 0.08) !important;
        border: none !important;
        border-bottom: 2.5px solid var(--color-deep-teal) !important;
        border-radius: 6px 6px 0 0 !important;
    }
    div[class*="st-key-nexus_top_bar"] button[kind="primary"] *,
    div[class*="st-key-nexus_top_bar"] button[kind="primary"] p,
    div[class*="st-key-nexus_top_bar"] button[kind="primary"] span,
    div[class*="st-key-nexus_top_bar"] button[data-testid="stBaseButton-primary"] * {
        color: var(--color-deep-teal) !important;
        font-weight: 700 !important;
    }

    .nexus-nav-status {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-family: var(--font-display);
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--color-graphite);
        background: rgba(255, 255, 255, 0.35) !important;
        backdrop-filter: blur(6px) !important;
        -webkit-backdrop-filter: blur(6px) !important;
        border: 1px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 9999px;
        padding: 5px 14px;
        white-space: nowrap;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03), inset 0 1px 0 rgba(255, 255, 255, 0.9);
    }
    .nexus-nav-dot {
        width: 7px; height: 7px;
        border-radius: 50%;
        background-color: var(--color-deep-teal);
        box-shadow: 0 0 6px rgba(1, 106, 113, 0.6);
    }
    .nexus-nav-divider {
        border-bottom: 1px solid var(--color-warm-mist);
        margin-top: 0.5rem;
        margin-bottom: 1.25rem;
    }

    /* ── Glassmorphic Modular Card (§7.1) ── */
    .pplx-card {
        background: var(--glass-bg) !important;
        backdrop-filter: var(--glass-blur) saturate(120%) !important;
        -webkit-backdrop-filter: var(--glass-blur) saturate(120%) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        padding: 1.15rem 1.35rem;
        margin-bottom: 16px;
        box-shadow: var(--glass-shadow) !important;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .pplx-card:hover {
        background: var(--glass-bg-hover) !important;
        border-color: rgba(1, 106, 113, 0.28) !important;
        box-shadow: var(--glass-shadow-hover) !important;
        transform: translateY(-1px);
    }

    /* ── Card Label (§7.2) ── */
    .pplx-card-label {
        font-family: var(--font-display) !important;
        font-size: 0.72rem;
        color: #484640;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }

    /* ── Pills (§7.3) ── */
    .pplx-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.8125rem;
        font-weight: 500;
        border-radius: 9999px;
        padding: 4px 12px;
    }
    .pill-blocked {
        background-color: #fdf2f0;
        color: var(--color-risk-red);
        border: 1px solid #f2c7c2;
    }
    .pill-approved {
        background-color: var(--color-deep-teal);
        color: #ffffff;
    }
    .pill-conditional {
        background-color: #fef8ea;
        color: var(--color-risk-amber);
        border: 1px solid #f9e2af;
    }
    .pill-neutral {
        background-color: var(--color-parchment);
        color: var(--color-ink);
        border: 1px solid var(--color-warm-mist);
    }

    /* ── Sidebar (§4) ── */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: fixed !important;
        top: 14px !important;
        left: 14px !important;
        z-index: 100001 !important;
        background-color: var(--color-soft-paper) !important;
        border: 1px solid var(--color-warm-mist) !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06) !important;
        padding: 4px 6px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="stSidebarCollapsedControl"]:hover {
        background-color: var(--color-parchment) !important;
        border-color: var(--color-deep-teal) !important;
    }
    [data-testid="stSidebarCollapsedControl"] button {
        background: transparent !important;
        border: none !important;
        color: var(--color-ink) !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebarCollapsedControl"] span {
        color: var(--color-ink) !important;
    }

    [data-testid="stSidebarCollapseButton"] {
        opacity: 0.8 !important;
        visibility: visible !important;
        transition: opacity 0.15s ease !important;
    }
    [data-testid="stSidebarCollapseButton"]:hover {
        opacity: 1 !important;
    }
    [data-testid="stSidebarCollapseButton"] button {
        color: var(--color-graphite) !important;
        background: rgba(255, 255, 255, 0.35) !important;
        backdrop-filter: blur(6px) !important;
        -webkit-backdrop-filter: blur(6px) !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover {
        color: var(--color-ink) !important;
        background: rgba(255, 255, 255, 0.60) !important;
        border-color: var(--color-deep-teal) !important;
    }

    section[data-testid="stSidebar"] {
        background: var(--glass-bg) !important;
        backdrop-filter: var(--glass-blur) saturate(120%) !important;
        -webkit-backdrop-filter: var(--glass-blur) saturate(120%) !important;
        border-right: 1px solid var(--glass-border) !important;
        box-shadow: 4px 0 24px -2px rgba(39, 37, 30, 0.04), inset -1px 0 0 rgba(255, 255, 255, 0.9) !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    /* Sidebar Primary Button: Minimalist Teal with Glass Highlight */
    section[data-testid="stSidebar"] button[kind="primary"],
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background-color: var(--color-deep-teal) !important;
        border: 1px solid var(--color-deep-teal) !important;
        border-radius: 6px !important;
        font-family: var(--font-sans) !important;
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.01em !important;
        padding: 0.42rem 1rem !important;
        box-shadow: 0 4px 14px rgba(1, 106, 113, 0.20), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"] *,
    section[data-testid="stSidebar"] button[kind="primary"] p,
    section[data-testid="stSidebar"] button[kind="primary"] span,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] * {
        color: #ffffff !important;
        font-size: 0.8125rem !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        background-color: #015a60 !important;
        border-color: #015a60 !important;
        box-shadow: 0 6px 18px rgba(1, 106, 113, 0.30) !important;
    }

    /* Sidebar Reset Button: Glass Ghost */
    section[data-testid="stSidebar"] button[kind="secondary"],
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        background: rgba(255, 255, 255, 0.35) !important;
        backdrop-filter: blur(6px) !important;
        -webkit-backdrop-filter: blur(6px) !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
        border-radius: 6px !important;
        font-family: var(--font-sans) !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        padding: 0.38rem 0.85rem !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02), inset 0 1px 0 rgba(255, 255, 255, 0.85) !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"] *,
    section[data-testid="stSidebar"] button[kind="secondary"] p,
    section[data-testid="stSidebar"] button[kind="secondary"] span,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] * {
        color: var(--color-graphite) !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:hover,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
        background: rgba(255, 255, 255, 0.55) !important;
        border-color: rgba(1, 106, 113, 0.35) !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:hover * {
        color: var(--color-ink) !important;
    }

    /* Sidebar Glassmorphic Form Controls */
    section[data-testid="stSidebar"] div.react-aria-ComboBox > div,
    section[data-testid="stSidebar"] div.react-aria-TextField > div,
    section[data-testid="stSidebar"] div[data-testid="stTextInputRootElement"],
    section[data-testid="stSidebar"] div.st-emotion-cache-evk21s,
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="base-input"],
    section[data-testid="stSidebar"] div[data-baseweb="input"] {
        background: rgba(255, 255, 255, 0.38) !important;
        backdrop-filter: blur(6px) !important;
        -webkit-backdrop-filter: blur(6px) !important;
        border: 1px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02), inset 0 1px 0 rgba(255, 255, 255, 0.85) !important;
    }

    /* ── Form Controls ── */
    .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label {
        color: var(--color-graphite) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
    }
    div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.72) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(209, 209, 205, 0.6) !important;
        border-radius: 8px !important;
        color: var(--color-ink) !important;
        font-size: 0.875rem !important;
    }
    div[data-baseweb="select"] * { color: var(--color-ink) !important; }
    div[data-baseweb="select"]:hover > div { border-color: var(--color-deep-teal) !important; }

    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[data-baseweb="menu"] {
        background: rgba(255, 255, 255, 0.92) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid var(--color-warm-mist) !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
    }
    li[role="option"] { background-color: transparent !important; color: var(--color-ink) !important; }
    li[role="option"] * { color: var(--color-ink) !important; }
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] { background-color: rgba(1, 106, 113, 0.08) !important; color: var(--color-deep-teal) !important; }
    li[role="option"]:hover *,
    li[role="option"][aria-selected="true"] * { color: var(--color-deep-teal) !important; }

    div[data-baseweb="input"],
    div[data-baseweb="base-input"] {
        background: rgba(255, 255, 255, 0.72) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(209, 209, 205, 0.6) !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {
        background-color: transparent !important;
        color: var(--color-ink) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.875rem !important;
    }

    /* ── Copilot Suggestion Chips (§5.4) — Glassmorphic ── */
    div[class*="st-key-copilot_chips"] button {
        background: rgba(253, 251, 250, 0.62) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
        border-radius: 9999px !important;
        padding: 7px 16px !important;
        font-family: var(--font-sans) !important;
        font-size: 0.8125rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02), inset 0 1px 0 rgba(255, 255, 255, 0.85) !important;
        transition: all 0.15s ease !important;
    }
    div[class*="st-key-copilot_chips"] button * {
        color: var(--color-ink) !important;
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
    }
    div[class*="st-key-copilot_chips"] button:hover {
        border-color: var(--color-deep-teal) !important;
        background: rgba(253, 251, 250, 0.88) !important;
        box-shadow: 0 4px 14px rgba(1, 106, 113, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
    }
    div[class*="st-key-copilot_chips"] button:hover * {
        color: var(--color-deep-teal) !important;
    }

    /* ── Hint Dismiss Button ── */
    div[class*="st-key-hint_dismiss"] button {
        background-color: transparent !important;
        border: 1px solid var(--color-warm-mist) !important;
        border-radius: 6px !important;
        padding: 4px 8px !important;
        font-size: 0.75rem !important;
        box-shadow: none !important;
    }
    div[class*="st-key-hint_dismiss"] button * {
        color: var(--color-graphite) !important;
        font-size: 0.75rem !important;
        font-weight: 400 !important;
    }
    div[class*="st-key-hint_dismiss"] button:hover * {
        color: var(--color-ink) !important;
    }

    /* ── Chat Messages (§5.4) — Glassmorphic ── */
    div[data-testid="stChatInput"] {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(16px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(16px) saturate(140%) !important;
        border: 1px solid rgba(255, 255, 255, 0.85) !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 24px rgba(39, 37, 30, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: var(--color-ink) !important;
    }
    div[data-testid="stChatInput"] button { color: var(--color-deep-teal) !important; }

    div[data-testid="stChatMessage"] {
        background: var(--glass-bg) !important;
        backdrop-filter: var(--glass-blur) saturate(120%) !important;
        -webkit-backdrop-filter: var(--glass-blur) saturate(120%) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        margin-bottom: 14px !important;
        box-shadow: var(--glass-shadow) !important;
    }

    /* ── Inline Code (§1.2) ── */
    code {
        color: var(--color-ink) !important;
        background-color: #f0eee9 !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: inherit !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        border: 1px solid rgba(0, 0, 0, 0.06) !important;
    }

    /* ── Trace Step (agents section) ── */
    .trace-step {
        border-left: 2px solid var(--color-warm-mist);
        padding-left: 12px;
        margin-bottom: 12px;
        transition: border-color 0.15s ease;
    }
    .trace-step:hover { border-left-color: var(--color-deep-teal); }
    .trace-step-desc {
        font-size: 0.8125rem;
        color: var(--color-graphite);
        line-height: 1.45;
    }

    /* ── Pipeline Arrow ── */
    .pipeline-arrow {
        text-align: center;
        color: var(--color-warm-mist);
        font-size: 1.5rem;
    }

    /* ── Stat Row (§7.7) ── */
    .stat-row {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
        margin: 8px 0;
    }
    .stat-row .stat-label {
        font-size: 0.8125rem;
        color: var(--color-graphite);
    }
    .stat-row .stat-value {
        font-size: 0.9375rem;
        font-weight: 500;
        color: var(--color-ink);
    }

    /* ── Hint card (glassmorphic) ── */
    .hint-card {
        background: rgba(255, 255, 255, 0.22) !important;
        backdrop-filter: var(--glass-blur) !important;
        -webkit-backdrop-filter: var(--glass-blur) !important;
        border: 1px dashed rgba(209, 209, 205, 0.85) !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem;
        font-size: 0.8125rem;
        color: var(--color-graphite);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
    }

    /* ── Copilot label ── */
    .copilot-label {
        display: inline-block;
        font-size: 0.6875rem;
        font-weight: 500;
        color: var(--color-deep-teal);
        background-color: rgba(1, 106, 113, 0.08);
        border-radius: 4px;
        padding: 2px 6px;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* ── Material Symbols helper ── */
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        vertical-align: middle;
        font-size: 1.15rem;
        line-height: 1;
        display: inline-block;
    }

    /* ── Expander (glassmorphic) ── */
    [data-testid="stExpander"] details {
        background: var(--glass-bg) !important;
        backdrop-filter: var(--glass-blur) saturate(120%) !important;
        -webkit-backdrop-filter: var(--glass-blur) saturate(120%) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        box-shadow: var(--glass-shadow) !important;
        margin-bottom: 14px;
        transition: all 0.2s ease;
    }
    [data-testid="stExpander"] details:hover {
        background: var(--glass-bg-hover) !important;
        border-color: rgba(1, 106, 113, 0.25) !important;
    }
    [data-testid="stExpander"] details summary {
        border-radius: 12px !important;
        padding: 0.65rem 1rem !important;
    }
    [data-testid="stExpander"] details summary p {
        font-family: var(--font-display) !important;
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        color: var(--color-deep-teal) !important;
    }

    /* ── PyVis Graph Glassmorphic Frame ── */
    div[class*="st-key-nexus_graph_frame"] {
        background: var(--glass-bg) !important;
        backdrop-filter: var(--glass-blur) saturate(120%) !important;
        -webkit-backdrop-filter: var(--glass-blur) saturate(120%) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        box-shadow: var(--glass-shadow) !important;
        margin-bottom: 1.25rem !important;
        overflow: hidden !important;
        transition: all 0.22s ease !important;
    }
    div[class*="st-key-nexus_graph_frame"]:hover {
        background: var(--glass-bg-hover) !important;
        border-color: rgba(1, 106, 113, 0.35) !important;
        box-shadow: var(--glass-shadow-hover) !important;
    }
    div[class*="st-key-nexus_graph_frame"] iframe {
        background: transparent !important;
        border: none !important;
        border-radius: 12px !important;
        display: block !important;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# 3. Preset Benchmark Scenarios & Function Metadata
# ──────────────────────────────────────────────────────────────
SCENARIOS = {
    "1. PR-904 -> applyDiscount (Checkout Outage Risk)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-904",
        "function": "applyDiscount",
        "badge": "CRITICAL RISK",
        "summary": "Developer attempts to delete legacy discount branch. Violates CEO Slack promise to Client X and repeats $12,000 outage I-007."
    },
    "2. PR-512 -> chargeStripeInvoice (Stripe Retry Race)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-512",
        "function": "chargeStripeInvoice",
        "badge": "HIGH RISK",
        "summary": "Alters Stripe webhook retry. Triggered $8,500 duplicate billing in I-019. Requires shadow replay before deploy."
    },
    "3. PR-108 -> renderCart (UI Promo Banner)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-108",
        "function": "renderCart",
        "badge": "LOW RISK",
        "summary": "Isolated client-side cart banner animation. Zero downstream callers, zero contractual decisions, zero past outages."
    },
    "4. PR-401 -> verifyJwtToken (Multi-Tenant Auth)": {
        "tenant": "acme_auth",
        "pr_id": "PR-401",
        "function": "verifyJwtToken",
        "badge": "CRITICAL RISK",
        "summary": "Modifies JWT token verification algorithm in acme_auth tenant. Violates zero-downtime key rotation playbook P-002."
    },
    "5. PR-770 -> refundOrder (Batch Refund Pipeline)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-770",
        "function": "refundOrder",
        "badge": "MEDIUM RISK",
        "summary": "Batch processing refund requests. High caller blast radius tied to checkout flow. Auto-assigns expert Priya."
    },
    "6. PR-330 -> hardDeleteAccount (GDPR Non-Compliance)": {
        "tenant": "acme_data",
        "pr_id": "PR-330",
        "function": "hardDeleteAccount",
        "badge": "CRITICAL RISK",
        "summary": "Direct customer table deletion bypasses immutable auditLogEvent. Violates GDPR Article 17 decision D-005 ($45,000 fine in I-033)."
    },
    "7. PR-610 -> rateLimitRedisBucket (Infra Eviction)": {
        "tenant": "acme_checkout",
        "pr_id": "PR-610",
        "function": "rateLimitRedisBucket",
        "badge": "HIGH RISK",
        "summary": "Tightens Redis sliding window without memory cap review. Author Victor departed; Elena (SRE Lead) auto-assigned per playbook P-004."
    },
    "8. PR-350 -> encryptPiiField (Legacy Cipher Crash)": {
        "tenant": "acme_data",
        "pr_id": "PR-350",
        "function": "encryptPiiField",
        "badge": "HIGH RISK",
        "summary": "Modifies AES-GCM IV salt. Past incident I-042 broke 4,200 profiles ($18,000 loss). Requires dual-version read verification."
    }
}

FN_METADATA = {
    # acme_checkout
    "applyDiscount": {"tenant": "acme_checkout", "pr_id": "PR-904", "scenario_key": "1. PR-904 -> applyDiscount (Checkout Outage Risk)"},
    "chargeStripeInvoice": {"tenant": "acme_checkout", "pr_id": "PR-512", "scenario_key": "2. PR-512 -> chargeStripeInvoice (Stripe Retry Race)"},
    "renderCart": {"tenant": "acme_checkout", "pr_id": "PR-108", "scenario_key": "3. PR-108 -> renderCart (UI Promo Banner)"},
    "refundOrder": {"tenant": "acme_checkout", "pr_id": "PR-770", "scenario_key": "5. PR-770 -> refundOrder (Batch Refund Pipeline)"},
    "rateLimitRedisBucket": {"tenant": "acme_checkout", "pr_id": "PR-610", "scenario_key": "7. PR-610 -> rateLimitRedisBucket (Infra Eviction)"},
    "calculateTotal": {"tenant": "acme_checkout", "pr_id": "PR-102", "scenario_key": None},
    "checkout": {"tenant": "acme_checkout", "pr_id": "PR-101", "scenario_key": None},
    "circuitBreaker": {"tenant": "acme_checkout", "pr_id": "PR-104", "scenario_key": None},

    # acme_auth
    "verifyJwtToken": {"tenant": "acme_auth", "pr_id": "PR-401", "scenario_key": "4. PR-401 -> verifyJwtToken (Multi-Tenant Auth)"},
    "rotateSigningKey": {"tenant": "acme_auth", "pr_id": "PR-402", "scenario_key": None},
    "invalidateSessions": {"tenant": "acme_auth", "pr_id": "PR-403", "scenario_key": None},
    "enforceMfaPolicy": {"tenant": "acme_auth", "pr_id": "PR-404", "scenario_key": None},

    # acme_data
    "hardDeleteAccount": {"tenant": "acme_data", "pr_id": "PR-330", "scenario_key": "6. PR-330 -> hardDeleteAccount (GDPR Non-Compliance)"},
    "encryptPiiField": {"tenant": "acme_data", "pr_id": "PR-350", "scenario_key": "8. PR-350 -> encryptPiiField (Legacy Cipher Crash)"},
    "exportUserData": {"tenant": "acme_data", "pr_id": "PR-301", "scenario_key": None},
    "auditLogEvent": {"tenant": "acme_data", "pr_id": "PR-302", "scenario_key": None},
}

# State synchronization for sidebar parameters
if "sb_scenario" not in st.session_state:
    st.session_state["sb_scenario"] = list(SCENARIOS.keys())[0]
if "sb_tenant" not in st.session_state:
    st.session_state["sb_tenant"] = "acme_checkout"
if "sb_fn" not in st.session_state:
    st.session_state["sb_fn"] = "applyDiscount"
if "sb_pr_id" not in st.session_state:
    st.session_state["sb_pr_id"] = "PR-904"

def _reset_copilot_and_sim():
    st.session_state.pop("chat_history", None)
    st.session_state.pop("chat_target_key", None)
    st.session_state.pop("sim_data", None)
    st.session_state.pop("sim_key", None)

def _on_scenario_change():
    scen = SCENARIOS[st.session_state["sb_scenario"]]
    st.session_state["sb_tenant"] = scen["tenant"]
    st.session_state["sb_fn"] = scen["function"]
    st.session_state["sb_pr_id"] = scen["pr_id"]
    _reset_copilot_and_sim()

def _on_copilot_scen_change():
    new_scen = st.session_state["copilot_scen_switcher"]
    st.session_state["sb_scenario"] = new_scen
    _on_scenario_change()

def _on_tenant_change():
    new_t = st.session_state["sb_tenant"]
    fns = [f for f, m in FN_METADATA.items() if m["tenant"] == new_t]
    if st.session_state.get("sb_fn") not in fns:
        new_f = fns[0]
        st.session_state["sb_fn"] = new_f
        meta = FN_METADATA[new_f]
        st.session_state["sb_pr_id"] = meta["pr_id"]
        if meta["scenario_key"]:
            st.session_state["sb_scenario"] = meta["scenario_key"]
    _reset_copilot_and_sim()

def _on_fn_change():
    new_f = st.session_state["sb_fn"]
    meta = FN_METADATA.get(new_f, {})
    if meta:
        st.session_state["sb_pr_id"] = meta["pr_id"]
        if meta.get("scenario_key"):
            st.session_state["sb_scenario"] = meta["scenario_key"]
    _reset_copilot_and_sim()

orchestrator = GovernanceOrchestrator()

# ──────────────────────────────────────────────────────────────
# 4. Sidebar  (§4 — three labeled groups)
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="pplx-card-label" style="margin-bottom:8px;">SCENARIO</div>', unsafe_allow_html=True)
    scenario_choice = st.selectbox(
        "Benchmark scenario",
        options=list(SCENARIOS.keys()),
        key="sb_scenario",
        on_change=_on_scenario_change,
        label_visibility="collapsed"
    )

    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="pplx-card-label" style="margin-bottom:8px;">TARGET</div>', unsafe_allow_html=True)

    tenant_options = ["acme_checkout", "acme_auth", "acme_data"]
    tenant = st.selectbox(
        "Tenant repository",
        options=tenant_options,
        key="sb_tenant",
        on_change=_on_tenant_change
    )

    available_fns = [f for f, m in FN_METADATA.items() if m["tenant"] == tenant]
    selected_fn = st.selectbox(
        "Target function",
        options=available_fns,
        key="sb_fn",
        on_change=_on_fn_change
    )

    pr_id = st.text_input(
        "Pull Request ID",
        key="sb_pr_id"
    )

    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="pplx-card-label" style="margin-bottom:8px;">ACTIONS</div>', unsafe_allow_html=True)

    run_sim = st.button("Run Governance Simulation", type="primary", use_container_width=True)
    reset_db = st.button("Reset Graph Database", type="secondary", use_container_width=True)

    if reset_db:
        with st.spinner("Restoring FalkorDB graphs..."):
            seed.seed_all()
        st.toast("Graphs restored from company.json")
        st.rerun()

# Dynamic scenario summary lookup
matched_scenario = None
for s_key, s_data in SCENARIOS.items():
    if s_data["function"] == selected_fn and s_data["tenant"] == tenant:
        matched_scenario = s_data
        break

if matched_scenario:
    scenario_summary = matched_scenario["summary"]
else:
    scenario_summary = f"Pull request {pr_id} evaluating architectural changes in {selected_fn}() within repository {tenant}."

# ──────────────────────────────────────────────────────────────
# 6. Run Simulation (auto-run on first load or when button clicked)
# ──────────────────────────────────────────────────────────────
current_key = f"{tenant}_{selected_fn}_{pr_id}"
if "sim_data" not in st.session_state or st.session_state.get("sim_key") != current_key or run_sim:
    with st.spinner("Reading FalkorDB memory graphs\u2026"):
        st.session_state["sim_data"] = orchestrator.simulate_pr(pr_id=pr_id, target_function=selected_fn, repo=tenant)
        st.session_state["sim_key"] = current_key

sim = st.session_state["sim_data"]

# ──────────────────────────────────────────────────────────────
# 7. Nav State  (§3 — state machine)
# ──────────────────────────────────────────────────────────────
if "nav_section" not in st.session_state:
    st.session_state["nav_section"] = "overview"

# ──────────────────────────────────────────────────────────────
# 8. Top Nav Bar  (§3) — Brand + Links + Status on one row
# ──────────────────────────────────────────────────────────────
with st.container(key="nexus_top_bar"):
    nav_c1, nav_c2, nav_c3, nav_c4, nav_c5, nav_c6 = st.columns([2.8, 1.25, 1.0, 1.05, 1.05, 2.85], vertical_alignment="center")

    with nav_c1:
        st.markdown("""
        <div style="display: flex; flex-direction: column; gap: 3px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-family: var(--font-display); font-size: 1.4rem; font-weight: 800; color: #1e1c16; letter-spacing: -0.035em; line-height: 1;">Nexus<span style="color: var(--color-deep-teal);">Guard</span></span>
                <span style="font-family: var(--font-display); font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-deep-teal); background: rgba(1, 106, 113, 0.09); border: 1px solid rgba(1, 106, 113, 0.22); padding: 2px 7px; border-radius: 4px; display: inline-block;">GRAPH ENGINE</span>
            </div>
            <span style="font-family: var(--font-sans); font-size: 0.75rem; font-weight: 500; color: #6e6c66; line-height: 1.2;">Graph-backed governance for pull requests</span>
        </div>
        """, unsafe_allow_html=True)

    with nav_c2:
        is_active = st.session_state["nav_section"] == "overview"
        if st.button("Overview", key="nav_btn_overview", type="primary" if is_active else "secondary"):
            st.session_state["nav_section"] = "overview"
            st.rerun()

    with nav_c3:
        is_active = st.session_state["nav_section"] == "graph"
        if st.button("Graph", key="nav_btn_graph", type="primary" if is_active else "secondary"):
            st.session_state["nav_section"] = "graph"
            st.rerun()

    with nav_c4:
        is_active = st.session_state["nav_section"] == "agents"
        if st.button("Agents", key="nav_btn_agents", type="primary" if is_active else "secondary"):
            st.session_state["nav_section"] = "agents"
            st.rerun()

    with nav_c5:
        is_active = st.session_state["nav_section"] == "copilot"
        if st.button("Copilot", key="nav_btn_copilot", type="primary" if is_active else "secondary"):
            st.session_state["nav_section"] = "copilot"
            st.rerun()

    with nav_c6:
        st.markdown(f"""
        <div style="text-align: right;">
            <span class="nexus-nav-status">
                <span class="nexus-nav-dot"></span>
                <strong>FalkorDB</strong> &middot; {tenant}
            </span>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="nexus-nav-divider"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Helper: build verdict pill
# ──────────────────────────────────────────────────────────────
def _verdict_pill(decision: str) -> str:
    if decision == "BLOCKED":
        return '<span class="pplx-pill pill-blocked"><span class="material-symbols-outlined" style="font-size:16px;">block</span> Merge Blocked</span>'
    elif decision == "CONDITIONAL_APPROVAL":
        return '<span class="pplx-pill pill-conditional"><span class="material-symbols-outlined" style="font-size:16px;">warning</span> Conditional Approval</span>'
    else:
        return '<span class="pplx-pill pill-approved"><span class="material-symbols-outlined" style="font-size:16px;">check_circle</span> Auto-Approved</span>'

def _distill_why(sim_dict: dict, fn_name: str) -> str:
    dec = sim_dict.get("decision", "")
    decisions = sim_dict.get("scout_findings", {}).get("decision_chain", {}).get("justifying_decisions", [])
    incidents = sim_dict.get("scout_findings", {}).get("memories", {}).get("episodic_memory", {}).get("past_incidents", [])

    parts = []
    if decisions:
        d = decisions[0]
        summary_clean = d.get('summary', 'contractual promise').rstrip('.')
        parts.append(f"violates decision {d.get('decision_id')} ({summary_clean})")
    if incidents:
        inc = incidents[0]
        loss = inc.get("loss_usd", 0)
        loss_str = f" (${loss:,} outage)" if loss else ""
        parts.append(f"repeats incident {inc.get('incident_id')}{loss_str}")

    if dec == "BLOCKED":
        if parts:
            return f"Modifying <code>{fn_name}()</code> " + " and ".join(parts) + "."
        return f"Modifying <code>{fn_name}()</code> introduces high architectural risk with unresolved downstream caller dependencies."
    elif dec == "CONDITIONAL_APPROVAL":
        return f"Modifying <code>{fn_name}()</code> requires verified expert review and safe-migration playbook execution before merge."
    else:
        return f"Modifying <code>{fn_name}()</code> is an isolated change with zero downstream callers and no past outage records."


# ╔══════════════════════════════════════════════════════════════╗
# ║  SECTION: OVERVIEW  (§5.1 — default landing)                ║
# ╚══════════════════════════════════════════════════════════════╝
if st.session_state["nav_section"] == "overview":

    # ── Card A: Hero / "What is this?" ──
    st.markdown(textwrap.dedent(f"""
    <div class="pplx-card">
        <div class="pplx-card-label" style="color: var(--color-deep-teal);">GOVERNANCE OBJECTIVE</div>
        <div style="font-family: var(--font-display); font-size: 1.15rem; font-weight: 700; color: #1e1c16; margin-bottom: 8px;">What this does</div>
        <div style="font-size: 0.9375rem; color: var(--color-ink); line-height: 1.6; margin-bottom: 12px;">
            NexusGuard reviews pull requests against a FalkorDB knowledge graph:
            who really owns this code, what broke before, and what promises
            were made about it.
        </div>
        <div style="font-size: 0.875rem; color: var(--color-ink); margin-bottom: 4px;">
            ● Currently evaluating&ensp;
            <code>{pr_id}</code> &rarr; <code>{selected_fn}()</code>
            in <code>{tenant}</code>
        </div>
        <div style="font-size: 0.8125rem; color: var(--color-graphite); line-height: 1.5;">
            {scenario_summary}
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # ── Card B: Governance Verdict ──
    dec = sim["decision"]
    risk = sim["risk_level"]
    risk_color = "#b83a2b" if risk == "HIGH" else "#8a6100" if risk == "MEDIUM" else "#016a71"
    reviewer = sim["assigned_reviewer"]
    stale_docs = sim["fixer_action"]["action_result"].get("flagged_stale_docs", [])
    explanation = sim["fixer_action"]["explanation"]
    why_sentence = _distill_why(sim, selected_fn)

    st.markdown(textwrap.dedent(f"""
    <div class="pplx-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
            <div>
                <div class="pplx-card-label" style="color: var(--color-deep-teal);">AUTOMATED DECISION</div>
                <div style="font-family: var(--font-display); font-size: 1.15rem; font-weight: 700; color: #1e1c16; margin-bottom: 8px;">Governance Verdict</div>
                {_verdict_pill(dec)}
            </div>
            <div style="text-align: right;">
                <div class="pplx-card-label">ASSIGNED REVIEWER</div>
                <div style="font-family: var(--font-display); font-size: 1rem; font-weight: 700; color: var(--color-deep-teal);">{reviewer}</div>
            </div>
        </div>
        <div class="stat-row" style="border-top: 1px solid #f0eee9; padding-top: 10px;">
            <div><span class="stat-label">Risk:&nbsp;</span><span class="stat-value" style="color: {risk_color};">{risk}</span></div>
            <div><span class="stat-label">Docs that no longer match the code:&nbsp;</span><span class="stat-value">{len(stale_docs)}</span></div>
        </div>
        <div style="font-size: 0.875rem; color: var(--color-ink); line-height: 1.55; margin-top: 12px;">
            <strong>Why, in one sentence:</strong> {why_sentence}
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # "What happens next" expander
    playbook_steps = sim["fixer_action"]["playbook_steps"]
    with st.expander("What happens next", expanded=False):
        st.markdown(f"**Remediation Directive:** {explanation}")
        st.markdown("**Required steps before merge:**")
        for idx, step in enumerate(playbook_steps, 1):
            st.markdown(f"**{idx}.** {step}")

    # ── Card C: First-visit hint ──
    if not st.session_state.get("hint_dismissed"):
        hint_col, btn_col = st.columns([5, 1], vertical_alignment="center")
        with hint_col:
            st.markdown("""
            <div class="hint-card">
                Use the top navigation to inspect the <strong>Graph</strong>, explore the
                <strong>Agents</strong> pipeline, or ask questions in the <strong>Copilot</strong>.
            </div>
            """, unsafe_allow_html=True)
        with btn_col:
            with st.container(key="hint_dismiss"):
                if st.button("Dismiss", key="dismiss_hint"):
                    st.session_state["hint_dismissed"] = True
                    st.rerun()


# ╔══════════════════════════════════════════════════════════════╗
# ║  SECTION: GRAPH  (§5.2)                                     ║
# ╚══════════════════════════════════════════════════════════════╝
elif st.session_state["nav_section"] == "graph":

    st.markdown(f"""
    <div class="pplx-card-label" style="color: var(--color-deep-teal);">GRAPH TOPOLOGY &amp; TRACE</div>
    <div style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; color: #1e1c16; margin-bottom: 4px;">
        Code Graph Around <code>{selected_fn}()</code>
    </div>
    <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-bottom: 12px;">
        Each dot is a function, incident, or contractual decision record in FalkorDB. Drag nodes to explore relationships.
    </div>
    """, unsafe_allow_html=True)

    # ── Panel 1: PyVis Interactive Graph ──
    subgraph = tools.get_subgraph_for_visualization(selected_fn, repo=tenant)
    net = Network(height="520px", width="100%", bgcolor="rgba(0,0,0,0)", font_color="#27251e", directed=True, cdn_resources="remote")

    for n in subgraph["nodes"]:
        is_target = n.get("group") == "TargetFunction"
        net.add_node(
            n["id"],
            label=n["label"],
            title=n["title"],
            color=n.get("color", "#016a71" if is_target else "#27251e"),
            size=n.get("size", 24 if is_target else 16),
            shape=n.get("shape", "dot"),
            font={"face": "Inter, system-ui, sans-serif", "size": 12, "color": "#27251e"}
        )
    for e in subgraph["edges"]:
        net.add_edge(e["from"], e["to"], label=e["label"], title=e["title"], color="#d1d1cd", width=1.2)

    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 1.5,
        "borderWidthSelected": 2.5,
        "color": {
          "border": "#d1d1cd",
          "highlight": { "border": "#016a71", "background": "#016a71" }
        },
        "font": {
          "face": "Inter, -apple-system, system-ui, sans-serif",
          "size": 12,
          "color": "#27251e"
        }
      },
      "edges": {
        "color": { "color": "#d1d1cd", "highlight": "#016a71", "hover": "#016a71" },
        "smooth": { "type": "continuous", "roundness": 0.25 },
        "font": {
          "face": "Inter, -apple-system, system-ui, sans-serif",
          "size": 10,
          "color": "#72706b",
          "strokeWidth": 2,
          "strokeColor": "#faf8f5"
        },
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.65 } }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -160,
          "centralGravity": 0.012,
          "springLength": 210,
          "springStrength": 0.07,
          "damping": 0.90,
          "avoidOverlap": 1.0
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 120,
        "zoomView": true,
        "dragView": true
      }
    }
    """)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
        net.write_html(f.name)
        t_path = f.name
    with open(t_path, "r", encoding="utf-8") as f:
        html_vis = f.read()
    os.remove(t_path)

    # Inject glassmorphic transparency styles into the PyVis inner document
    glass_inner_css = """
    <style>
        html, body {
            background-color: transparent !important;
            background: transparent !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }
        .card {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        #mynetwork {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        canvas {
            background: transparent !important;
            background-color: transparent !important;
        }
    </style>
    """
    html_vis = html_vis.replace("</head>", f"{glass_inner_css}</head>")

    with st.container(key="nexus_graph_frame"):
        components.html(html_vis, height=540, scrolling=False)

    # ── Panel 2: Two-column expertise & blast radius ──
    col_exp, col_blast = st.columns(2)

    with col_exp:
        exp_info = sim["fixer_action"]["expert_info"]
        lead_data = exp_info.get("official_owner", {})
        reviewer = sim["assigned_reviewer"]
        ranked_html = ""
        for exp in exp_info.get("ranked_experts", [])[:3]:
            status_text = "Active" if exp["active"] else "Departed"
            is_assigned = "&bull; <span style='color:var(--color-deep-teal); font-weight:500;'>Assigned</span>" if exp["name"] == reviewer else ""
            status_color = "var(--color-deep-teal)" if exp["active"] else "var(--color-ash)"
            ranked_html += f'<div style="margin-bottom: 8px; font-size: 0.8125rem;"><div style="display: flex; justify-content: space-between; align-items: baseline;"><span><b>{exp["name"]}</b> <code>{exp["score"]}</code> &bull; <span style="color: {status_color};">{status_text}</span> {is_assigned}</span></div><div style="font-size: 0.75rem; color: var(--color-graphite); margin-top: 2px;">commits: {exp["commits"]} | reviews: {exp["reviews"]}</div></div>'

        st.markdown(textwrap.dedent(f"""
        <div class="pplx-card">
            <div class="pplx-card-label" style="color: var(--color-deep-teal);">CODE OWNERSHIP INTELLIGENCE</div>
            <div style="font-family: var(--font-display); font-size: 1.05rem; font-weight: 700; color: #1e1c16; margin-bottom: 6px;">Who actually knows this code</div>
            <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-bottom: 10px;">
                The graph finds who actually fixed this code recently — which may differ from the nominal team lead.
            </div>
            <div style="font-size: 0.875rem; margin-bottom: 12px; color: var(--color-ink);">
                Nominal Lead: <code>{lead_data.get('lead')}</code> ({lead_data.get('team')}) &mdash; Score: <code>{lead_data.get('lead_knowledge_score')}</code>
            </div>
            <div style="border-top: 1px solid var(--color-warm-mist); padding-top: 10px;">
                <div class="pplx-card-label">Ranked by recent contributions</div>
                {ranked_html}
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)

    with col_blast:
        callers = sim["scout_findings"]["blast_radius"].get("callers", [])
        callers_html = ""
        if callers:
            for c in callers[:4]:
                callers_html += f'<div style="font-size: 0.8125rem; font-family: monospace; color: var(--color-ink); margin-bottom: 4px;">&bull; {c["call_path"]}</div>'
        else:
            callers_html = '<div style="font-size: 0.8125rem; color: var(--color-deep-teal);">Isolated leaf node &mdash; zero downstream callers. A clean blast radius.</div>'

        decisions = sim["scout_findings"]["decision_chain"].get("justifying_decisions", [])
        dec_html = ""
        if decisions:
            d = decisions[0]
            dec_html = f'<div style="font-size: 0.875rem; font-weight: 500; color: var(--color-ink);">{d.get("decision_id")}: {d.get("summary")}</div><div style="font-size: 0.78rem; color: var(--color-graphite); font-style: italic; margin-top: 4px;">Slack #{d.get("slack_channel")} ({d.get("slack_date")}): &ldquo;{d.get("slack_text")}&rdquo;</div>'
        else:
            dec_html = '<div style="font-size: 0.8125rem; color: var(--color-graphite);">No contractual decisions linked to this function.</div>'

        st.markdown(textwrap.dedent(f"""
        <div class="pplx-card">
            <div class="pplx-card-label" style="color: var(--color-deep-teal);">BLAST RADIUS &amp; PROMISES</div>
            <div style="font-family: var(--font-display); font-size: 1.05rem; font-weight: 700; color: #1e1c16; margin-bottom: 6px;">What breaks if this change ships</div>
            <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-bottom: 10px;">
                Downstream callers that would be affected by changes to <code>{selected_fn}()</code>.
            </div>
            <div style="margin-bottom: 12px;">{callers_html}</div>
            <div style="border-top: 1px solid var(--color-warm-mist); padding-top: 10px;">
                <div class="pplx-card-label">Where this rule came from</div>
                {dec_html}
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  SECTION: AGENTS  (§5.3 — data-driven pipeline)             ║
# ╚══════════════════════════════════════════════════════════════╝
elif st.session_state["nav_section"] == "agents":

    st.markdown("""
    <div class="pplx-card-label" style="color: var(--color-deep-teal);">MULTI-AGENT GOVERNANCE</div>
    <div style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; color: #1e1c16; margin-bottom: 4px;">
        Autonomous Investigation Pipeline
    </div>
    <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-bottom: 16px;">Three specialized agents collaborating across FalkorDB knowledge graphs.</div>
    """, unsafe_allow_html=True)

    # Build data-driven findings for each agent
    callers = sim["scout_findings"]["blast_radius"].get("callers", [])
    incidents = sim["scout_findings"]["memories"]["episodic_memory"].get("past_incidents", [])
    decisions = sim["scout_findings"]["decision_chain"].get("justifying_decisions", [])

    scout_findings = []
    scout_findings.append(f"Found {len(callers)} downstream caller{'s' if len(callers) != 1 else ''} in the blast radius")
    if decisions:
        scout_findings.append(f"Retrieved decision {decisions[0].get('decision_id', 'N/A')}: {decisions[0].get('summary', '')}")
    if incidents:
        scout_findings.append(f"Recalled {len(incidents)} past incident{'s' if len(incidents) != 1 else ''} from memory")
    else:
        scout_findings.append("No past incidents found — clean history")

    consolidator_findings = [
        "Synthesized incident, procedural, and knowledge graph data",
        f"Verified tenant isolation for {tenant}",
        "Handed off consolidated findings to the decision-maker"
    ]

    reviewer_name = sim["assigned_reviewer"]
    fixer_findings = [
        f"Assigned {reviewer_name} as reviewer based on contribution history",
        f"Decision: {sim['decision'].replace('_', ' ').title()}",
        f"Generated {len(sim['fixer_action']['playbook_steps'])} required steps before merge"
    ]

    # Pipeline strip: three cards with arrows
    p1, a1, p2, a2, p3 = st.columns([3, 0.4, 3, 0.4, 3], vertical_alignment="center")

    with p1:
        findings_html = "".join([f'<div class="trace-step"><div class="trace-step-desc">{f}</div></div>' for f in scout_findings])
        st.markdown(textwrap.dedent(f"""
        <div class="pplx-card">
            <div class="pplx-card-label" style="color: var(--color-deep-teal); font-weight: 800;">STAGE 1 &middot; SCOUT</div>
            <div style="font-family: var(--font-display); font-size: 1.05rem; font-weight: 700; color: #1e1c16; margin-bottom: 6px;">Detective</div>
            {findings_html}
        </div>
        """).strip(), unsafe_allow_html=True)

    with a1:
        st.markdown('<div class="pipeline-arrow">&rarr;</div>', unsafe_allow_html=True)

    with p2:
        findings_html = "".join([f'<div class="trace-step"><div class="trace-step-desc">{f}</div></div>' for f in consolidator_findings])
        st.markdown(textwrap.dedent(f"""
        <div class="pplx-card">
            <div class="pplx-card-label" style="color: var(--color-deep-teal); font-weight: 800;">STAGE 2 &middot; CONSOLIDATOR</div>
            <div style="font-family: var(--font-display); font-size: 1.05rem; font-weight: 700; color: #1e1c16; margin-bottom: 6px;">Memory Librarian</div>
            {findings_html}
        </div>
        """).strip(), unsafe_allow_html=True)

    with a2:
        st.markdown('<div class="pipeline-arrow">&rarr;</div>', unsafe_allow_html=True)

    with p3:
        findings_html = "".join([f'<div class="trace-step"><div class="trace-step-desc">{f}</div></div>' for f in fixer_findings])
        st.markdown(textwrap.dedent(f"""
        <div class="pplx-card">
            <div class="pplx-card-label" style="color: var(--color-deep-teal); font-weight: 800;">STAGE 3 &middot; FIXER</div>
            <div style="font-family: var(--font-display); font-size: 1.05rem; font-weight: 700; color: #1e1c16; margin-bottom: 6px;">Decision-Maker</div>
            {findings_html}
        </div>
        """).strip(), unsafe_allow_html=True)

    # ── Memory Cards (two columns) ──
    m1, m2 = st.columns(2)

    with m1:
        inc_html = ""
        if incidents:
            for inc in incidents:
                inc_html += f'<div style="margin-bottom: 10px;"><div style="font-size: 0.875rem; font-weight: 500; color: var(--color-risk-red);">{inc["incident_id"]} <span style="font-size: 0.75rem; color: var(--color-graphite);">({inc.get("date", "N/A")})</span> &bull; ${inc.get("loss_usd", 0):,} loss</div><div style="font-size: 0.8125rem; color: var(--color-graphite); line-height: 1.4; margin-top: 2px;">{inc.get("summary")}</div></div>'
        else:
            inc_html = '<div style="font-size: 0.85rem; color: var(--color-deep-teal);">No past incidents recorded for this function — a clean history.</div>'

        st.markdown(textwrap.dedent(f"""
        <div class="pplx-card">
            <div class="pplx-card-label">Past incidents this code caused</div>
            <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-bottom: 10px;">
                NexusGuard remembers outages across restarts — this is FalkorDB, not a chat history.
            </div>
            {inc_html}
        </div>
        """).strip(), unsafe_allow_html=True)

    with m2:
        steps = sim["fixer_action"]["playbook_steps"]
        steps_html = "".join([f'<div style="font-size: 0.8125rem; color: var(--color-ink); margin-bottom: 8px;"><span style="color: var(--color-deep-teal); font-weight: 600;">[{idx}]</span> {step}</div>' for idx, step in enumerate(steps, 1)])
        st.markdown(textwrap.dedent(f"""
        <div class="pplx-card">
            <div class="pplx-card-label">Required steps before merge</div>
            <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-bottom: 10px;">
                Mandatory checklist generated from playbook and incident memory.
            </div>
            <div style="margin-top: 8px;">{steps_html}</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    # ── Advanced expander: how agents coordinate (§5.3) ──
    with st.expander("How agents coordinate (advanced)", expanded=False):
        st.markdown("""
The three agents communicate through a shared **blackboard** stored in FalkorDB as `dev_agent_state` tokens.

1. **Scout** writes its raw findings (blast radius, decision chain, episodic memory) to the blackboard.
2. **Consolidator** reads all Scout tokens, cross-references tenant isolation boundaries, synthesizes a unified risk picture, and posts a consolidated token.
3. **Fixer** consumes the consolidated token, computes expertise centrality, generates the verdict, assigns a reviewer, and writes the final state.

Each token is a graph node linked to the PR and target function, so the full reasoning chain is queryable via Cypher after the simulation completes.
        """)


# ╔══════════════════════════════════════════════════════════════╗
# ║  SECTION: COPILOT  (§5.4 — Q&A over the graph)              ║
# ╚══════════════════════════════════════════════════════════════╝
elif st.session_state["nav_section"] == "copilot":

    st.markdown("""
    <div class="pplx-card-label" style="color: var(--color-deep-teal);">INTERACTIVE GOVERNANCE</div>
    <div style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; color: #1e1c16; margin-bottom: 4px;">
        Governance Copilot
    </div>
    <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-bottom: 14px;">
        Ask questions directly against the FalkorDB knowledge graph.
    </div>
    """, unsafe_allow_html=True)

    # ── Active Connected Context Header Card ──
    dec = sim.get("decision", "BLOCKED")
    reviewer = sim.get("assigned_reviewer", "Verified Contributor")
    risk = sim.get("risk_level", "HIGH")
    explanation = sim.get("fixer_action", {}).get("explanation", "")
    playbook = sim.get("fixer_action", {}).get("playbook_steps", [])
    decisions = sim.get("scout_findings", {}).get("decision_chain", {}).get("justifying_decisions", [])
    incidents = sim.get("scout_findings", {}).get("memories", {}).get("episodic_memory", {}).get("past_incidents", [])
    callers = sim.get("scout_findings", {}).get("blast_radius", {}).get("callers", [])
    exp_info = sim.get("fixer_action", {}).get("expert_info", {})

    st.markdown(f"""
    <div class="pplx-card" style="margin-bottom: 12px; padding: 12px 18px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
            <div>
                <div class="pplx-card-label" style="margin-bottom: 3px;">CONNECTED SCENARIO CONTEXT</div>
                <div style="font-size: 1rem; font-weight: 500; color: var(--color-ink);">
                    <code>{pr_id}</code> &rarr; <code>{selected_fn}()</code> &middot; <span style="color: var(--color-deep-teal); font-weight: 500;">{tenant}</span>
                </div>
                <div style="font-size: 0.8125rem; color: var(--color-graphite); margin-top: 4px; line-height: 1.45;">
                    {scenario_summary}
                </div>
            </div>
            <div style="text-align: right; flex-shrink: 0;">
                {_verdict_pill(dec)}
                <div style="font-size: 0.75rem; color: var(--color-graphite); margin-top: 4px;">Assigned: <strong style="color:var(--color-deep-teal);">{reviewer}</strong></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # In-Copilot quick scenario switcher
    curr_scen_idx = list(SCENARIOS.keys()).index(st.session_state["sb_scenario"]) if st.session_state["sb_scenario"] in SCENARIOS else 0
    st.selectbox(
        "Active Scenario",
        options=list(SCENARIOS.keys()),
        index=curr_scen_idx,
        key="copilot_scen_switcher",
        on_change=_on_copilot_scen_change,
        help="Switch benchmark scenario directly from Copilot"
    )

    # ── Fully Scenario-Tailored Suggestion Chips ──
    if dec == "BLOCKED":
        chip1_label = f"Why was {pr_id} blocked?"
    elif dec == "CONDITIONAL_APPROVAL":
        chip1_label = f"Why conditional approval for {pr_id}?"
    else:
        chip1_label = f"Why was {pr_id} auto-approved?"

    chip2_label = f"Who is the verified expert for {selected_fn}()?"

    if incidents:
        first_inc = incidents[0]
        loss_val = first_inc.get("loss_usd", 0)
        loss_str = f" (${loss_val:,})" if loss_val else ""
        chip3_label = f"Explain incident {first_inc.get('incident_id')}{loss_str}"
    elif decisions:
        first_dec = decisions[0]
        chip3_label = f"Show decision {first_dec.get('decision_id')} details"
    else:
        chip3_label = f"Verify blast radius of {selected_fn}()"

    with st.container(key="copilot_chips"):
        col_c1, col_c2, col_c3 = st.columns(3)
        chip_prompt = None
        with col_c1:
            if st.button(chip1_label, use_container_width=True, key=f"chip1_{current_key}"):
                chip_prompt = chip1_label
        with col_c2:
            if st.button(chip2_label, use_container_width=True, key=f"chip2_{current_key}"):
                chip_prompt = chip2_label
        with col_c3:
            if st.button(chip3_label, use_container_width=True, key=f"chip3_{current_key}"):
                chip_prompt = chip3_label

    # Reset chat history if evaluation target changed
    if "chat_history" not in st.session_state or st.session_state.get("chat_target_key") != current_key:
        st.session_state["chat_history"] = [
            {"role": "assistant", "content": f"NexusGuard Copilot online. Connected to `{tenant}`. Currently analyzing PR `{pr_id}` touching `{selected_fn}()` (Verdict: **{dec}**, Risk: **{risk}**). How can I assist you with this change?"}
        ]
        st.session_state["chat_target_key"] = current_key

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    query = st.chat_input("Ask a question about this code change\u2026") or chip_prompt

    if query:
        st.session_state["chat_history"].append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        q_lower = query.lower()

        if any(w in q_lower for w in ["why", "verdict", "decision", "block", "approve", "conditional"]):
            label = '<span class="copilot-label">Governance Finding</span>'
            if dec == "BLOCKED":
                reasons = []
                if decisions:
                    d = decisions[0]
                    reasons.append(f"Decision `{d.get('decision_id')}` (*{d.get('summary', '').rstrip('.')}*)")
                if incidents:
                    inc = incidents[0]
                    loss = inc.get("loss_usd", 0)
                    loss_str = f" causing a **${loss:,} outage loss**" if loss else ""
                    reasons.append(f"Incident `{inc.get('incident_id')}` ({inc.get('summary', '')}{loss_str})")

                reason_text = " and repeats ".join(reasons) if reasons else f"blast radius constraints in `{tenant}`"
                ans = (
                    f"{label}\n\n`PR {pr_id}` was **BLOCKED** because modifying `{selected_fn}()` violates {reason_text}.\n\n"
                    f"**Remediation Directive:** {explanation}"
                )
            elif dec == "CONDITIONAL_APPROVAL":
                steps_txt = "; ".join(playbook[:2]) if playbook else "required safety validations"
                ans = (
                    f"{label}\n\n`PR {pr_id}` received **CONDITIONAL APPROVAL** (Risk: **{risk}**). "
                    f"Modifying `{selected_fn}()` touches active services. Before merge, author must complete: {steps_txt}.\n\n"
                    f"**Reviewer Assigned:** `{reviewer}` per historical incident resolution centrality."
                )
            else:
                ans = (
                    f"{label}\n\n`PR {pr_id}` is **AUTO-APPROVED** (Risk: **LOW**). "
                    f"Function `{selected_fn}()` has zero downstream callers, zero contractual decisions, and zero historical outages recorded in FalkorDB."
                )
        elif any(w in q_lower for w in ["expert", "who", "lead", "reviewer"]):
            label = '<span class="copilot-label">Expertise Centrality</span>'
            lead_data = exp_info.get("official_owner", {})
            lead_name = lead_data.get("lead", "Official Lead")
            lead_team = lead_data.get("team", "Core Team")
            lead_score = lead_data.get("lead_knowledge_score", 0)
            ranked = exp_info.get("ranked_experts", [])

            details = []
            for exp in ranked[:3]:
                st_text = "active" if exp.get("active") else "departed"
                details.append(f"- **{exp['name']}** (Score: `{exp['score']}`, {st_text}, {exp.get('commits', 0)} commits, {exp.get('reviews', 0)} reviews)")

            ranked_list = "\n".join(details) if details else "- No previous committer history recorded."
            ans = (
                f"{label}\n\nNominal team lead `{lead_name}` ({lead_team}) has knowledge score of `{lead_score}`. "
                f"FalkorDB computed graph centrality over recency-weighted commits and past incident responses:\n\n{ranked_list}\n\n"
                f"NexusGuard auto-assigned **`{reviewer}`** to review PR `{pr_id}`."
            )
        elif any(w in q_lower for w in ["incident", "outage", "loss", "broke", "history"]):
            label = '<span class="copilot-label">Incident Memory</span>'
            if incidents:
                inc = incidents[0]
                loss = inc.get("loss_usd", 0)
                loss_str = f" causing a **${loss:,} outage loss**" if loss else ""
                ans = (
                    f"{label}\n\n**Incident `{inc.get('incident_id')}` ({inc.get('date', 'Historical')}):**\n\n"
                    f"{inc.get('summary')}{loss_str}.\n\n"
                    f"Root cause in FalkorDB: modifying `{selected_fn}()` directly repeated this failure mode. "
                    f"NexusGuard flagged 1 governing doc as stale."
                )
            else:
                ans = f"{label}\n\nZero past outages or incidents are linked to `{selected_fn}()` in repository `{tenant}`. Clean historical record in FalkorDB."
        elif any(w in q_lower for w in ["slack", "promise", "ceo", "contract", "provenance", "decision", "rule", "ticket"]):
            label = '<span class="copilot-label">Decision Provenance</span>'
            if decisions:
                d = decisions[0]
                slack_txt = f"\n\n> *\"{d.get('slack_text', '')}\"*" if d.get('slack_text') else ""
                channel_txt = f"Channel: `#{d.get('slack_channel', 'general')}` &middot; " if d.get('slack_channel') else ""
                date_txt = f"Date: `{d.get('slack_date', 'N/A')}` &middot; " if d.get('slack_date') else ""
                ticket_txt = f"Ticket: `[{d.get('ticket_id', 'N/A')}]`" if d.get('ticket_id') else ""
                ans = (
                    f"{label}\n\n**Decision `{d.get('decision_id')}`:** {d.get('summary')}{slack_txt}\n\n"
                    f"{channel_txt}{date_txt}{ticket_txt}"
                )
            else:
                ans = f"{label}\n\nNo contractual Slack decisions or executive commitments are attached to function `{selected_fn}()` in repository `{tenant}`."
        elif any(w in q_lower for w in ["blast", "caller", "callers", "radius", "depend", "breaks", "impact"]):
            label = '<span class="copilot-label">Blast Radius Analysis</span>'
            if callers:
                caller_items = "\n".join([f"- `{c['call_path']}` (hops: {c['hops']})" for c in callers[:6]])
                ans = (
                    f"{label}\n\nModifying `{selected_fn}()` affects **{len(callers)} downstream caller(s)** across repository `{tenant}`:\n\n"
                    f"{caller_items}\n\n"
                    f"Assigned reviewer `{reviewer}` must verify backward compatibility for these call paths."
                )
            else:
                ans = f"{label}\n\n`{selected_fn}()` is an **isolated leaf function** with zero downstream callers. Blast radius is completely contained."
        else:
            label = '<span class="copilot-label">Graph Summary</span>'
            ans = (
                f"{label}\n\n"
                f"- **Function:** `{selected_fn}()` in `{tenant}`\n"
                f"- **Pull Request:** `{pr_id}`\n"
                f"- **Impacted Callers:** {len(callers)}\n"
                f"- **Past Outages in Memory:** {len(incidents)}\n"
                f"- **Governing Decisions:** {len(decisions)}\n"
                f"- **Verified Expert Reviewer:** `{reviewer}`\n"
                f"- **Governance Verdict:** `{dec}` (Risk: `{risk}`)"
            )

        st.session_state["chat_history"].append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# 9. Footer  (§5.5)
# ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; color: var(--color-graphite); font-size: 0.75rem; margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--color-warm-mist);">
    NexusGuard &middot; Built on FalkorDB &middot; FalkorDB Hackathon 2026
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# 10. Ambient Background Nodes (rendered at bottom of page)
# ──────────────────────────────────────────────────────────────
components.html("""
<script>
(function() {
    const parentDoc = window.parent.document || document;
    const parentWin = window.parent || window;

    // Remove any previous canvas versions
    const oldCanvases = parentDoc.querySelectorAll('#minimal-nodes-canvas, #nexus-3d-constellation');
    oldCanvases.forEach(el => el.remove());

    const canvas = parentDoc.createElement('canvas');
    canvas.id = 'nexus-3d-constellation';
    canvas.dataset.version = 'v3_glass_3d';
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100vw';
    canvas.style.height = '100vh';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '0';
    canvas.style.opacity = '0.92';
    parentDoc.body.prepend(canvas);

    const ctx = canvas.getContext('2d');
    let width = 0;
    let height = 0;
    const dpr = Math.min(parentWin.devicePixelRatio || 1, 2);

    function resize() {
        width = parentWin.innerWidth || window.innerWidth;
        height = parentWin.innerHeight || window.innerHeight;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    parentWin.addEventListener('resize', resize, { passive: true });

    // Generate 3D Nodes clustered in an undulating geometric band across the page
    const NODE_COUNT = 62;
    const nodes = [];

    for (let i = 0; i < NODE_COUNT; i++) {
        const normX = (i / (NODE_COUNT - 1)) * 2 - 1; // -1 to 1
        const x = normX * (width * 0.58) + (Math.random() - 0.5) * 55;
        const wave = Math.sin(normX * Math.PI * 1.5) * (height * 0.18);
        const y = wave + (Math.random() - 0.5) * (height * 0.62);
        const z = (Math.random() - 0.5) * 460; // -230 to +230

        nodes.push({
            ox: x, oy: y, oz: z,
            vx: (Math.random() - 0.5) * 0.14,
            vy: (Math.random() - 0.5) * 0.14,
            vz: (Math.random() - 0.5) * 0.14,
            px: 0, py: 0, pz: 0, scale: 1
        });
    }

    // Interactive cursor tracking
    let targetRotY = 0;
    let targetRotX = 0;
    let targetPanX = 0;
    let targetPanY = 0;

    let rotY = 0;
    let rotX = 0;
    let panX = 0;
    let panY = 0;

    parentWin.addEventListener('mousemove', (e) => {
        const cx = width / 2;
        const cy = height / 2;
        const nx = (e.clientX - cx) / cx;
        const ny = (e.clientY - cy) / cy;

        targetRotY = nx * 0.40;
        targetRotX = -ny * 0.30;
        targetPanX = nx * 45;
        targetPanY = ny * 28;
    }, { passive: true });

    function animate() {
        ctx.clearRect(0, 0, width, height);

        // Smooth inertia damping
        rotY += (targetRotY - rotY) * 0.055;
        rotX += (targetRotX - rotX) * 0.055;
        panX += (targetPanX - panX) * 0.055;
        panY += (targetPanY - panY) * 0.055;

        // Subtle harmonic idle breathing
        const time = performance.now() * 0.0006;
        const idleRotY = Math.sin(time) * 0.035;
        const idleRotX = Math.cos(time * 0.8) * 0.025;

        const curRotY = rotY + idleRotY;
        const curRotX = rotX + idleRotX;

        const cosY = Math.cos(curRotY), sinY = Math.sin(curRotY);
        const cosX = Math.cos(curRotX), sinX = Math.sin(curRotX);

        const cx = width / 2;
        const cy = height / 2 + 15;
        const fov = 750;

        // 1. Update and Project 3D positions to 2D
        for (let i = 0; i < nodes.length; i++) {
            const n = nodes[i];
            n.ox += n.vx;
            n.oy += n.vy;
            n.oz += n.vz;

            if (Math.abs(n.ox) > width * 0.65) n.vx *= -1;
            if (Math.abs(n.oy) > height * 0.48) n.vy *= -1;
            if (Math.abs(n.oz) > 240) n.vz *= -1;

            // Rotation around Y
            const x1 = n.ox * cosY + n.oz * sinY;
            const y1 = n.oy;
            const z1 = -n.ox * sinY + n.oz * cosY;

            // Rotation around X
            const x2 = x1;
            const y2 = y1 * cosX - z1 * sinX;
            const z2 = y1 * sinX + z1 * cosX;

            const scale = fov / (fov + z2 + 250);
            n.px = cx + (x2 + panX) * scale;
            n.py = cy + (y2 + panY) * scale;
            n.pz = z2;
            n.scale = scale;
        }

        // 2. Draw Triangulated Connecting Lines
        const MAX_DIST = 145;
        for (let i = 0; i < nodes.length; i++) {
            const ni = nodes[i];
            for (let j = i + 1; j < nodes.length; j++) {
                const nj = nodes[j];
                const dx = ni.px - nj.px;
                const dy = ni.py - nj.py;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < MAX_DIST) {
                    const alpha = (1 - dist / MAX_DIST);
                    const avgZ = (ni.pz + nj.pz) / 2;

                    ctx.beginPath();
                    ctx.moveTo(ni.px, ni.py);
                    ctx.lineTo(nj.px, nj.py);

                    if (avgZ < 0) {
                        // Foreground line: crisp dark ink (#1e1c16)
                        ctx.strokeStyle = 'rgba(30, 28, 22, ' + (alpha * 0.70).toFixed(3) + ')';
                        ctx.lineWidth = 1.10;
                    } else {
                        // Background line: soft graphite (#92918b)
                        ctx.strokeStyle = 'rgba(138, 137, 131, ' + (alpha * 0.40).toFixed(3) + ')';
                        ctx.lineWidth = 0.85;
                    }
                    ctx.stroke();
                }
            }
        }

        // 3. Draw Nodes (Depth-sorted so foreground renders over background)
        const sortedIndices = [];
        for (let i = 0; i < nodes.length; i++) sortedIndices.push(i);
        sortedIndices.sort((a, b) => nodes[b].pz - nodes[a].pz);

        for (let k = 0; k < sortedIndices.length; k++) {
            const n = nodes[sortedIndices[k]];
            ctx.beginPath();

            if (n.pz < 0) {
                // Foreground: crisp dark circular dot
                const r = Math.max(2.2, 3.2 * n.scale);
                ctx.arc(n.px, n.py, r, 0, Math.PI * 2);
                ctx.fillStyle = '#1e1c16';
                ctx.fill();
            } else {
                // Background: soft grey translucent circle
                const r = Math.max(3.0, 4.4 * n.scale);
                ctx.arc(n.px, n.py, r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(146, 145, 139, 0.62)';
                ctx.fill();
            }
        }

        requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
})();
</script>
""", height=0)
