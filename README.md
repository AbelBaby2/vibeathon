# Bid2Work AI — Evidence-Driven Tender Compliance and Work-Permit Readiness Intelligence

**Bid2Work AI** is a production-grade enterprise decision-support intelligence platform built for MSME bidders, procurement leads, and Health, Safety & Environment (HSE) compliance auditors. It bridges the critical operational divide between **pre-award tender compliance analysis** and **post-award work-permit mobilization readiness**.

---

## 1. Project Overview & Real-World Problem

In engineering, procurement, construction (EPC), industrial facilities, and technical services, bid teams spend days manually cross-referencing multi-hundred-page tender Requests for Proposals (RFPs) against company credentials, audited financial records, ISO certificates, and HSE manuals. 

Critical challenges include:
- **Missing or Conflicting Proof:** Bidders miss mandatory criteria or submit conflicting data (e.g. outdated turnover figures, differing legal entities, or expired certificates), causing tender disqualification.
- **Traceability Deficits:** Evaluators struggle to verify exactly where in thousands of pages an assertion is grounded.
- **Handover Blindspots:** When a tender is won, safety and site-mobilization requirements buried inside tender clauses are frequently lost during operational handover, causing expensive site mobilization delays and unverified safety credentials.

**Bid2Work AI solves this with end-to-end intelligence:**
1. **Pre-Award Tender Compliance:** Ingests tender PDFs and multiple bidder proof PDFs, extracts clause requirements with exact page-level citations, matches evidence, and flags gaps and conflicts.
2. **Post-Award Work-Permit Readiness:** Carries HSE and certification clauses forward into an actionable pre-mobilization checklist upon simulated contract award, validates certificate expiration dates, and records human reviewer sign-offs in an immutable audit ledger.

---

## 2. Main Features & Intended Users

### Primary Users
- **MSME Bidders & Tender Managers:** Identify compliance gaps, missing certifications, and conflicting statements before submitting bids.
- **Compliance & Procurement Reviewers:** Cross-examine claims with exact document-page citations and download audit-ready compliance CSV reports.
- **Site HSE & Safety Officers:** Carry forward tender safety commitments into pre-mobilization work-permit readiness checklists and record qualification verifications.

### Key Capabilities
- **Multi-Document Ingestion:** Processes 1 primary Tender PDF (`TENDER`) alongside up to 10 Bidder Supporting PDFs (`BIDDER_SUPPORTING`).
- **Exact Page-Level Citations:** Retains 1-based page indices, character counts, SHA-256 integrity hashes, and verbatim source excerpts.
- **Categorized Requirement Extraction:** Classifies requirements into `ELIGIBILITY`, `EXPERIENCE`, `FINANCIAL`, `CERTIFICATION`, `DEADLINE`, `SAFETY`, and `OTHER`.
- **Bidder Evidence Cross-Matching:** Matches each requirement against supporting documents with confidence scoring and extracted values.
- **Deterministic Python Validation:** Performs Python-level comparisons for numeric turnover thresholds, ISO certifications, and certificate expiration dates.
- **Conflict & Discrepancy Highlighting:** Preserves conflicting claims from differing documents without silently dropping contradictory evidence.
- **Simulated Contract Award:** Connects tender analysis to post-award work-permit mobilization, carrying safety requirements forward into an actionable checklist.
- **Audited Human Review Workflow:** Enables qualified reviewers to transition items between `incomplete`, `requires_verification`, `ready_for_review`, and `approved_by_reviewer` with role guards.
- **Consolidated CSV Export:** Downloads a 9-column compliance matrix generated directly by the backend service.
- **SQLite Audit Trail:** Automatically logs all document uploads, evaluations, award simulations, reviews, and report downloads.

---

## 3. End-to-End Workflow

