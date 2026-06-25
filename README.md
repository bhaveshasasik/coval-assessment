# Workflow Verification System

> A deterministic compliance verification system that evaluates whether conversational AI agents correctly follow defined workflows.

**Tech Stack:** FastAPI + Anthropic Claude (backend) | Next.js + TypeScript (frontend)

## Prerequisites

**System Requirements:**
- Python 3.10+ | Node.js 20.0.0+ | npm 10.0.0+
- [Anthropic API Key](https://console.anthropic.com/)

```bash
# Verify versions
python3 --version && node --version && npm --version
```

## 🚀 Quick Start

```bash
# Copy environment template and add your API key
cp .env.example .env
# Edit .env and set: ANTHROPIC_API_KEY=sk-ant-your-key-here

# One-command startup (both backend + frontend)
./start.sh

# Access: http://localhost:3000
# API Docs: http://localhost:8000/docs

# To stop all services:
./stop.sh
```

## Usage

Upload workflow + transcript files at [http://localhost:3000](http://localhost:3000) → Run Verification → View results

**Sample Files:** [Workflow](examples/nexacare_workflow.json) | [Transcript](examples/nexacare_transcript.json)

**Full setup instructions:** See [docs/SETUP.md](docs/SETUP.md) for detailed guide including troubleshooting.

**Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system diagram and data flow.


---

## Approach

**Problem:** Given a workflow graph (expected flow) and conversation transcript (actual conversation), determine if the agent correctly followed the workflow with a PASS/FAIL verdict.

**Solution:** 9-stage hybrid pipeline combining:
- **LLM-powered evidence extraction** - for semantic understanding
- **Quote verification firewall** - to eliminate hallucinations  
- **Deterministic rule engine** - for unbiased pass/fail decisions

**Why hybrid?** Pure LLM is unreliable (hallucinations), pure string matching is inflexible (misses semantic equivalence). Our approach: LLM understands meaning → quotes verified against transcript → deterministic rules decide verdict.

---

## Key Design Decisions

### 1. **Mapping Conversation to Nodes**

**Decision:** LLM extracts sub-requirements + quotes → Verify quotes verbatim → Rules evaluate

**Reasoning:**
- Break vague descriptions ("Collect patient info") into atomic requirements (Name, DOB, Phone)
- LLM extracts evidence with exact quotes from transcript
- 3-check verification: quote exists, correct speaker, timestamp match (±1s)
- Deterministic rules: node satisfied only if ALL sub-requirements have verified quotes

**Example:**
```
Node: "Collect name and DOB"
✓ "Your full name?" - VERIFIED at t=396.58
✓ "Date of birth?" - VERIFIED at t=402.12
→ Node SATISFIED
```

### 2. **Defining "Correct" Traversal**

**Decision:** Valid path matching + edge validation + order enforcement

**Criteria:**
1. Execution sequence matches at least one valid path through graph
2. Every transition A→B exists in workflow edges
3. Prerequisites completed before dependent nodes
4. START and all END nodes satisfied

**Why not simpler?** Just visiting all nodes allows random jumping. Just following edges allows wrong order.

### 3. **Handling Edge Cases**

| Case | Approach | Severity |
|------|----------|----------|
| **Skipped Node** | V-01 violation, immediate FAIL | Critical |
| **Invalid Edge** | V-02 violation, immediate FAIL | Critical |
| **Partial Completion** | Node NOT satisfied if any sub-requirement missing | Critical |
| **Repeated Node** | Take first occurrence, ignore repeats | None |
| **Interruptions** | V-06 violation, track duration | Minor |

**Interruption example:**
```
AGENT: "Thank you for—"
PATIENT: "Stop, I need to reschedule"
→ Node 1 still satisfied (agent recovered)
→ V-06 minor violation logged
```

### 4. **Metrics Design**

**Decision:** 8 metrics + binary verdict

| Metric | Purpose |
|--------|---------|
| Node Completion Rate | Coverage (satisfied / total) |
| Critical Node Pass | START + END satisfied? |
| Edge Accuracy | Valid transitions / total |
| Valid Path Matched | Sequence matches valid path? |
| Order Violation | Dependencies broken? |
| First Deviation Point | When did failure occur? |
| Sub-Requirement Coverage | Granular completeness |
| Low Confidence Count | Needs human review? |

**Binary Verdict:** `PASS = zero critical violations` | `FAIL = any critical violation`

**Why binary?** Compliance use cases need clear pass/fail, not scores.

### 5. **Output Structure**

**Decision:** Structured JSON with verdict, violations, metrics, and node-level evidence

**Format:** See [docs/example_output.json](docs/example_output.json)

**Key fields:**
- `result`: "PASS" | "FAIL"
- `violations[]`: Code (V-01 to V-06), severity, description, timestamp
- `metrics{}`: All 8 metrics from above
- `node_results[]`: Status, evidence quote, verification timestamp per node

**Why?** Enables CI/CD gates, audit trails, and human review workflows.

---

**Created by:** Bhavesha  
**Version:** 1.0.0  
**Date:** June 24, 2026
