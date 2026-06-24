# Workflow Verification System — Logic Specification

## What This System Does

Given a workflow graph and a conversation transcript, determine whether the AI agent followed the workflow correctly. Output is a structured audit report with exact violations, metrics, and a binary pass/fail verdict.

---

## Inputs

**Workflow graph** contains two things:
- Nodes — each step the agent must perform, with an id, a type (start / end / process / decision), a label, a description of what must happen, and an x/y position
- Edges — pairs of source and target node ids defining which transitions between steps are legal

**Transcript** contains a list of turns, each with a speaker role (user or assistant), the text content, and a beginning timestamp in seconds.

---

## Stage 1 — Parse and Preprocess

**Graph parsing:**
- Confirm exactly one node has type start and at least one has type end
- Confirm every edge references node ids that exist in the nodes list
- Pre-compute all valid complete paths through the graph by traversing from start to every end node via DFS — store these as ordered lists of node ids
- Example for the NexaCare graph: valid paths are [1,2,3,5] and [1,2,3,4,5]

**Transcript preprocessing:**
- Sort all turns by beginning timestamp ascending
- Assign each turn a sequential index number starting at zero
- Relabel speaker roles: assistant becomes AGENT, user becomes PATIENT

---

## Stage 2 — Classify Nodes

Before batching, every node gets a behavior classification that determines how it will be grouped and how its transcript window is estimated.

**Anchored** — fires at a predictable fixed point in the conversation:
- The start node always fires at the very beginning
- The end node always fires at the very end
- Window for start node: first 10 percent of total call duration
- Window for end node: last 10 percent of total call duration

**Sequential** — fires after a specific predecessor node completes, in a predictable region of the transcript:
- Most process and decision nodes fall here
- Window is estimated from the node's position.y value as a ratio of the maximum position.y across all nodes, applied to the total transcript duration, with a 15 percent buffer on each side

**Conditional** — fires only when a specific condition occurs, could appear anywhere in the transcript:
- Any node whose description contains words like: error, unclear, difficulty, technical, retry, repeat
- Receives the full transcript rather than a windowed slice

---

## Stage 3 — Build Batches

**Goal:** minimize the number of LLM calls and the number of transcript tokens sent per call.

**Rule 1 — Separate conditional nodes:**
All conditional nodes go into their own batch group and always receive the full transcript. They are never mixed with anchored or sequential nodes.

**Rule 2 — Group anchored and sequential nodes by window overlap:**
- Sort these nodes by their estimated window start time ascending
- Walk through them in order, greedily building batches
- Two nodes belong in the same batch if their estimated windows overlap by at least 50 percent of the smaller window
- A batch is closed and a new one opened when either the window no longer overlaps or the batch reaches the maximum size of 3 nodes

**Rule 3 — Transcript slice per batch:**
- For non-conditional batches: the transcript slice is all turns that fall within the union of all member node windows, plus a 30 second buffer on each side
- For conditional batches: the full transcript

**Result for the NexaCare example:**
- Batch A: node 1 only, transcript turns from t=0 to t=30
- Batch B: nodes 2, 3, 5, transcript turns from t=340 to t=500
- Batch C: node 4 only, full transcript
- Total: 3 LLM calls instead of 5

---

## Stage 4 — LLM Extraction

**One API call per batch.** The LLM's only job is to find evidence. It does not decide pass or fail.

**What is sent to the LLM:**

System instruction — kept short and static across all calls:
- You are a strict clinical compliance auditor
- Default assumption is that a requirement was not met unless explicit verbatim evidence exists
- Partial completion does not count
- Patient volunteering information unprompted does not satisfy the agent's obligation to collect it
- Return only JSON, no preamble

User message — constructed per batch:
- The transcript slice, with each turn labeled by index, speaker, and timestamp
- For each node in the batch: its id, label, full description, and 2 auto-generated negative examples
- The exact JSON schema to return

**Negative example generation:**
For each node, programmatically extract the key required actions from the description and negate them. For example, if the description says collect full name and date of birth, the negatives are: collecting name only without date of birth does not satisfy this, and patient stating their name without being asked does not satisfy this. Cap at 2 negatives per node to control token usage.

**What the LLM returns per node:**
- For each sub-requirement within the node: whether it was satisfied, the exact quote from the transcript, the timestamp of that quote, which speaker said it, a confidence level of high or low, and the reasoning
- A top-level node_satisfied opinion and confidence level
- The primary evidence quote and its timestamp

**Token minimization:**
- System prompt is static — node definitions never go in the system prompt
- Transcript is sliced to only the relevant window — never the full transcript for sequential nodes
- Output schema is tight — only the fields listed above, nothing else
- Max output tokens capped at 1000 per call
- Batches run in parallel so wall clock time does not multiply

---

## Stage 5 — Quote Verification

Every quote returned by the LLM goes through three checks before any verdict is made. This is the hallucination firewall. No LLM is involved — these are simple programmatic checks.

**Check 1 — Does the quote exist verbatim in the transcript?**
The exact string the LLM returned must appear as a substring within one of the transcript turn content fields. If it does not exist: force the sub-requirement to unsatisfied regardless of what the LLM said, and mark the node as hallucination-forced.

**Check 2 — Was it spoken by the right speaker?**
Find the turn containing the quote. Confirm the turn's speaker matches the expected speaker for this sub-requirement (AGENT or PATIENT). If mismatch: force unsatisfied.

