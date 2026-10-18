# NexusGuard — Product Walkthrough & Pitch Guide

> **One sentence:** NexusGuard is an AI system that automatically stops dangerous code changes by remembering what went wrong in the past, knowing who actually understands the code, and tracing why the code exists in the first place.

---

## The Problem (Explain This First)

Imagine you're a developer at a company called **Acme Corp**. You open a file called `applyDiscount()` and see a weird `if-statement` that looks like dead code. So you delete it and submit a Pull Request to clean things up.

**What you don't know:**

1. **That "dead code" is load-bearing.** It gives Client X a special 15% discount that the CEO personally promised them on Slack 18 months ago. Deleting it will overbill them.

2. **This exact mistake already happened.** Six months ago, another developer deleted the same line. It caused a **$12,000 refund outage** before anyone noticed.

3. **The person who wrote it left the company.** Bob, who built this code, quit in June. The official "team lead" (Asha) has never actually touched this file. The only person who truly understands it is Priya from a completely different team — she fixed it twice during emergencies.

**No existing AI code review tool knows any of this.** They only look at the code diff. They can't see the Slack promise, the past outage, or who really knows the code.

**NexusGuard sees all of it** — because it stores everything in a connected graph database (FalkorDB) and uses AI agents to reason over it.

---

## How It Works (The Simple Version)

Think of NexusGuard as a **company memory brain** that connects four things most tools look at separately:

```
    CODE              PEOPLE            CONVERSATIONS        HISTORY
 (functions,       (who wrote it,      (Slack messages,     (past outages,
  dependencies)     who reviewed it)    Jira tickets)        safe procedures)
       \                |                   /                    /
        \               |                  /                    /
         └──────────────┴─────────────────┴────────────────────┘
                              │
                     ┌────────┴────────┐
                     │    FalkorDB     │
                     │  (Graph Brain)  │
                     └────────┬────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              Scout Agent         Fixer Agent
            (Finds the risk)    (Takes the action)
```

When a developer opens a Pull Request, three autonomous AI agents work together across the FalkorDB Blackboard:

### Agent 1: Scout (The Detective)
- **"What could break?"** → Traces all the functions that depend on the changed code (the "blast radius").
- **"Why does this code exist?"** → Finds the original Slack message or Jira ticket that explains the decision.
- **"Has this gone wrong before?"** → Checks if a past outage was caused by touching this code.

### Agent 2: Consolidator (The Memory Synthesizer & Cross-Tenant Bridge)
- **"What past lessons apply?"** → Synthesizes episodic incidents, safe procedures, and semantic contracts.
- **"Does this cross tenant boundaries?"** → Safely coordinates cross-repo dependencies without exposing internal code.
- **"How do agents communicate?"** → Posts working memory handoff tokens to the `dev_agent_state` Blackboard graph.

### Agent 3: Fixer (The Decision-Maker)
- **"Who should review this?"** → Computes recency-decay expertise scores to assign who *actually* knows the code.
- **"What are the safe steps?"** → Pulls up the safe procedure checklist created after the last outage.
- **"Block or approve?"** → Automatically blocks dangerous merges and flags stale documentation.

---

## Live Demo: 5 Real Scenarios

### Scenario 1: "The Innocent Cleanup That Breaks Billing"

> **PR-904:** *"Remove dead code: applyDiscount"*
> **Developer thinks:** "This if-statement does nothing. Let me clean it up."

**What NexusGuard finds:**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | 6 functions depend on this code, across 2 teams (Checkout + Payments) |
| 💬 Why does this code exist? | CEO promised Client X a 15% discount on Slack `#sales` on March 12 |
| ⚠️ Past outages | Incident I-007: Last time someone deleted this → **$12,000 refund outage** |
| 👤 Who really knows this? | Bob wrote it (but he quit). Priya fixed it twice and is still here |
| 📄 Documentation | "Discount Logic Runbook" is now outdated — flagged as stale |

**NexusGuard's Decision:** 🛑 **MERGE BLOCKED**
- Assigned **Priya** as reviewer (not Asha, the "official" lead who never touched this code)
- Displayed the 4-step safe migration checklist from the last outage

---

### Scenario 2: "The Payment Webhook That Double-Charges"

> **PR-512:** *"Make Stripe invoice retries async"*
> **Developer thinks:** "This will make webhooks faster."

**What NexusGuard finds:**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | Stripe invoicing is connected to calculateTotal and checkout |
| 💬 Why does this code exist? | Nina wrote on Slack `#payments`: "Stripe requires strict idempotency on retries" |
| ⚠️ Past outages | Incident I-019: A retry race condition caused **$8,500 in duplicate charges** |
| 👤 Who really knows this? | Nina is the top expert (14 commits). Priya is second (5 commits) |

**NexusGuard's Decision:** ⚠️ **CONDITIONAL APPROVAL**
- Must run shadow billing replay before merge
- Must follow the 3-step Stripe deployment playbook

---

### Scenario 3: "The Harmless UI Change"

> **PR-108:** *"Add seasonal banner animation to cart page"*
> **Developer thinks:** "Just a fun holiday banner."