```
[1. Upload Tender PDF] + [Upload Bidder Supporting PDFs]
                       │
                       ▼
[2. Automated PDF Extraction & Text Layer Validation]
                       │
                       ▼
[3. Clause Extraction & Evidence Matching (Deterministic or LLM)]
                       │
                       ▼
[4. Compliance Evaluation & Rationale Generation]
     ├── "Evidence Found"
     ├── "Missing"
     ├── "Conflicting"
     └── "Needs Review"
                       │
                       ▼
[5. Interactive Tender Compliance Table & Evidence Detail Drawer]
                       │
                       ▼
[6. Simulate Contract Award (CTR-..., Mobilization Date, Site)]
                       │
                       ▼
[7. Work-Permit Readiness Checklist Generation]
     ├── Certificate Expiration Verification
     ├── Unresolved Blocking Conditions Detection
     └── Human Reviewer Verification & Sign-Off (Role-Guarded)
                       │
                       ▼
[8. Export Consolidated CSV Report & Audit Trail Inspection]
```

---

## 4. Technology Stack & Architecture

### Backend
- **Framework:** FastAPI 0.115+ (Python 3.10 / 3.12)
- **ASGI Server:** Uvicorn with standard workers
- **Data Validation & Schemas:** Pydantic v2 & Pydantic-Settings
- **PDF Extraction:** PyPDF 5.0+ (native text extraction)
- **Persistence & Auditing:** SQLite 3 with connection context managers and memory-buffer fallback
- **HTTP Client:** HTTPX 0.28+
- **LLM SDK:** Official OpenAI Python SDK (`AsyncOpenAI`)
- **Testing:** Pytest 8.3+ with AnyIO plugin

### Frontend
- **Framework:** React 18 with TypeScript 5.6
- **Build Tool:** Vite 5.4
- **Iconography:** Lucide React
- **Design System:** Vanilla CSS with custom CSS variables (Three-tone palette, no gradients, subtle glassmorphism)
- **API Client:** Centralized typed service module (`bid2WorkApi`) consuming standard `ApiResponse<T>` envelopes

### Architectural Highlights
- **Decoupled Services:** Clean separation of concerns across extraction (`pdf_extractor`), parsing (`requirement_extractor`), matching (`evidence_matcher`), rules (`compliance_rules`), permit readiness (`permit_readiness`), and reporting (`report_generator`).
- **Defensive Error Handling:** Comprehensive custom exception hierarchy (`ValidationError`, `NotFoundError`, `UploadLimitExceededError`, `InvalidFileTypeError`, `UnauthorizedReviewerError`, `ExternalLLMError`) mapped to RFC 7807-compatible JSON error responses.

---

## 5. Final Repository Structure