**Check 3 — Is the timestamp consistent?**
Find the turn containing the quote. Confirm the LLM's claimed timestamp is within 1 second of the turn's actual beginning timestamp. If inconsistent: correct the timestamp to the actual value. Do not fail the quote for timestamp inconsistency alone — just correct it.

**Confidence handling:**
If any sub-requirement returned confidence low, mark the entire node as requiring human review. These nodes are not auto-passed and not auto-failed. They are excluded from edge traversal ordering and flagged in the output for a human to review.

---

## Stage 6 — Rule Engine

Each node is evaluated deterministically against its definition. No LLM is involved. The LLM's node_satisfied opinion is never used — the rule engine recomputes it independently from the verified evidence.

**Start node rules:**
- Primary quote must have passed quote verification
- The verified timestamp must equal the beginning of the very first AGENT turn in the transcript
- If the agent said anything before the introduction: order violation

**End node rules:**
- Primary quote must have passed quote verification
- The verified timestamp must be later than every other satisfied node's verified timestamp
- If any other node fired after the end node: order violation

**Process node rules:**
- Each sub-requirement that failed quote verification gets a required field not collected violation (V-04)
- If the primary quote was hallucination-forced: required node not found violation (V-01)

**Decision node rules:**
- Same as process node, plus:
- The branch the agent took must match the evidence collected — for example if the patient said they are returning but the agent collected a contact number (new patient field), that is an incorrect branch violation (V-05)

**Unauthorized step detection:**
- Identify clusters of AGENT turns that contain no verified quote from any node in the workflow
- If such a cluster spans more than 60 seconds with no verified evidence: flag as unauthorized step (V-06)
- This catches the complaint-handling detour in the NexaCare transcript

---

## Stage 7 — Edge Traversal Check

**Input:** all nodes that passed the rule engine and are not flagged for human review, sorted by verified timestamp ascending.

**This produces the actual execution sequence.** For the NexaCare transcript: [1, 4, 2, 3, 5]

**Check 1 — Are consecutive transitions valid?**
For each consecutive pair in the actual sequence, look up whether an edge exists from the first to the second in the graph's edge list. If no such edge exists: invalid edge traversal violation (V-02).

**Check 2 — Does the sequence match a valid path?**
Remove conditional nodes from the actual sequence. Check whether the cleaned sequence matches any of the pre-computed valid paths. If it matches: valid_path_matched is true. If it does not: valid_path_matched is false.

**Check 3 — Are any required nodes missing?**
For the closest matching valid path, identify any node that appears in the path but not in the actual sequence. If that node is not conditional: required node not found violation (V-01).

**Check 4 — Order violations:**
For each node, look up which nodes must precede it according to the graph. If any predecessor has a verified timestamp greater than this node's verified timestamp: order violation (V-03). Record the timestamp of the earliest order violation as first_deviation_point.

---

## Stage 8 — Metrics

All metrics are computed from the outputs of the previous stages. No additional processing or LLM calls.

**Node completion rate** — how many nodes were satisfied divided by total nodes in the graph

**Critical node pass** — boolean: true only if the start node and all end nodes were satisfied

**Edge accuracy** — how many consecutive transitions in the actual sequence were valid edges divided by total transitions taken

**Valid path matched** — boolean: true only if the actual sequence (minus conditional nodes) exactly matches one of the pre-computed valid paths

**Order violation** — boolean: true if any V-03 violation was raised

**First deviation point** — the timestamp of the earliest V-02 or V-03 violation, null if none

**Sub-requirement coverage** — total sub-requirements satisfied across all process and decision nodes divided by total sub-requirements required across those same nodes

**Low confidence count** — number of nodes flagged for human review due to low confidence extractions

**Unauthorized steps** — number of V-06 violations raised

---

## Stage 9 — Final Verdict

**PASS requires all three conditions to be true simultaneously:**
- Zero critical severity violations (V-01, V-02, V-03, V-05 are all critical)
- valid_path_matched is true
- critical_node_pass is true

**FAIL if any one of those three conditions is false.**

There is no partial score. There is no weighted compliance percentage. In healthcare, a workflow was either followed or it was not.

**The output report contains:**
- The binary result: PASS or FAIL
- The full list of violations with code, severity, description, node id or edge, and timestamp
- All eight metrics
- The actual sequence of steps taken ordered by timestamp
- The required sequence from the matching valid path
- Whether human review is required

---

## Key Design Principles

**LLM touches only one thing:** converting raw conversation text into structured evidence with quotes and timestamps. Every decision — pass, fail, violation, metric — is made by deterministic rule-based logic downstream.

**Quotes are the ground truth:** if a quote cannot be found verbatim in the transcript, the claim is rejected. The system never infers, approximates, or semantically matches.

**Ordering is enforced by timestamps:** the beginning field on each transcript turn gives a physical anchor for every claim. The edge checker sorts by these timestamps — not by the LLM's narrative understanding of sequence.

**Conditional nodes are never ordered against sequential nodes:** error handling can legitimately fire at any point. The system knows this and excludes conditional nodes from path matching, treating them as floating evidence rather than sequence-breaking violations.

**Human review is a gate, not a score:** low confidence extractions do not contribute to any metric. They are quarantined until a human confirms or rejects them. This prevents uncertain LLM outputs from silently influencing a compliance verdict in a healthcare context.