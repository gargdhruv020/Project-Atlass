# Project Atlas — Architectural Design Decisions & Trade-Offs

## 1. Overview & Context

This document captures the key architectural, security, and algorithmic decisions made during the implementation of **Project Atlas**. Each decision is documented with its context, alternatives considered, chosen approach, and accepted trade-offs.

---

## 2. Decision Log

### Decision 1: LangGraph Directed Acyclic Graph (DAG) vs Cyclic ReAct Agent

* **Context**: The Copilot must reliably execute multi-step research tasks (intent routing, entitlement checks, dual retrieval, calculation, critique, escalation, and synthesis) without nondeterministic drift or runaway execution costs.
* **Options Considered**:
  1. *Unconstrained Cyclic ReAct Agent*: An LLM dynamically decides which tools to call in an open-ended loop until it decides to stop.
  2. *LangChain Sequential Chain*: A static linear sequence of prompts (`ChainA | ChainB | ChainC`).
  3. *LangGraph Directed Acyclic State Graph (Selected)*: A stateful graph (`langgraph.graph.StateGraph`) with explicit nodes, typed state (`AgentGraphState`), deterministic conditional transitions, and strictly forward-directed edges.
* **Rationale**:
  - Unconstrained ReAct agents frequently get stuck in tool-execution loops, hallucinate tool arguments, or leak unauthorized data when prompt injection attacks manipulate loop conditions.
  - Linear sequential chains cannot handle conditional branching (e.g., routing SQL aggregate queries directly to SQL tools without executing vector retrieval, or bypassing calculation nodes for factual lookups).
  - LangGraph provides mathematical loop prevention, strongly typed state propagation, per-node latency telemetry, and predictable execution paths.
* **Trade-Off Accepted**: Graph execution paths are structured and deterministic, requiring code changes to add new branches rather than relying on emergent LLM tool-selection behavior.

---

### Decision 2: Local Persistent ChromaDB vs Cloud-Hosted Vector Database

* **Context**: Semantic search over unstructured report narrative text requires vector storage.
* **Options Considered**:
  1. *Managed Cloud Vector Databases (Pinecone, Qdrant Cloud, Weaviate Cloud)*: Off-premise vector indexing with cloud API keys.
  2. *Local Ephemeral ChromaDB (In-Memory)*: ChromaDB running in RAM, rebuilding on every container restart.
  3. *Local Persistent ChromaDB on Disk (Selected)*: ChromaDB running embedded within the application process storing index files in `chroma_data/`.
* **Rationale**:
  - Enterprise market research involves proprietary, paid research reports (`R-101`, `R-103`). Storing embeddings or document chunks in public cloud vector databases introduces intellectual property leakage and external data-sovereignty compliance risks.
  - In-memory vector databases require re-embedding documents on every restart, causing unacceptable cold-start delays.
  - Persistent ChromaDB on disk provides immediate local startup, zero external API keys, zero network latency to cloud databases, and complete data isolation within the container volume.
* **Trade-Off Accepted**: Horizontal scaling across multiple worker instances requires shared network volumes or a centralized Chroma server container rather than embedded in-process storage.

---

### Decision 3: Deterministic Python Arithmetic Engine vs LLM Calculation