**What NexusGuard finds:**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | Zero other functions depend on renderCart |
| 💬 Why does this code exist? | No decisions or promises attached |
| ⚠️ Past outages | No incidents ever linked to this function |
| 👤 Who really knows this? | Dev has 8 commits, no conflict |

**NexusGuard's Decision:** ✅ **AUTO-APPROVED**
- No risks detected. No special reviewer needed. Merge away.

*This scenario proves NexusGuard doesn't cry wolf — it only blocks when there's real evidence.*

---

### Scenario 4: "The Auth Change in a Different Department"

> **PR-401:** *"Upgrade JWT token verification to RS256"*
> **Developer thinks:** "Better security algorithm."

**What NexusGuard finds (in the acme_auth tenant — completely separate graph):**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | rotateSigningKey depends on verifyJwtToken |
| 💬 Why does this code exist? | Alice posted on `#security`: "5-minute key rotation tolerance required" |
| ⚠️ Past outages | Incident I-010: Premature key expiry → **20-min enterprise SSO outage ($5,000)** |
| 👤 Who really knows this? | Alice is the top expert (25 commits) |

**NexusGuard's Decision:** 🛑 **MERGE BLOCKED**
- Auto-assigned **Alice** as reviewer
- Enforced the 4-step zero-downtime key rotation procedure

*This scenario proves multi-tenant isolation: the auth team's memory is completely separate from checkout.*

---

### Scenario 5: "The Batch Refund Optimization"

### Scenario 5: "The Batch Refund Optimization"

> **PR-770:** *"Batch refund queue processing"*
> **Developer thinks:** "Group refunds into bulk SQL transactions for speed."

**What NexusGuard finds:**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | refundOrder calls applyDiscount (which has its own risk history) |
| ⚠️ Past outages | Linked through applyDiscount to the $12k incident |
| 👤 Who really knows this? | Priya has 14 commits on refundOrder |

**NexusGuard's Decision:** ⚠️ **CONDITIONAL APPROVAL**
- Auto-assigned **Priya** as reviewer
- Required expert sign-off before merge

---

### Scenario 6: "The GDPR Purge Without Audit Log" (Data Tenant)

> **PR-330:** *"Compliance: Cascade purge customer PII in hardDeleteAccount"*
> **Developer thinks:** "Speed up user deletions by skipping cold storage archival."

**What NexusGuard finds (in `acme_data` tenant):**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | hardDeleteAccount triggers auditLogEvent |
| 💬 Why does this code exist? | Slack `#legal-compliance`: Marcus posted "Article 17 GDPR requires verifiable audit trail before deleting rows" (Decision D-005) |
| ⚠️ Past outages | Incident I-033: Unlogged customer deletion caused **$45,000 regulatory fine** |
| 👤 Who really knows this? | Marcus (Data Governance Lead, 15 commits) |

**NexusGuard's Decision:** 🛑 **MERGE BLOCKED**
- Blocked: Direct schema purge violates Article 17 audit requirements
- Auto-assigned **Marcus** (Data Protection Officer)
- Enforced 3-step GDPR compliance purge playbook P-005

---

### Scenario 7: "The Redis Sliding Window Memory Hazard" (Infra)

> **PR-610:** *"Reliability: Tighten sliding window threshold in rateLimitRedisBucket"*
> **Developer thinks:** "Reduce rate limit window from 60s to 10s for better protection."

**What NexusGuard finds:**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | rateLimitRedisBucket protects the checkout cluster |
| 💬 Why does this code exist? | Slack `#infra-warroom`: Elena warns "Victor originally wrote Redis token bucket with Lua; changing window evicts checkout keys" |
| ⚠️ Past outages | Incident I-025: Lua memory spike evicted session keys on Black Friday (**$28,000 loss**) |
| 👤 Who really knows this? | Victor (25 commits) left company; Elena (SRE Lead, 8 recent commits) is true active expert |

**NexusGuard's Decision:** ⚠️ **CONDITIONAL APPROVAL**
- Flags Victor as departed author and detects knowledge gap
- Auto-assigns active SRE Lead **Elena**
- Demands 5,000 req/sec benchmark verification per playbook P-004

---

### Scenario 8: "The Crypto Cipher IV Breaking Legacy Data" (Crypto)

> **PR-350:** *"Security: Upgrade AES encryption salt derivation in encryptPiiField"*
> **Developer thinks:** "Improve cryptographic salt generation."

**What NexusGuard finds (in `acme_data` tenant):**

| What the Agent Checked | What It Found |
|---|---|
| 🔍 Blast radius | encryptPiiField is called by exportUserData across customer profiles |
| 💬 Why does this code exist? | Leila posted on `#crypto-security`: "Rotating AES-GCM IV broke 4,000 legacy records" (Decision D-006) |
| ⚠️ Past outages | Incident I-042: Decryption crash across 4,200 profiles (**$18,000 loss**) |
| 👤 Who really knows this? | Leila (22 commits) |

**NexusGuard's Decision:** ⚠️ **CONDITIONAL APPROVAL**
- Auto-assigns **Leila**
- Demands dual-cipher reading verification with key version header per playbook P-006

