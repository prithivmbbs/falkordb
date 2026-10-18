# NexusGuard — UI Component Specification

**Purpose of this document.** This is the single source of truth for how every part of the NexusGuard web app looks and behaves. Any engineer or agent can restructure `app.py` from this file alone. It replaces the current "everything at once" layout with a minimal, self-explanatory interface.

**Current problems this spec fixes.**
1. All content (verdict, graph, expert rankings, agent traces, memory, chat) renders at once — a wall of detail on first load.
2. No navigation. Brand header is static decoration; `st.tabs` do the real work but read as a single dense scroll.
3. Sidebar is unlabeled and mixes settings with actions.
4. Two conflicting design themes exist in the repo (`DESIGN.md` vs `walkthrough.md`). This spec standardizes on **Scholar's Parchment** (already implemented).

---

## 1. Design Foundation — Scholar's Parchment

### 1.1 Color tokens

| Token | Hex | Use |
|---|---|---|
| Parchment | `#faf8f5` | Page canvas |
| Soft Paper | `#fdfbfa` | Card surfaces |
| Warm Mist | `#d1d1cd` | Borders, dividers, edges |
| Ash | `#92918b` | Disabled / muted text |
| Graphite | `#72706b` | Secondary text, captions |
| Ink | `#27251e` | Primary text, headings |
| Deep Teal | `#016a71` | Accent: active nav, buttons, highlights, links |
| Risk Red | `#b83a2b` | BLOCKED verdicts, HIGH risk, incident loss amounts |
| Risk Amber | `#8a6100` | CONDITIONAL verdicts, MEDIUM risk |

Semantic rule: **Deep Teal = informational/positive. Red = blocked/danger. Amber = conditional.** Never use teal for danger.

### 1.2 Typography

- Font: `Inter` (weights 400 and 500 only — no bold display weight).
- App title: 1.25rem / 500 / `letter-spacing: -0.02em`.
- Card labels (`.pplx-card-label`): 11–12px / 500 / uppercase Graphite.
- Body text: 0.875–1rem / 400 / Ink, `line-height: 1.5`.
- Captions: 0.8125rem / 400 / Graphite.
- Code (`<code>`): same size as surrounding text, monospace, subtle background `#f0eee9`.

### 1.3 Spacing & shape

- Content column max-width: **920px**, centered.
- Card padding: 1rem–1.25rem. Card radius: 8px. Card border: 1px solid `#d1d1cd`.
- Vertical rhythm between cards: 12–16px. Between sections: 24px.
- Shadows: none (flat design; borders carry the structure).

### 1.4 Three golden rules (apply everywhere)

1. **One idea per card.** A card answers exactly one question. If it answers two, split it or move one answer behind a disclosure.
2. **Every technical label gets a plain-English caption.** "Blast Radius" → caption "What breaks if this change ships". Never show jargon alone.
3. **Nothing renders until asked for.** The landing state shows the minimum. Deep detail lives behind navigation (§3) or expanders (§7.6).

---

## 2. App Shell

```
┌──────────────────────────────────────────────────────────────────────┐
│  ⬡ NexusGuard     Overview   Graph   Agents   Copilot    ● FalkorDB  │  ← Top Nav Bar (sticky)
│  Autonomous code review…                                             │
├──────────────┬───────────────────────────────────────────────────────┤
│  SIDEBAR     │   MAIN PANEL                                          │
│              │                                                       │
│  SCENARIO    │   (exactly ONE section renders at a time,             │
│  Benchmark   │    chosen by the nav bar)                             │
│  scenario ▾  │                                                       │
│              │   ┌─────────────────────────────────────┐             │
│  TARGET      │   │  card                               │             │
│  Tenant  ▾   │   └─────────────────────────────────────┘             │
│  Function ▾  │   ┌─────────────────────────────────────┐             │
│  PR ID  ___  │   │  card                               │             │
│              │   └─────────────────────────────────────┘             │
│  ──────────  │                                                       │
│  [ Run Sim ] │                                                       │
│  [ Reset ]   │                                                       │
└──────────────┴───────────────────────────────────────────────────────┘
```

- Sidebar: fixed width (~300px), parchment background, always visible (desktop).
- Main panel: single column, max 920px, centered within remaining space.
- The app renders **one section at a time**. There is no long scroll and no visible tab row.

---

## 3. Top Nav Bar (section switcher)

The nav bar replaces the current static header (app.py ~636–649) and the `st.tabs` (app.py ~727–731).

### 3.1 Contents (left → right)

| Slot | Content |
|---|---|
| Brand | `NexusGuard` (Ink, 1.25rem/500) |
| Value prop | one line, Graphite 0.8125rem: `Graph-backed governance for code review` — hidden below 1000px width |
| Section links | `Overview` · `Graph` · `Agents` · `Copilot` |
| Status | Pill: teal dot + `FalkorDB · <tenant>` |