```
vibeathon/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI entrypoint, CORS, lifespan, routes mounting
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analysis.py         # /api/v1/analysis (create, list, get, award, report)
│   │   │   │   ├── audit.py            # /api/v1/audit/events
│   │   │   │   ├── compliance.py       # /api/v1/compliance/extract, /analyze
│   │   │   │   ├── documents.py        # /api/v1/documents/upload, list
│   │   │   │   ├── health.py           # /health, /api/v1/health, /ready
│   │   │   │   ├── permit.py           # /api/v1/permits/simulate-award, /permit-items/{id}
│   │   │   │   └── reports.py          # /api/v1/reports/export
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic BaseSettings, environment variable loader
│   │   │   ├── exceptions.py           # Custom exception classes and global handlers
│   │   │   └── logging.py              # Structured JSON logging & request ID tracking
│   │   ├── db/
│   │   │   └── sqlite.py               # SQLite schema initialization & connection manager
│   │   ├── models/
│   │   │   ├── analysis_record.py      # SQLite repository for ComplianceAnalysisResult
│   │   │   ├── audit_record.py         # SQLite repository for AuditEvent trail
│   │   │   ├── document_record.py      # SQLite repository for DocumentExtractionResult
│   │   │   └── permit_record.py        # SQLite repository for PermitReadinessResult
│   │   ├── schemas/
│   │   │   ├── audit.py                # Audit trail contracts
│   │   │   ├── common.py               # ApiResponse envelope, ErrorCode, ProcessingState
│   │   │   ├── compliance.py           # TenderRequirement, BidderEvidence, ComplianceResult
│   │   │   ├── document.py             # DocumentMetadata, ExtractedPage, BatchUpload
│   │   │   ├── permit.py               # PermitChecklistItem, ReviewStatus, AwardRequest
│   │   │   └── report.py               # ReportExportRequest, ExportableReportData
│   │   └── services/
│   │       ├── compliance_rules.py     # Deterministic evaluation & scoring logic
│   │       ├── evidence_matcher.py     # Cross-document evidence matching service
│   │       ├── grounding.py            # Citation verification & anti-hallucination checks
│   │       ├── llm_provider.py         # AsyncOpenAI provider client & schema validation
│   │       ├── pdf_extractor.py        # PyPDF-based native text extraction
│   │       ├── permit_readiness.py     # Award simulation & safety carryover mapping
│   │       ├── prompts.py              # Versioned anti-injection prompt templates
│   │       ├── report_generator.py     # 9-column CSV, Markdown, HTML, JSON report builder
│   │       └── requirement_extractor.py # Regex/LLM requirement extraction service
│   ├── tests/                          # 39 Pytest automated unit and integration tests
│   ├── .env.example                    # Backend environment template
│   ├── pytest.ini                      # Pytest configuration
│   └── requirements.txt                # Python dependencies
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUploadSection.tsx   # Drag-and-drop file upload with role validation
│   │   │   ├── Header.tsx              # Application header with analysis selector
│   │   │   ├── PermitReviewModal.tsx   # Human review verification & sign-off dialog
│   │   │   ├── RequirementDetailDrawer.tsx # Slide-out evidence detail drawer
│   │   │   ├── Sidebar.tsx             # Persistent enterprise navigation sidebar
│   │   │   ├── StatusBadge.tsx         # Accessible compliance & review badges
│   │   │   └── WorkflowOverview.tsx    # Technical architecture & telemetry card
│   │   ├── hooks/
│   │   │   └── useWorkflowState.ts     # Global state management and API integration
│   │   ├── layouts/
│   │   │   └── MainLayout.tsx          # Shell layout with disclaimer banner
│   │   ├── pages/
│   │   │   ├── ComplianceReportsPage.tsx # Report center & backend CSV download
│   │   │   ├── DashboardPage.tsx       # Main tab router
│   │   │   ├── OverviewPage.tsx        # High-level statistics, saved runs, audit trail
│   │   │   ├── PermitReadinessPage.tsx # Simulated award & work-permit checklist
│   │   │   └── TenderAnalysisPage.tsx  # Requirements table, search, filters, drawer
│   │   ├── services/
│   │   │   └── apiClient.ts            # Typed HTTP client with fetch wrapper
│   │   ├── styles/
│   │   │   └── global.css              # Custom minimalist design system & tokens
│   │   ├── types/
│   │   │   ├── contracts.ts            # TypeScript interfaces matching backend schemas
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── .env.example                    # Frontend environment template
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── render.yaml                         # Render Blueprint infrastructure specification
└── README.md                           # Master project documentation
```

---

## 6. Prerequisites

- **Python:** 3.10 or 3.12+ (64-bit)
- **Node.js:** 18.x or 20.x+ LTS & npm 10+
- **Git**

---

## 7. Local Setup for Backend & Frontend

### 7.1 Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env

# 6. Start backend development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- **API Base:** `http://127.0.0.1:8000`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/health`

### 7.2 Frontend Setup

```bash
# 1. Open a new terminal and navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env
# (Leave VITE_API_BASE_URL empty for local development; Vite proxies /api to 127.0.0.1:8000)

# 4. Start Vite development server
npm run dev
```