---

## What Makes This Special (The Pitch Points)

### 1. It Remembers (Track 02: Agent Memory)
Most AI tools have no memory. NexusGuard stores three types of memory in FalkorDB:
- **Episodic Memory:** "This exact change caused a $12,000 outage on March 2nd (I-007) or $45,000 fine (I-033)"
- **Procedural Memory:** "Here are the safe playbook checklists to follow before merging"
- **Semantic Memory:** "Living runbooks and architectural contracts governing each function"

### 2. It Knows Who Really Knows (Track 03: Company Brain)
The org chart says Asha or official owners lead this code. But the graph reveals:
- Bob wrote 22 commits (but he left the company in June 2025)
- Priya fixed it twice during emergencies and is active today
- Victor wrote the Redis bucket (departed); Elena is the active SRE expert
NexusGuard uses **recency-decay graph centrality** to assign the person who actually understands the code.

### 3. It Acts, Not Just Advises (Track 01: Agents That Act)
NexusGuard doesn't just generate a report. It:
- **Blocks** the dangerous PR directly in the graph state
- **Assigns** the verified expert as reviewer
- **Flags** outdated documentation as stale
- **Proves provenance:** surfaces the exact Slack message, Jira ticket, and postmortem incident

---

## 3-Minute Judge Winning Demo Flow

### Act 1: The Hook (30 seconds)
1. Open **http://localhost:8501** featuring the clean **Scholar's Parchment UI** (`#faf8f5`) with minimalist floating nodes.
2. Say: *"Every engineering company has load-bearing legacy code that nobody dares touch. Why? Because the context is lost across Slack threads, departed engineers, and past outages. When an engineer opens a PR today, GitHub and Copilot have no idea what will break. NexusGuard is an autonomous governance brain backed by FalkorDB that fixes this."*

### Act 2: The Critical Block (60 seconds)
1. Select **Scenario 1: [CRITICAL // BLOCKED] PR-904 -> applyDiscount** in the sidebar.
2. Click **"EXECUTE NEURAL GRAPH SIMULATION"**.
3. Point to the **Status Banner:** 🛑 **HIGH RISK // BLOCKED**.
4. Open the **Synaptic Thinking Trace Tab:**
   - Show **Scout-Agent**: traversed 7 callers across 3 teams.
   - Show **Decision Provenance**: caught CEO Sarah's promise on Slack `#sales` from 2025 for Client X.
   - Show **Episodic Memory**: identified Incident I-007 ($12,000 outage from doing this exact refactor).
   - Show **Fixer-Agent**: caught that original author Bob quit, so it assigned **Priya** (the active expert) instead of the nominal lead.

### Act 3: Multi-Tenant & Compliance (45 seconds)
1. Select **Scenario 6: [CRITICAL // BLOCKED] PR-330 -> hardDeleteAccount (acme_data)**.
2. Click **"EXECUTE NEURAL GRAPH SIMULATION"**.
3. Explain: *"NexusGuard isn't a monolith. Notice how it seamlessly switched to our `acme_data` tenant memory graph. It caught a GDPR Article 17 non-compliance violation (D-005) that previously cost $45,000 in incident I-033, and assigned Data Protection Officer Marcus."*

### Act 4: Non-Crying Wolf & Copilot Chat (45 seconds)
1. Switch to **Scenario 3: [LOW // AUTO-APPROVED] PR-108 -> renderCart**.
2. Click simulate: point out ✅ **SAFE // AUTO-APPROVED**.
   - Explain: *"NexusGuard doesn't slow developers down. If there are no downstream callers, no contractual decisions, and no past outages, it auto-approves instantly."*
3. Click the **Nexus Copilot Console Tab**:
   - Type: *"Why was PR-904 blocked?"* or *"Who knows about applyDiscount?"*
   - Show the instant graph-grounded response.
4. Conclude: *"In under 2 seconds, FalkorDB turns scattered Slack messages and git history into autonomous engineering safety."*

---

## How to Run Locally

### Step 1: Start FalkorDB (Docker)
```bash
docker run -p 6379:6379 -p 3000:3000 -d --name falkordb falkordb/falkordb:latest
```

### Step 2: Seed the multi-tenant graphs
```powershell
.\.venv\Scripts\python.exe seed.py
```

### Step 3: Launch the Streamlit dashboard
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
Open **http://localhost:8501** in your browser.

---

## The 90-Second Elevator Pitch

> *"When a developer opens a Pull Request, today's AI tools only see the code diff. They don't know that the CEO promised a client a custom pricing deal on Slack. They don't know that deleting this exact line caused a $12,000 outage six months ago. They don't know that the person who wrote it left the company.*
>
> *NexusGuard connects all of this in FalkorDB — code, people, conversations, and incident history — into one living graph. Two AI agents traverse this graph in real time: one finds the risk, the other takes action. It blocks dangerous merges, assigns the person who actually knows the code, and surfaces the exact Slack message and Jira ticket that explain why this code exists.*
>
> *It doesn't just advise. It acts. And it remembers."*

