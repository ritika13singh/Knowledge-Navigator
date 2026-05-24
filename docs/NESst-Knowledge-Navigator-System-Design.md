# NESsT AI-Powered Knowledge Navigator — System Design

System design for the **NESsT Knowledge Navigator** prototype, correlating the [project brief](04_21_23.jpg) with the application's RAG + LLM architecture and defining components and implementation approach.

---

## 1. Context and Requirements Mapping

### 1.1 From the NESsT Project Brief


| Brief section       | Requirement                                                                                                                                       | System design implication                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Organization**    | NESsT: 28+ years of institutional knowledge; mission-driven impact investing                                                                      | Single, searchable knowledge graph over all content types                                                 |
| **Challenge**       | Reports, manuals, case studies, notes, policies, training records, learnings; manual search; retrieval by “who created it” or “where it’s stored” | Content-based semantic search; RAG over ingested documents; metadata + full-text + vectors                |
| **Opportunity**     | Faster onboarding; no missed insights (e.g. donor feedback); cross-variable analysis, cause–effect, trends                                        | Thematic Q&A, summarization, analytics API, and (later) trend/relationship extraction                     |
| **Desired outcome** | ≥60% reduction in time spent searching; actionable, thematically-organized answers; foundation for a **public-facing** resource                   | Measurable search-time metric; RAG + chat API; internal vs public access model; content curation pipeline |


### 1.2 API patterns

The Knowledge Navigator uses a standard RAG + LLM pattern:

- **RAG insert** → Ingest NESsT documents (PDF, text, CSV) into a searchable index.
- **RAG retrieve** → Natural-language queries returning relevant chunks for answers.
- **LLM chat** → Anthropic Messages API for grounded Q&A over retrieved context.
- **File formats** → PDF, text, CSV (comma-separated); defines the initial ingestion surface; DOCX/HTML can be converted to text or PDF in the pipeline.

The Navigator system design **adopts these patterns** and adds NESsT-specific ingestion, access control, metrics, and public-layer design.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USERS & CLIENTS                                      │
├──────────────────────────────┬────────────────────────────────────────────────────┤
│  Internal (staff)            │  External (future public)                          │
│  • Web app                   │  • Public portal / API                              │
│  • API clients               │  • Curated content only                             │
└──────────────┬───────────────┴────────────────────┬───────────────────────────────┘
               │                                    │
               ▼                                    ▼
┌──────────────────────────────┐    ┌──────────────────────────────────────────────┐
│  GATEWAY / BFF               │    │  PUBLIC API (read-only, curated)             │
│  • Auth (Bearer)             │    │  • Scoped key or token                       │
│  • Rate limit                │    │  • Thematic / best-practices only            │
└──────────────┬───────────────┘    └──────────────────────┬───────────────────────┘
               │                                            │
               ▼                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        KNOWLEDGE NAVIGATOR CORE                                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │ RAG Insert  │   │ RAG Retrieve│   │ Chat / Q&A  │   │ Analytics / Themes  │   │
│  │ (ingest)    │   │ (semantic)  │   │ (LLM)       │   │ (optional)          │   │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────────┬──────────┘   │
│         │                 │                 │                      │              │
│         └─────────────────┴─────────────────┴────────────────────┘              │
│                                    │                                              │
│                                    ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │  Vector store + search index + (optional) metadata DB                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
               ┌─────────────────────────┼─────────────────────────┐
               ▼                         ▼                         ▼
┌──────────────────────────┐ ┌──────────────────────┐ ┌──────────────────────────┐
│  ORCHESTRATOR (n8n)      │ │  SOURCE DATA         │ │  OBSERVABILITY            │
│  • Trigger: webhook /    │ │  • Reports, manuals │ │  • Search-time metrics    │
│    schedule / manual     │ │  • Case studies      │ │  • Query logs (no PII)    │
│  • Coordinates ingest    │ │  • Policies, notes  │ │  • Alerts                 │
│  • Optional: approval   │ │  • Training records  │ │  • 60% target tracking    │
└──────────────┬───────────┘ └──────────┬───────────┘ └──────────────────────────┘
               │                         │
               ▼                         │