The user interface will be accessible at `http://localhost:5173/`.

---

## 8. Environment Variables (`.env.example`)

### Backend (`backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `Bid2Work AI` | Name of the application displayed in logs and headers |
| `APP_ENV` | `development` | Runtime environment (`development`, `production`, `test`) |
| `APP_VERSION` | `0.1.0` | Semantic API version |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `HOST` | `0.0.0.0` | Server interface binding |
| `PORT` | `8000` | Port for the FastAPI server |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of permitted frontend origins |
| `MAX_UPLOAD_MB` | `25` | Maximum upload size per PDF file in megabytes |
| `MAX_BIDDER_FILES` | `10` | Maximum number of bidder supporting PDFs allowed per analysis |
| `MAX_PAGES_PER_PDF` | `200` | Maximum number of pages extracted from any single PDF |
| `TEMP_UPLOAD_DIR` | `/tmp/bid2work_uploads` | Scoped temporary file path for upload processing |
| `DATABASE_URL` | `./data/bid2work_audit.db` | Path to the SQLite persistence and audit database |
| `LLM_ENABLED` | `false` | When `false`, runs in deterministic/mock mode without API keys |
| `LLM_PROVIDER` | `openai` | LLM provider backend (`openai`, `azure`, `groq`) |
| `LLM_API_KEY` | *(placeholder)* | API key for the live LLM provider (never commit real secrets) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL for OpenAI-compatible endpoint |
| `LLM_MODEL` | `gpt-4o-mini` | Model name used for clause extraction |
| `LLM_TIMEOUT_SECONDS` | `60` | Network request timeout for external LLM API calls |
| `LLM_MAX_RETRIES` | `2` | Number of schema validation retry attempts on parse failure |

### Frontend (`frontend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | *(empty)* | Base URL of backend API. Leave empty locally to use Vite proxy; set to deployed backend URL in production |

---

## 9. How to Run in Mock / Deterministic Mode

Bid2Work AI is designed to run completely offline without an external API key:

1. In `backend/.env`, set:
   ```env
   LLM_ENABLED=false
   ```
2. Start the backend: `uvicorn app.main:app --port 8000`
3. The platform uses the deterministic Python rules engine (`ComplianceRulesService`), PyPDF native extraction, and regex heuristic clause extraction.
4. All 39 backend test cases execute in mock mode with zero external network dependencies.

---

## 10. How to Configure the Real LLM Provider

To enable live LLM evaluation:

1. Obtain an API key from an OpenAI-compatible provider (e.g. OpenAI, Groq, OpenRouter).
2. In `backend/.env`, set:
   ```env
   LLM_ENABLED=true
   LLM_PROVIDER=openai
   LLM_API_KEY=your_actual_api_key_here
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_MODEL=gpt-4o-mini
   ```
3. Restart the backend. The health endpoint (`/health`) will show `"llm_configured": true`.
4. If an invalid or placeholder key is configured with `LLM_ENABLED=true`, the backend returns a clear `HTTP 503 LLM_PROVIDER_ERROR` detailing the configuration error rather than silently fabricating mock results.

---

## 11. How to Run Tests

### Backend Tests
```bash
cd backend
.venv\Scripts\Activate.ps1
pytest -v
```
All 39 unit, schema, PDF extraction, rules, permit, and report tests will run and pass.

### Frontend Typecheck & Tests
```bash
cd frontend
npm test
```
Executes TypeScript strict type checking (`tsc --noEmit`).

---

## 12. How to Build the Frontend

```bash
cd frontend
npm run build
```
This runs TypeScript compilation (`tsc -b`) and Vite production bundling into `frontend/dist/`.

To preview the production build locally:
```bash
npm run preview
```

---

## 13. Deploying to Render

The repository includes a ready-to-use `render.yaml` Blueprint configuring two independently deployable services:
1. **`bid2work-ai-backend`:** Python web service running FastAPI on port `$PORT`.
2. **`bid2work-ai-frontend`:** Static site publishing the Vite build from `frontend/dist`.

