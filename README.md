# Bid2Work AI — Tender Compliance and Work-Permit Readiness Intelligence

**Bid2Work AI** is a production-minded decision-support intelligence platform designed for engineering, procurement, construction (EPC), industrial services, and infrastructure teams. It bridges the critical operational gap between **pre-award tender compliance verification** and **post-award work-permit mobilization readiness**.

---

## 1. Product Purpose & Real-World Problem

In industrial and infrastructure bidding, procurement and bid teams spend days manually cross-referencing hundreds of pages of tender Request for Proposals (RFPs) against internal company credentials, audited financials, ISO certificates, and Health, Safety & Environment (HSE) manuals. Even worse, when a contract is awarded, safety and site-mobilization requirements buried inside the tender are frequently lost during handover to operations—leading to expired certificates, missing HSE approvals, and costly work-permit delays at site mobilization.

**Bid2Work AI solves both problems in a unified workflow:**
1. **Pre-Award Compliance Matrix:** Extracts structured tender requirements with page-level traceability and matches them against bidder supporting PDFs, flagging gaps and conflicts early.
2. **Post-Award Work-Permit Handover:** Simulates contract award and automatically carries safety, HSE, and certification requirements into a structured work-permit readiness checklist, checking expiry dates and unresolved conditions before mobilization.

---

## 2. Core Features & 10-Step Workflow

1. **Multi-Document PDF Ingestion:** Upload one text-based tender PDF (`TENDER`) and one or more bidder supporting PDFs (`BIDDER_SUPPORTING`).
2. **Page-Level Extraction & Traceability:** Extract and retain 1-based page text, character/word metrics, SHA-256 hashes, and source references (`filename`, `page_number`, `excerpt`).
3. **Requirement Identification:** Identify structured tender requirements across six core domains:
   - `ELIGIBILITY` (legal registration, licenses, joint-venture rules)
   - `EXPERIENCE` (similar project track record, years of operation)
   - `FINANCIAL` (minimum annual turnover, net worth, audited statements)
   - `CERTIFICATION` (ISO 9001, ISO 14001, ISO 45001, technical accreditations)
   - `DEADLINE` (submission closing dates, mobilization schedules)
   - `SAFETY` (HSE plans, confined space, lifting, PPE, work-permit rules)
4. **Bidder Evidence Matching:** Match each extracted tender requirement against evidence across all uploaded bidder PDFs.
5. **Standardized Compliance Flagging:** Classify every requirement as:
   - `Evidence Found`
   - `Missing`
   - `Conflicting`
   - `Needs Review`
6. **Verifiable Citations:** Display verbatim or near-verbatim evidence excerpts alongside source filenames and 1-based page numbers.
7. **Contract Award Simulation:** Simulate a contract award (`CTR-...`) to carry safety and certification requirements directly into a post-award work-permit readiness checklist.
8. **Permit Readiness & Expiry Verification:** Check supporting safety documents, qualifications, issuing authorities, expiry dates (`YYYY-MM-DD`) against planned mobilization dates, and unresolved blocking conditions.
9. **Audit Trail Persistence:** Record compliance evaluations, award simulations, and report exports in a lightweight SQLite audit database (`audit_events` table) with graceful non-blocking fallback.
10. **Multi-Format Report Export:** Export consolidated compliance and work-permit readiness reports in `MARKDOWN`, `JSON`, or `HTML`.

---

## 3. Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React 18, Vite 5, TypeScript 5 |
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **PDF Processing** | `pypdf` (page-level text extraction with scoped temp-file cleanup) |
| **Data Validation** | Pydantic v2 & matching TypeScript interfaces |
| **LLM Integration** | Configurable external OpenAI-compatible REST client via `httpx` |
| **Audit Persistence** | Lightweight built-in `sqlite3` (optional/non-blocking for core document analysis) |
| **Testing** | `pytest` + FastAPI `TestClient` (backend), TypeScript compiler checks (`tsc --noEmit`) |
| **Deployment** | Render Blueprint (`render.yaml`) |