### 3.2 Behavior

- Sticky at top; parchment background; 1px Warm-Mist bottom border.
- **Active link**: Ink text + 2px Deep-Teal underline. **Inactive links**: Graphite.
- Clicking a link sets `st.session_state["nav_section"]` (one of `overview | graph | agents | copilot`) and reruns the app. Default: `overview`.
- Landing state = **Overview**. A visitor sees what the product is before seeing any internals.

### 3.3 Copy contract (what the first-time viewer reads, in order)

1. Nav value prop — *what it is.*
2. Overview hero — *what it does* (§5.1).
3. Verdict card — *what it decided, right now* (§5.2).

That's the entire first impression. Everything else requires a click.

---

## 4. Sidebar

Groups only — no free-floating labels, no `---` dividers between every widget. Group titles use the card-label style.

### 4.1 Structure

```
SCENARIO
  Benchmark scenario ▾        (the 8 built-in PR scenarios)

TARGET
  Tenant repository ▾         (acme_checkout / acme_auth / acme_data)
  Target function ▾           (filtered per tenant)
  Pull Request ID  [PR-904]

ACTIONS
  [ Run Governance Simulation ]      ← primary, teal filled, full width
  [ Reset Graph Database ]           ← ghost/quiet button, full width
```

### 4.2 Rules

- Selecting a scenario auto-populates Tenant / Function / PR ID (existing behavior, keep it).
- `Run` is always visible; `Reset` is visually quieter (ghost button) — it is destructive.
- After reset: success toast **"Graphs restored from company.json"** and rerun. Toasts must not be suppressed (remove the current `stToast`/`stNotification` `display:none` CSS — feedback was invisible).
- No footer caption in sidebar. Attribution moves to the app footer (§5.5).

---

## 5. Main Panel Sections

### 5.1 Section: Overview (default landing)

Purpose: a stranger should understand the product in one screen.

**Card A — Hero / "What is this?"**

```
┌────────────────────────────────────────────────────────────┐
│ WHAT THIS DOES                                             │
│ NexusGuard reviews pull requests against a FalkorDB        │
│ knowledge graph: who really owns this code, what broke     │
│ before, and what promises were made about it.              │
│                                                            │
│ ● Currently evaluating  PR-904 → applyDiscount()           │
│   in acme_checkout                                         │
└────────────────────────────────────────────────────────────┘
```

- First paragraph is **static copy** (always the same, plain English).
- Second line is live-bound: `PR {pr_id}`, `{selected_fn}()`, `{tenant}`.
- Below it, the current scenario summary in a caption (`current_scenario["summary"]`).

**Card B — Governance Verdict**

```
┌────────────────────────────────────────────────────────────┐
│ VERDICT                              Assigned reviewer     │
│ [⛔ Merge Blocked]                   Alice  (score 4.79)   │
│ ────────────────────────────────────────────────────────── │
│ Risk: HIGH            Stale docs: 1                        │
│                                                            │
│ Why, in one sentence: modifying applyDiscount violates     │
│ decision D-001 (CEO pricing promise) and repeats incident  │
│ I-007 ($12,000 outage).                                    │
│                                                            │
│ [ What happens next ▸ ]   ← expander, closed by default    │
└────────────────────────────────────────────────────────────┘
```

- Verdict pill: same three states as today (blocked / conditional / approved) with icons.
- **"Why, in one sentence"** — new mandatory element: a single plain-English sentence distilled from `sim["fixer_action"]["explanation"]`. This is the *explains itself on sight* requirement.
- `What happens next` expander contains the full remediation directive + playbook steps (currently dumped in Tab 2).

**Card C — How to explore (only on first visit)**

- One-line hint: `Use the top navigation to inspect the graph, the agents, or ask questions.` Rendered once (session flag), dismissible.

### 5.2 Section: Graph

Purpose: show the code graph and the two "hidden truth" findings.

- **Panel 1 — Interactive Knowledge Subgraph**: PyVis visualization exactly as today (Parchment background, teal target node, ForceAtlas2), height 460px. Label: `Code graph around <function>`; caption: `Each dot is a function, incident, or decision record in FalkorDB. Drag to explore.`
- **Panel 2 (two columns)**:
  - `True expert vs. org chart` — today's expertise-centrality card. Caption: `The graph finds who actually fixed this code recently — which may differ from the nominal team lead.`
  - `Blast radius` — callers list + decision provenance. Caption: `What breaks if this change ships.`

### 5.3 Section: Agents

Purpose: show the autonomous pipeline as a story, not a log.