### Deployment via Render Blueprint
1. Push your repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New** > **Blueprint**.
3. Connect your repository. Render will automatically detect `render.yaml`.
4. Configure required secrets in the Render dashboard:
   - `CORS_ALLOWED_ORIGINS`: Set to your Render frontend static site URL (e.g. `https://bid2work-ai-frontend.onrender.com`).
   - `LLM_API_KEY`: Enter your live LLM provider API key if using live mode, or leave `LLM_ENABLED=false`.
   - `VITE_API_BASE_URL`: In the frontend static site settings, set to the backend URL (e.g. `https://bid2work-ai-backend.onrender.com`).

### Manual Render Configuration (Without Blueprint)
If configuring manually:
- **Backend Service:**
  - Runtime: `Python`
  - Root Directory: `backend`
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Health Check Path: `/api/v1/health`
- **Frontend Service:**
  - Type: `Static Site`
  - Root Directory: `frontend`
  - Build Command: `npm install && npm run build`
  - Publish Directory: `dist`
  - Rewrite Rules: `/*` -> `/index.html` (for SPA routing)

---

## 14. Persistence Guarantees on Ephemeral Cloud Filesystems

> [!IMPORTANT]
> **Ephemeral Storage Notice on Render:**
> Standard Render web services utilize an ephemeral filesystem. Any files stored in `/tmp` or the local SQLite database (`./data/bid2work_audit.db`) are reset when the service restarts, scales, or redeploys.
> 
> **For Persistent Production Environments:**
> 1. Attach a **Render Persistent Disk** mounted at `/data` and configure `DATABASE_URL=/data/bid2work_audit.db`.
> 2. Or configure a managed PostgreSQL instance for production audit logging.
> 3. Document temporary files are safely purged from `/tmp/bid2work_uploads` in `finally` blocks immediately following extraction.

---

## 15. API Endpoint Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Basic application health and service version |
| `GET` | `/api/v1/health` | Comprehensive health, LLM configuration, and DB status |
| `GET` | `/api/v1/health/ready` | Readiness probe checking database readiness and storage paths |
| `GET` | `/api/v1/documents` | List metadata of previously uploaded documents |
| `POST` | `/api/v1/documents/upload` | Upload files with explicit `roles` (`TENDER`, `BIDDER_SUPPORTING`) |
| `GET` | `/api/v1/analysis` | Retrieve list of recent compliance analysis runs from SQLite |
| `POST` | `/api/v1/analysis` | Execute compliance analysis using uploaded document IDs or multipart |
| `GET` | `/api/v1/analysis/{id}` | Retrieve full compliance analysis findings by analysis ID |
| `POST` | `/api/v1/analysis/{id}/award` | Simulate contract award and generate work-permit readiness checklist |
| `GET` | `/api/v1/analysis/{id}/permit-readiness` | Retrieve post-award work-permit checklist (`auto_simulate=false`) |
| `PATCH` | `/api/v1/permit-items/{item_id}` | Update human review state with role authorization and audit event |
| `GET` | `/api/v1/analysis/{id}/report` | Download official 9-column compliance CSV report |
| `POST` | `/api/v1/reports/export` | Export structured Markdown, HTML, or JSON compliance report |
| `GET` | `/api/v1/audit/events` | Query immutable SQLite audit log events |

---

## 16. Supported PDF Types & File Limits

- **Text-Based PDFs Only:** Ingests native text layers. Scanned raster-image PDFs requiring OCR are rejected with an actionable notice.
- **Encrypted / Password-Protected PDFs:** Detected and rejected with HTTP 422 (`PDF_EXTRACTION_ERROR`).
- **File Size Limit:** Maximum 25 MB per PDF file (configurable via `MAX_UPLOAD_MB`).
- **Page Limits:** Up to 200 pages per document (configurable via `MAX_PAGES_PER_PDF`).
- **Batch Limits:** Up to 10 bidder supporting PDFs per analysis session.