* **Context**: B2B market intelligence demands exact financial growth projections (CAGR compounding: $FV = BV \times (1 + CAGR)^n$ and regional sizing: $V_{\text{regional}} = V_{\text{global}} \times \text{share}$).
* **Options Considered**:
  1. *Direct LLM Generation*: Asking the LLM prompt to compute future market valuations and format the arithmetic.
  2. *LLM with Python Code Interpreter*: Allowing the LLM to write and execute arbitrary Python scripts in a sandbox.
  3. *Dedicated Pure-Python Calculator Node (Selected)*: A deterministic calculator tool ([`MarketCalculator`](file:///backend/app/tools/calculator.py)) with strict input validation, finite bounds checking, verified report forecast window boundaries, and transparent formula reporting.
* **Rationale**:
  - LLMs are probabilistic language models prone to mathematical hallucinations, rounding errors, and compounding drift ($4.21 \times 1.112^6$ can easily yield different values across runs).
  - Code interpreter sandboxes introduce severe Remote Code Execution (RCE) attack surfaces.
  - A dedicated Python module guarantees exact mathematical reproducibility, explicit assumption tagging, and enforced forecast window boundaries (refusing silent extrapolation beyond published years).
* **Trade-Off Accepted**: Calculation types are limited to pre-implemented algorithms (CAGR compounding, regional distribution). Novel financial calculations require implementing additional Python calculation methods.

---

### Decision 4: Multi-Layer Entitlement Defense-in-Depth

* **Context**: Reports in the catalog have different access tiers (`paid` vs `public`). Client `C-01` purchased `R-101` and `R-103`, while Client `C-02` only purchased `R-103`. Client `C-02` must never access `R-101` data.
* **Options Considered**:
  1. *Single-Layer Prompt System Instructions*: Instructing the LLM: "Do not tell Client C-02 anything from report R-101."
  2. *Pre-Retrieval Vector Filter Only*: Applying `{"report_id": {"$in": permitted_reports}}` during vector queries.
  3. *Three-Layer Defense-in-Depth (Selected)*:
     - **Layer 1 (Pre-Retrieval Scope)**: Relational and vector queries are filtered upfront by the client's verified permissions.
     - **Layer 2 (Hard Python Gate)**: Every retrieved vector chunk is inspected by `ClientService.check_report_access()` in Python before adding to context.
     - **Layer 3 (Post-Generation Audit)**: `CitationValidator` audits generated citations and metrics against authorized catalog records, excising any unentitled claims.
* **Rationale**:
  - Prompt-based instructions are vulnerable to prompt injection and jailbreaking.
  - Vector filtering alone fails if metadata tags are corrupted or if similarity thresholds produce loose matches.
  - Layered defense guarantees that unauthorized chunks never reach the model prompt, preventing accidental intellectual property leakage even under adversarial inputs.
* **Trade-Off Accepted**: Slight computational overhead (approximately 2–5 ms per query) due to post-retrieval verification.

---

### Decision 5: Restricted SELECT-Only MySQL Connection for Natural Language Aggregations

* **Context**: The copilot supports aggregate analytics (e.g., sector distributions, average CAGR across reports) executed over MySQL tables.
* **Options Considered**:
  1. *Shared Application Connection*: Using the standard application database user with `INSERT`/`UPDATE`/`DELETE` permissions for all tool executions.
  2. *ORM Abstraction Only*: Restricting queries to hardcoded ORM method calls without dynamic SQL.
  3. *Restricted SELECT-Only Connection + Query Whitelisting (Selected)*: Executing read-only queries using a dedicated `atlas_readonly` user, restricted to approved tables (`reports`, `market_metrics`), bound by hard row limits (`LIMIT 50`) and statement timeouts ($5\text{ seconds}$).
* **Rationale**:
  - Using a read-write database connection for NL-to-SQL creates catastrophic risks of database corruption (`DROP TABLE`, `DELETE FROM`, data alteration).
  - The combination of a physically restricted database user (enforced by MySQL engine privilege checks), regex AST mutation token blocking, and statement timeouts ensures mathematical protection against data tampering.
* **Trade-Off Accepted**: Administrative setup requires managing two database credentials (`DB_USER` and `DB_READONLY_USER`).

---

### Decision 6: Explicit Scope Disambiguation vs Automatic LLM Averaging

* **Context**: The seed catalog features divergent 2024 global smart water market valuations:
  - Report R-101: **USD 4.21 Billion** (Full System: hardware, software, services).
  - Report R-102: **USD 3.87 Billion** (Hardware endpoints only).
* **Options Considered**:
  1. *Silent Averaging*: Blending the figures into a single compromise number: $\frac{4.21 + 3.87}{2} = 4.04\text{ Billion}$.
  2. *Arbitrary Winner Selection*: Prompting the LLM to choose the "best" or "most authoritative" report.
  3. *Explicit Scope Disambiguation & Analyst Escalation (Selected)*: Displaying both numbers separately, explaining their methodological scopes, citing respective sources, and escalating to a human analyst if the user demands a definitive choice.
* **Rationale**:
  - Silent averaging creates fictitious numbers unsupported by any published methodology.
  - An AI system should not make executive business judgments between conflicting published research reports.
  - Displaying separate valuations with scope notes provides actionable transparency while preserving research integrity.
* **Trade-Off Accepted**: Users seeking a single simplistic number are presented with a nuanced comparison and an analyst escalation reference instead.

---

### Decision 7: Additive Database Migrations Preserving Existing Seed Records

* **Context**: Additional features (analyst escalation tracking, conversation history, user feedback) required new database tables and columns.
* **Options Considered**:
  1. *Database Reset / Re-creation*: Dropping and re-creating the `project_atlas` schema.
  2. *Additive Non-Destructive Migrations (Selected)*: Inspecting the existing database and creating new tables (`escalation_tickets`, `conversations`, `conversation_messages`, `user_feedback`) without altering or dropping existing rows in `clients`, `reports`, or `market_metrics`.
* **Rationale**:
  - The assignment explicitly prohibited dropping, overwriting, or recreating the reviewer's existing development database.
  - Additive migrations allow new application capabilities to function seamlessly without risking existing data.
* **Trade-Off Accepted**: Client entitlements remain stored as comma-separated text in `clients.purchased_reports` (matching legacy schema) rather than being normalized into a relational join table.

---

## 3. Architecture Decision Matrix

| Dimension | Selected Approach | Key Benefit | Alternative Rejected | Why Alternative Rejected |
| :--- | :--- | :--- | :--- | :--- |
| **Agent Orchestration** | LangGraph StateGraph | Deterministic transitions, loop prevention | ReAct loop | Vulnerable to infinite loops and injection drift |
| **Vector Indexing** | Local Persistent ChromaDB | Data sovereignty, zero external API keys | Cloud Pinecone | External IP leakage, vendor lock-in |
| **Embeddings** | ONNX MiniLM-L6-v2 | Fast local inference (~30ms), zero API cost | OpenAI Embeddings | Cloud dependency, recurring token expense |
| **Calculations** | Pure-Python Engine | Exact arithmetic, forecast boundary refusal | LLM Arithmetic | Hallucinations, rounding errors, drift |
| **Entitlements** | 3-Layer Defense-in-Depth | Zero data leaks across client tiers | Prompt-only rules | Vulnerable to prompt injection jailbreaks |
| **SQL Safety** | Dedicated `atlas_readonly` user | Hardware-enforced SELECT-only isolation | Shared DB account | Catastrophic mutation risk under NL-to-SQL |
| **Conflicting Reports** | Disambiguation + Escalation | Preserves research integrity; no fake numbers | Averaging | Fabricates ungrounded non-source figures |
| **Legacy Portal** | CodeIgniter 3 cURL Service | Clean separation of concerns; safe timeouts | Direct Python calls | Tight coupling, incompatible runtime environments |