- **Pipeline strip** — three step cards in a row, visually connected by arrows:

  ```
  [1 Scout]  →  [2 Consolidator]  →  [3 Fixer]
  Detective     Memory librarian    Decision-maker
  ```

  Each card: agent number + name, one-word persona (the subtitle), and **only the findings that apply to the current simulation** (today's static `trace-step` blocks become data-driven from `sim`).
- **Memory cards (two columns)**:
  - `Past incidents this code caused` (episodic memory). Caption: `NexusGuard remembers outages across restarts — this is FalkorDB, not a chat history.`
  - `Required steps before merge` (procedural memory / playbook).
- Internal terms (`dev_agent_state tokens`, `blackboard`) move into an **"Advanced: how agents coordinate"** expander at the bottom.

### 5.4 Section: Copilot

Purpose: Q&A over the graph. Unchanged functionally, cleaned visually.

- Three suggestion chips (existing): `Why was this PR blocked?` / `Who is the true expert & why?` / `Show the CEO Slack promise`.
- Chat history + input, styled to Parchment (user bubbles soft-paper with Warm-Mist border; assistant messages plain on canvas).
- Copilot answers already read well — keep them, but render "Governance Finding:"-style prefixes as small teal labels instead of bold text.

### 5.5 Footer

Single centered line, Graphite 0.75rem:
`NexusGuard · Built on FalkorDB · FalkorDB Hackathon 2026`

---

## 6. Copy & Tone Rules

1. Plain English first, jargon second. Jargon may appear only after its plain-English caption.
2. Sentences over labels. "What breaks if this change ships" beats "Blast radius".
3. Numbers always carry units and meaning: `$12,000 refund outage`, not `loss_usd: 12000`.
4. Second person where natural: "This PR touches…", "We found…".
5. Jargon translation table (apply on sight):

| Internal term | User-facing wording |
|---|---|
| Blast radius | What breaks if this change ships |
| Expertise centrality | Who actually knows this code |
| Episodic memory | Past incidents |
| Procedural memory | Required steps before merge |
| Decision provenance | Where this rule came from |
| Blackboard / agent_state | How the agents coordinate (advanced) |
| Stale documentation | Docs that no longer match the code |

---

## 7. Component Catalog

### 7.1 `Card` (`.pplx-card`)
Soft-Paper surface, 8px radius, Warm-Mist border, 1rem padding. **Do:** one heading + one body idea. **Don't:** stack three data grids inside.

### 7.2 `CardLabel` (`.pplx-card-label`)
11–12px, 500, uppercase, Graphite. Sits at top of every card. Always paired with a plain-English caption directly below when the label is jargon.

### 7.3 `Pill`
Rounded chip, 0.8125rem. Variants: `pill-blocked` (red tint), `pill-conditional` (amber tint), `pill-approved` (teal tint), status pill (neutral). Icon 16px inline.

### 7.4 `PrimaryButton`
Teal filled, white text, full sidebar width. One per sidebar (Run). All other buttons are `GhostButton` (transparent, Ink text, Warm-Mist border).

### 7.5 `NavLink`
Graphite 0.875rem; active = Ink + 2px teal underline offset 6px. Hover: Ink text.

### 7.6 `Expander`
Used for anything longer than 3 lines of detail (remediation steps, agent coordination internals). Always closed by default. Title is a question or verb phrase: `What happens next`, `How agents coordinate`.

### 7.7 `StatRow`
Inline `label: value` pairs inside a card, Graphite label + Ink value, separated by 16px gaps. Max 4 stats per row.

### 7.8 States (apply to every panel)

- **Loading**: single spinner with a narrated line: `Reading FalkorDB memory graphs…` (never a bare spinner).
- **Empty**: one Graphite sentence with the fix: `No past incidents recorded for this function — a clean history.`
- **Error**: red-tinted card, one sentence + one action: `Couldn't reach FalkorDB on port 6379. Start the Docker container, then retry.`

---

## 8. Implementation Map (current `app.py` → spec)

| Current lines | Current content | Spec destination |
|---|---|---|
| 23–28 | `set_page_config` | Keep |
| 31–~560 | CSS tokens + component styles + SCENARIOS dict | Keep tokens (§1); add nav CSS (§3); keep scenarios |
| 588–632 | Sidebar | Restructure per §4 (3 groups, quiet Reset, allow toasts) |
| 636–649 | Static header | Replace with nav bar (§3) |
| 653–672 | Hero card + run buttons | Hero moves to Overview §5.1; Run stays in sidebar |
| 684–723 | Verdict card | Overview §5.1 Card B (add one-sentence "why") |
| 727–731 | `st.tabs` | Delete — replaced by nav state machine |
| 734–868 | Graph tab | Section §5.2 |
| 871–965 | Reasoning/memory tab | Section §5.3 (data-driven pipeline, internals → expander) |
| 968–1037 | Copilot tab | Section §5.4 |
| 1039–1043 | Footer | §5.5 |

**Key state change:** add `st.session_state["nav_section"]` (default `"overview"`); main panel is a single `if/elif` over it. Remove the CSS that hides `stToast`/`stNotification`.

**Out of scope for this spec:** backend (`api.py`, `tools.py`, `agents.py`, `seed.py`) — unchanged.