---

## 17. Evidence Status & Human Review Definitions

### Compliance Status Categories (Backend & Frontend)
- **`Evidence Found`:** Verifiable evidence matched in bidder material meeting clause criteria and numerical thresholds.
- **`Missing`:** Supporting evidence was not located in the uploaded material. Indicates missing documentation, not definitive lack of bidder qualification.
- **`Conflicting`:** Inconsistent claims detected across documents (e.g. differing turnover numbers or conflicting validity dates). Both references are preserved.
- **`Needs Review`:** Requires human clarification due to ambiguous units, unverified citations, or currency mismatch.

### Work-Permit Human Review States
- **`incomplete`:** Mandatory safety documents or credentials have not been provided.
- **`requires_verification`:** Credentials expired, conflicting, or require physical inspection.
- **`ready_for_review`:** Credentials attached; awaiting qualified safety inspector verification.
- **`approved_by_reviewer`:** Qualified human reviewer has verified and signed off on the item. *Requires reviewer authorization role (`hse_officer`, `authorised_reviewer`, `safety_auditor`).*

---

## 18. Data Privacy, Provider Data Handling & Security

- **Zero Document Leakage in Bundles:** API keys and credentials are never placed in `VITE_` frontend variables or browser local storage.
- **Scoped Upload Cleanup:** Uploaded files written to temporary disk are automatically removed in `finally` blocks.
- **Data Minimization:** Only relevant text chunks are transmitted to LLM endpoints.
- **Prompt Injection Isolation:** Extracted document text is strictly encapsulated as untrusted user data with boundary tags.
- **Confidential Tenders Notice:** In live LLM mode, text is transmitted via HTTPS to the configured provider. Organizations dealing with proprietary or confidential bids should verify zero-retention enterprise terms with their provider.

---

## 19. Known Limitations

1. **No Scanned Image OCR:** The MVP supports text-based PDFs only. Scanned image PDFs requiring optical character recognition must be converted prior to ingestion.
2. **No Automatic Permit Issuance:** Work-permit readiness checklists assist human reviewers; they do **not** generate legal or statutory work permits. Automatic issuance is strictly disallowed.
3. **No Final Legal Adjudication:** Findings are decision-support intelligence only. They do not constitute a formal legal procurement ruling.
4. **Ephemeral Local Storage:** On serverless or ephemeral container deployments without persistent disks, uploaded sessions do not persist across instance restarts.

---

## 20. Troubleshooting Common Issues

| Problem | Root Cause | Solution |
| :--- | :--- | :--- |
| **HTTP 503: Live LLM mode is enabled, but LLM_API_KEY is missing** | `LLM_ENABLED=true` in `.env`, but no valid API key was provided | Add a valid key in `backend/.env` or set `LLM_ENABLED=false` to use mock mode |
| **CORS Error on Frontend** | Backend `CORS_ORIGINS` does not include frontend origin | Add `http://localhost:5173` or your deployed static site URL to `CORS_ORIGINS` in `backend/.env` |
| **HTTP 413: Upload Limit Exceeded** | Uploaded file exceeds 25 MB | Increase `MAX_UPLOAD_MB=50` in `backend/.env` |
| **HTTP 403: Only an authorised human reviewer can approve** | Attempted to mark item `approved_by_reviewer` without reviewer authorization | Select an authorized role (`hse_officer`, `authorised_reviewer`) and check the authorization confirmation |
| **Blank screen on deployed frontend** | SPA router rewrite missing | Ensure Render static site has rewrite rule `/*` -> `/index.html` configured |
| **Backend 404 on `/api/v1/...` from frontend** | `VITE_API_BASE_URL` misconfigured | In production, set `VITE_API_BASE_URL` to the backend URL without trailing slash |