┌──────────────────────────┐            │
│  INGESTION PIPELINE      │◄───────────┘
│  • Normalize (PDF/TXT/   │  (files from Drive, uploads)
│    CSV, future: DOCX)    │
│  • Chunk + embed         │
│  • Metadata extraction   │
└──────────────────────────┘
```

---

## 3. Component Specification

### 3.1 Data Ingestion (aligned with Developer Guide RAG Insert)

**Requirement (brief):** “Reports, methodology manuals, investment case studies, strategic notes, policies, training records, learnings.”


| Aspect                | Specification                                                                                                                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Reference API**     | `POST /rag/insert/file`, multipart upload. Implemented in `backend/services/rag_service.py`.                                                      |
| **Formats (initial)** | PDF, text, CSV (comma-separator only) per developer guide; extend pipeline to accept DOCX/HTML via server-side conversion to text or PDF.                                                                           |
| **Pipeline steps**    | (1) Validate type/size → (2) Extract text (and metadata where possible) → (3) Chunk for embedding → (4) Call RAG insert or equivalent internal ingest API → (5) Store metadata (source, date, theme) for filtering. |
| **Metadata**          | At least: source file name, upload/ingest date, optional theme/category; support for “internal only” vs “eligible for public” for future public layer.                                                              |


**Developer guide alignment:** Use the same `insert_file()`-style client against the Navigator’s ingest endpoint (or the same backend contract), so existing scripts can target NESsT’s instance with a different base URL and key.

### 3.2 Search & Retrieval (aligned with Developer Guide RAG Retrieve)

**Requirement (brief):** “Faster, deeper, more consistent access”; “reduce time spent searching by at least 60%”; “actionable, thematically-organized answers.”


| Aspect            | Specification                                                                                                                                                                                                                                                    |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Reference API** | `POST /rag/retrieve`, JSON body with prompt (and optional filters). Implemented in `backend/services/rag_service.py`.                                                                                    |
| **Semantics**     | Natural-language prompt; backend returns relevant chunks (and optionally themes/sources). Thematic organization can be implemented by: (a) metadata filters (theme/category), (b) prompt instructions (“group by theme”), or (c) a separate classification step. |
| **Metrics**       | Log query latency and (where possible) “time to first useful result” or “session-to-answer time”; baseline current manual search time, then track improvement toward ≥60% reduction.                                                                             |


**Developer guide alignment:** `rag_retrieve(prompt)` pattern applies directly; add optional parameters (e.g. `theme`, `date_range`, `internal_only`) in the request body as the API evolves.

### 3.3 Chat / Q&A and “Actionable Answers”

**Requirement (brief):** “Actionable, thematically-organized answers to internal queries.”


| Aspect                    | Specification                                                                                                                                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Flow**                  | User question → RAG retrieve (get relevant chunks) → LLM with chunks as context → structured answer (and optional themes/sources).                                                                                                                |
| **API**                   | Either: (1) Single “chat” or “query” endpoint that runs retrieve + LLM internally, or (2) Client calls RAG retrieve then a separate chat/completion endpoint (as in developer guide’s “simple prompt” pattern with retrieved text in the prompt). |
| **Thematic organization** | Answers can include theme tags or a short “themes” section; optionally support filter-by-theme in the request.                                                                                                                                    |


**Developer guide alignment:** “Using documents without RAG” is for one-off/small context; for the Navigator, **always use RAG** for large institutional content and pass retrieved context into the LLM prompt to stay within token limits and ensure traceability.

### 3.4 Internal vs Public Access (future)

**Requirement (brief):** “Lay the groundwork for a public-facing resource” for social enterprises, beneficiaries, and the public.


| Aspect                 | Specification                                                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Internal API**       | Full RAG insert + retrieve + chat; Bearer token; access to all ingested content; rate limits and audit logging.                                                                       |
| **Public API (later)** | Read-only; separate base path or subdomain; scoped API key or token; only documents/flags marked “public” or “curated”; thematically filtered (e.g. best practices, lessons learned). |
| **Data model**         | Metadata field per document: `visibility: internal                                                                                                                                    |