---

## 4. Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI application factory, CORS, middleware
│   │   ├── api/routes/
│   │   │   ├── health.py                # GET /health, GET /api/v1/health
│   │   │   ├── compliance.py            # POST /api/v1/compliance/extract & /analyze
│   │   │   ├── permit.py                # POST /api/v1/permits/simulate-award
│   │   │   ├── audit.py                 # GET /api/v1/audit/events
│   │   │   └── reports.py               # POST /api/v1/reports/export
│   │   ├── core/
│   │   │   ├── config.py                # Environment-driven settings & upload limits
│   │   │   ├── logging.py               # Structured JSON logging with X-Request-ID
│   │   │   └── exceptions.py            # Standardized ApiResponse error handlers
│   │   ├── db/
│   │   │   └── sqlite.py                # Lightweight SQLite initialization & health check
│   │   ├── models/
│   │   │   └── audit_record.py          # AuditRepository for recording/listing events
│   │   ├── schemas/
│   │   │   ├── common.py                # ApiResponse[T], ApiError, ProcessingState, HealthStatus
│   │   │   ├── document.py              # DocumentMetadata, ExtractedPage, DocumentExtractionResult
│   │   │   ├── compliance.py            # TenderRequirement, BidderEvidence, RequirementAssessment
│   │   │   ├── permit.py                # PermitChecklistItem, AwardSimulationRequest, PermitReadinessResult
│   │   │   ├── audit.py                 # AuditEvent, AuditEventType, AuditLogListResponse
│   │   │   └── report.py                # ReportExportRequest, ExportableReportData
│   │   └── services/
│   │       ├── pdf_extractor.py         # pypdf extraction, validation, temp-file cleanup
│   │       ├── llm_provider.py          # External LLM API wrapper configured via env vars
│   │       ├── requirement_extractor.py # Tender requirement extraction service
│   │       ├── evidence_matcher.py      # Bidder evidence matching service
│   │       ├── compliance_rules.py      # Status classification & summary calculation
│   │       ├── permit_readiness.py      # Contract award simulation & permit checklist service
│   │       └── report_generator.py      # JSON / Markdown / HTML report builder
│   ├── tests/                           # Automated pytest suite
│   ├── pytest.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/                  # Reusable UI components
│   │   ├── hooks/                       # Workflow state & API hooks
│   │   ├── layouts/                     # Application shell & disclaimer banner
│   │   ├── pages/                       # Main dashboard & workflow views
│   │   ├── services/                    # Typed fetch client (bid2WorkApi)
│   │   ├── styles/                      # Global CSS design tokens
│   │   └── types/                       # Shared TypeScript contracts mirroring Pydantic
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
├── render.yaml                          # Render Blueprint deployment spec
├── .gitignore
└── README.md
```

---

## 5. Shared Data Contracts & API Endpoints

### Consistent API Response Envelope

Every endpoint returns a consistent JSON envelope (`ApiResponse<T>`):

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "request_id": "REQ-8F3A12C901",
    "timestamp": "2026-10-24T12:00:00Z",
    "processing_state": "COMPLETED",
    "version": "0.1.0",
    "warnings": []
  }
}
```

When an error occurs (`4xx` or `5xx`), `success` is `false`, `data` is `null`, `meta.processing_state` is `"FAILED"`, and `error` contains a structured `ApiError` (`code`, `message`, `details`, `request_id`, `timestamp`).

### Endpoint Contracts