**Developer guide alignment:** Same auth pattern (Bearer); different keys and scopes for internal vs public; public endpoint may only expose a subset of retrieve/query operations and pre-curated content.

### 3.5 Analytics, Trends, and “Cross-Variable Analysis” (optional / later)

**Requirement (brief):** “Cross-variable analysis,” “cause-effect relationships,” “detect trends.”


| Aspect                  | Specification                                                                                                                                                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Phase 1 (prototype)** | Focus on RAG + Q&A and search-time metric; analytics can be “manual” (staff querying the Navigator with analytical questions).                                                                                                             |
| **Phase 2**             | Dedicated analytics API or module: structured queries over metadata (e.g. by year, program, region); optional integration with exported CSV/structured data; trend and correlation work can use the same RAG store plus structured tables. |


No change to the core developer-guide-style RAG APIs; analytics is an additional layer that may consume the same indexed content and metadata.

### 3.6 Orchestration (n8n recommended for prototype)

**Requirement (brief):** Reliable ingestion of many documents; optional scheduled syncs; repeatable pipelines; room for human steps (e.g. curation).


| Need                     | Description                                                                                                             |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| **Ingestion workflows**  | Multi-step: trigger (upload / folder watch / schedule) → validate → extract text → chunk → RAG insert → write metadata. |
| **Scheduling**           | Periodic batch ingest (e.g. new files from Drive), re-index after schema changes.                            |
| **Retries & visibility** | Failed documents retried; clear logs and status without writing code.                                                   |
| **Optional human steps** | “Approve for public” or “tag theme” before or after ingest.                                                             |


**Recommendation: use n8n for the prototype.**


| Criterion             | n8n                                                                                                      | Alternatives (when to consider)                                  |
| --------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Setup**             | Low-code UI; self-host or cloud; quick to wire HTTP (RAG insert/retrieve), file ops, and schedules       | —                                                                |
| **Fit for NESsT**     | Nonprofit-friendly (self-hosted, fair licensing); non-developers can inspect or tweak flows              | Airflow/Prefect/Dagster: more “data-engineering” team            |
| **RAG / HTTP**        | Native HTTP Request node; easy to call `POST /rag/insert/file` and `POST /rag/retrieve` with Bearer auth | Same possible in Prefect/Dagster with more code                  |
| **Scheduling**        | Built-in cron/interval triggers                                                                          | Prefect/Dagster/Airflow: stronger for complex DAGs               |
| **Human-in-the-loop** | Pause for approval, webhook for “curation done”                                                          | Temporal: better for long-running, multi-day workflows           |
| **Scaling**           | Single instance often enough for prototype; scale workers if needed                                      | For high-volume, parallel document pipelines: Prefect or Dagster |


**Suggested use of n8n:**

- **Workflow 1 — On-demand ingest:** Webhook or “manual” trigger → read file (or receive upload) → validate type/size → extract text (n8n code node or external script) → chunk (code or external) → HTTP POST to RAG insert → write metadata to DB/sheet.
- **Workflow 2 — Scheduled batch:** Schedule trigger → list new/changed files (Drive/FS) → loop over files → same ingest steps as above; optional “notify on failure.”
- **Workflow 3 (later):** After ingest, pause for “mark as public” or “set theme”; then update metadata and optionally trigger a re-index step.

**When to revisit:**

- **Heavy data-engineering:** Large, parallel, Python-centric pipelines → consider **Prefect** or **Dagster** (code-first, good observability).
- **Long-running, multi-step human workflows:** E.g. multi-day review chains → consider **Temporal** or n8n’s queue/approval patterns.
- **Already on a platform:** If NESsT standardizes on Power Automate or Zapier, a thin orchestration layer there calling your RAG APIs is also valid; n8n still fits as a self-hosted, API-centric option.

**Placement in architecture:** The orchestrator (n8n) sits **above or beside** the ingestion pipeline: it triggers and coordinates the steps (validate → extract → chunk → RAG insert); the RAG and search APIs remain unchanged and are called from n8n via HTTP.

---

## 4. Data Flow Summary

1. **Ingest:** Source documents (PDF, text, CSV, and later DOCX/HTML) → validation → text extraction + metadata → chunking → **RAG insert** (developer-guide pattern) → vector store + search index.
2. **Query:** User question → **RAG retrieve** (developer-guide pattern) → relevant chunks (+ optional theme filters) → optional LLM step → actionable, thematically-organized answer.
3. **Public (future):** Same retrieve path but restricted to documents marked public/curated and to a scoped key.
4. **Metrics:** Every retrieve/query logged (anonymized, no PII); latency and usage aggregated to track progress toward the 60% search-time reduction.

---

## 5. Security and Compliance (aligned with Developer Guide and Codeguard)


| Concern     | Approach                                                                                                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Secrets** | No hardcoded keys; use env vars or secrets manager for `ANTHROPIC_API_KEY`, Google OAuth, and JWT signing. |
| **Auth**    | Bearer token for all APIs; separate keys/scopes for internal vs public.                                                                                                          |
| **HTTPS**   | All endpoints over TLS only.                                                                                                                                                     |
| **Data**    | Access control (RBAC) for internal vs public content; audit logs for ingest and query; sensitive content only in internal index.                                                 |
| **Input**   | Validate and size-limit uploads; allowlisted file types (PDF, text, CSV; then DOCX/HTML via conversion); sanitize prompts and log without storing raw PII.                       |


---

## 6. Implementation Checklist (using Developer Guide patterns)

- **Ingest API:** Implement `POST /rag/insert/file` in `backend/services/rag_service.py`; support PDF, text, CSV.
- **Retrieve API:** Implement `POST /rag/retrieve` in `backend/services/rag_service.py`; support prompt + optional filters.
- **LLM:** Anthropic Messages API via `backend/services/llm_client.py` for `/api/query`.
- **Auth:** Enforce Bearer token on all routes; keys from env/secrets manager.
- **Orchestration:** Deploy n8n (self-hosted or cloud); implement ingest workflow(s): trigger → validate → extract → chunk → RAG insert → metadata; add schedule for batch ingest if needed (see §3.6).
- **Ingestion pipeline:** Normalize and chunk documents; extract metadata; tag internal/public where relevant; pipeline invoked by n8n or directly by API.
- **Metrics:** Log query latency and usage; define baseline and target for “time spent searching” to measure ≥60% improvement.
- **Public layer (later):** Scoped key + visibility filter; curated content only.
- **Docs:** Keep API contract and examples in sync with the FastAPI routes in `backend/routers/rag.py`.

---

## 7. References

- **NESsT project brief:** `04_21_23.jpg` (organization overview, challenge, opportunity, desired outcome).
- **API and integration patterns:** `backend/services/rag_service.py` and `backend/services/llm_client.py` — RAG insert/retrieve and Anthropic chat.
- **Orchestration:** [n8n](https://n8n.io) — workflow automation (recommended for prototype); alternatives: [Prefect](https://www.prefect.io), [Dagster](https://dagster.io), [Temporal](https://temporal.io) for code-first or long-running workflows.
- **NESsT:** [About NESsT](https://www.nesst.org/about-nesst).

---

*This system design defines an architecture for NESsT's AI-powered Knowledge Navigator that can be implemented and measured against the 60% search-time reduction goal.*