| Method | Path | Request Contract | Response Payload (`data`) |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` (and `/health`) | None | `HealthStatus` (service status, limits, DB & LLM readiness) |
| `POST` | `/api/v1/compliance/extract` | `multipart/form-data`: `file` (PDF), `role` (`TENDER` \| `BIDDER_SUPPORTING`) | `DocumentExtractionResult` (metadata + 1-based page text array) |
| `POST` | `/api/v1/compliance/analyze` | `multipart/form-data`: `tender_file` (1 PDF), `bidder_files` (1..N PDFs) | `ComplianceAnalysisResult` (requirements, assessments, evidence, metrics) |
| `POST` | `/api/v1/permits/simulate-award` | `application/json`: `AwardSimulationRequest` | `PermitReadinessResult` (checklist items, expiry checks, blocking conditions) |
| `GET` | `/api/v1/audit/events` | Query params: `analysis_id` (optional), `limit` (1..200) | `AuditLogListResponse` (`events`, `total`) |
| `POST` | `/api/v1/reports/export` | `application/json`: `ReportExportRequest` | `ExportableReportData` (rendered Markdown, JSON, or HTML report) |

---

## 6. Prerequisites & Installation

### Prerequisites
- **Python:** 3.11 or newer
- **Node.js:** 18.x or 20.x+ (with `npm`)

### Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

---

## 7. Environment Variable Setup

### Backend (`backend/.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `Bid2Work AI` | Service display name |
| `APP_ENV` | `development` | Environment (`development`, `staging`, `production`) |
| `LOG_LEVEL` | `INFO` | Structured log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server bind port |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed frontend origins |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum file size per uploaded PDF in megabytes |
| `MAX_BIDDER_FILES` | `10` | Maximum number of bidder supporting PDFs per analysis |
| `MAX_PAGES_PER_PDF` | `200` | Maximum page count allowed per PDF |
| `TEMP_UPLOAD_DIR` | `/tmp/bid2work_uploads` | Scoped directory for temporary PDF extraction files |
| `SQLITE_DB_PATH` | `./data/bid2work_audit.db` | File path for SQLite audit event storage |
| `LLM_PROVIDER` | `openai_compatible` | External LLM provider identifier |
| `LLM_API_KEY` | *(placeholder)* | API key for external LLM calls (never commit real keys) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL for OpenAI-compatible chat completions |
| `LLM_MODEL` | `gpt-4o-mini` | Target model name |
| `LLM_TIMEOUT_SECONDS` | `60` | Request timeout for external LLM calls |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `""` (empty uses Vite proxy) | Base URL of backend API when deployed separately |

---

## 8. Local Development Commands

### Start the Backend API Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

### Start the Frontend Dev Server

```bash
cd frontend
npm run dev
```

- Frontend UI: `http://localhost:5173` (automatically proxies `/api` and `/health` to `http://127.0.0.1:8000`)

---

## 9. Testing Commands

### Backend Automated Tests (`pytest`)

```bash
cd backend
pytest -v
```

### Frontend Type & Build Verification

```bash
cd frontend
npm run typecheck
npm run build
```

---

## 10. Render Deployment Overview

The repository includes a `render.yaml` Blueprint at the root defining two services:
1. **`bid2work-ai-backend` (Python Web Service):**
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/api/v1/health`
   - Configure `LLM_API_KEY` and `CORS_ALLOWED_ORIGINS` in the Render dashboard.
2. **`bid2work-ai-frontend` (Static Site):**
   - Root directory: `frontend`
   - Build command: `npm ci && npm run build`
   - Publish directory: `dist`
   - Set `VITE_API_BASE_URL` to the public Render URL of `bid2work-ai-backend`.

---

## 11. Current MVP Limitations & Safety Disclaimers

- **Text-Based PDFs Only:** The MVP uses `pypdf` for deterministic page-level text extraction and does not perform OCR on scanned image-only PDFs. Documents with little or no extractable text trigger explicit extraction warnings.
- **Ephemeral File Handling:** Uploaded PDFs are processed in temporary storage and deleted immediately after page extraction; raw PDFs are not persisted on disk.
- **Decision-Support Disclaimer:**
  > **Important:** Bid2Work AI is a decision-support intelligence tool. It does **not** make automated legal eligibility decisions, adjudicate formal procurement compliance, or issue binding safety work permits. All extracted requirements, evidence matches, expiry dates, and permit checklists must be reviewed and approved by qualified procurement, legal, and HSE professionals prior to bid submission or site mobilization.
