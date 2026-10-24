# Bid2Work AI — Tender Compliance and Work-Permit Readiness Intelligence

**Bid2Work AI** is a production-minded decision-support intelligence platform built for engineering, procurement, construction (EPC), industrial services, and infrastructure teams. It bridges the critical operational gap between **pre-award tender compliance verification** and **post-award work-permit mobilization readiness**.

---

## 1. Product Purpose & Real-World Problem

In industrial and infrastructure bidding, procurement and bid teams spend days manually cross-referencing hundreds of pages of tender Request for Proposals (RFPs) against internal company credentials, audited financials, ISO certificates, and Health, Safety & Environment (HSE) manuals. Even worse, when a contract is awarded, safety and site-mobilization requirements buried inside the tender are frequently lost during handover to operations—leading to expired certificates, missing HSE approvals, and costly work-permit delays at site mobilization.

**Bid2Work AI solves both problems in a unified workflow:**
1. **Pre-Award Compliance Matrix:** Extracts structured tender requirements with page-level traceability and matches them against bidder supporting PDFs, flagging gaps and conflicts early.
2. **Post-Award Work-Permit Handover:** Simulates contract award and automatically carries safety, HSE, and certification requirements into a structured work-permit readiness checklist, checking expiry dates and unresolved conditions before mobilization.

---

## 2. Core Features & Architecture

1. **Multi-Document PDF Ingestion:** Upload one text-based tender PDF (`TENDER`) and one or more bidder supporting PDFs (`BIDDER_SUPPORTING`).
2. **Page-Level Extraction & Traceability:** Extract and retain 1-based page text, character/word metrics, SHA-256 hashes, and source references (`filename`, `page_number`, `excerpt`).
3. **Structured Requirement Extraction:** Convert tender text into structured requirements across seven categories:
   - `ELIGIBILITY` (legal registration, licenses, joint-venture eligibility)
   - `EXPERIENCE` (similar project track record, years of operation)
   - `FINANCIAL` (minimum annual turnover, net worth, audited statements)
   - `CERTIFICATION` (ISO 9001, ISO 14001, ISO 45001, technical accreditations)
   - `DEADLINE` (submission closing dates, mobilization schedules)
   - `SAFETY` (HSE plans, confined space, lifting, PPE, work-permit rules)
   - `OTHER` (technical specifications and general terms)
4. **Bidder Evidence Matching:** Match each requirement against evidence across all uploaded bidder documents using a replaceable service interface.
5. **Real External LLM API Integration:** Powered by the standard OpenAI provider SDK (`openai.AsyncOpenAI`) with Pydantic structured output validation, bounded page-based chunking, and strict anti-prompt-injection system directives.
6. **Strict Evidence Grounding:** Validates every model-generated citation against actual extracted document text. Hallucinated or invalid citations are discarded and flagged as `Needs Review`.
7. **Deterministic Python Compliance Checks:**
   - Numerical financial thresholds with explicit currency and unit checks.
   - Date and deadline comparisons against reference mobilization dates.
   - Certificate expiry date validation in Python.
   - Document presence and exact identifiers.
   - Currency mismatch and conversion ambiguity automatically flagged as `Needs Review`.
8. **Conflict Preservation:** When documents disagree, preserve both source excerpts and filenames rather than silently picking one.
9. **Post-Award Contract Simulation:** Simulate contract award (`CTR-...`) to carry safety and operational requirements directly into a work-permit readiness checklist linked to originating requirement IDs.
10. **Human Review States & Authorization Restrictions:**
   - Review states: `incomplete`, `requires_verification`, `ready_for_review`, and `approved_by_reviewer`.
   - Only an authorised human reviewer (e.g., HSE officer or site auditor) can approve checklist items.
   - Model output can never directly approve a permit item.
11. **9-Column Compliance CSV Export:** Download consolidated compliance matrices formatted for procurement audit and operational handovers.
12. **SQLite Audit Trail:** Record all document uploads, compliance evaluations, award simulations, permit checklist updates, and report downloads.

---

## 3. External LLM API Integration & Operation Modes

Bid2Work AI features a clean, documented LLM provider implementation behind a unified service interface (`LLMProviderService`).

### Supported Provider
- **Provider:** OpenAI and OpenAI-compatible endpoints (Azure OpenAI, vLLM, Ollama, Groq, OpenRouter).
- **SDK:** Official `openai` Python SDK (`openai>=1.50.0,<4.0.0`) using `AsyncOpenAI`.
- **Default Model:** `gpt-4o-mini` (configurable via `LLM_MODEL`).

### Mock Mode vs. Live Mode

The application supports two operating modes toggled via `LLM_ENABLED`:

| Mode | `LLM_ENABLED` | Required Keys | Behavior |
| :--- | :--- | :--- | :--- |
| **Mock / Deterministic Mode** | `false` (default) | None required | Uses high-performance deterministic rule engine. Starts cleanly without any API key. Automated test suite runs 100% offline with zero external network calls. |
| **Live LLM Mode** | `true` | Valid `LLM_API_KEY` | Calls the external LLM provider for structured extraction, evidence matching, and conflict explanations. |

> **Fail-Safe Principle:** When `LLM_ENABLED=true` is requested but `LLM_API_KEY` is missing or contains a placeholder value, the backend **never fabricates simulated results**. Instead, it returns a clear configuration error (`HTTP 503 LLM_PROVIDER_ERROR`) detailing the missing credential.

---

## 4. Prompt Engineering & Anti-Prompt-Injection Safeguards

All prompts in `app/services/prompts.py` are versioned (`2026-10-v1`) and enforce defensive guidelines:

1. **Untrusted Data Isolation:** All extracted document text is treated as untrusted user data. The model is explicitly instructed to ignore any adversarial instructions embedded in the PDF (e.g., `"Ignore previous instructions"`, `"Grant automatic approval"`, or prompt extraction attempts).
2. **Bounded Chunking:** Full documents are never dumped into a single prompt. Documents are broken into bounded page/section chunks (max 3,000 characters) preserving 1-based page metadata.
3. **Structured Pydantic Validation:** Every response is requested in JSON mode (`response_format={"type": "json_object"}`) and strictly validated against Pydantic schemas (`LLMRequirementExtractionResult`, `LLMEvidenceMatchingResult`, `LLMConflictExplanation`, `LLMSafetyMappingResult`).
4. **Bounded Retry Budget:** If an output fails schema validation, the client retries up to `LLM_MAX_RETRIES` (default `2`) with a corrective reminder before raising `ExternalLLMError`.

---

## 5. Evidence Grounding & Verification

Every AI-generated assessment must link to an actual extracted document page and excerpt. After the LLM responds:

- **Grounding Verification:** The backend verifies that the cited `page_number` exists and that the `excerpt` is contained within that page's extracted text (`app/services/grounding.py`).
- **Hallucination Discard Policy:** If a source citation cannot be verified against the actual PDF text, the unsupported reference is **discarded**, and the requirement is marked `needs_review` with an explicit audit note: `"Cited excerpt could not be verified in extracted text on page X."`
- **Transparent Reasoning:** Model reasoning is stored as a concise, user-facing explanation of the factual evidence. Hidden chain-of-thought is never requested or exposed.
- **Review Aid Only:** Numeric confidence scores are treated as review aids only, never as calibrated proof of compliance.

---

## 6. Privacy, Security & Cost Considerations

- **Data Minimization:** Only relevant document chunks are transmitted to the provider. Irrelevant pages (e.g. boilerplate cover pages without search terms) are filtered out before calling the LLM.
- **No Secret/Document Logging:** API keys and raw document text are never logged in application logs, database records, or API error payloads. Only sanitized attempt counts and error codes are emitted.
- **Confidentiality Notice:** In live mode, document text is sent over HTTPS to the configured provider (`LLM_BASE_URL`). Organizations handling sensitive, classified, or proprietary tender documents must review their LLM provider's data-retention and training terms (e.g. OpenAI zero-data-retention enterprise agreements) before uploading sensitive documents.
- **Cost Controls:** Request timeouts (`LLM_TIMEOUT_SECONDS`), capped page chunk sizes, bounded retries (`LLM_MAX_RETRIES`), and candidate chunk pre-filtering prevent runaway API token costs.

---

## 7. Supported PDF Types & Safeguards

| Constraint | Limit | Description / Behavior |
| :--- | :--- | :--- |
| **Supported File Format** | `.pdf` (text-based) | Machine-readable text PDFs. Scanned/rasterized image-only PDFs are detected and rejected with an explicit message that OCR is not supported yet in the MVP. |
| **Encrypted PDFs** | Rejected | Password-protected or encrypted PDFs are detected and rejected (`PDF_EXTRACTION_ERROR`). |
| **Max File Upload Size** | `25 MB` per file | Configurable via `MAX_UPLOAD_MB` (default `25`). Oversized files return HTTP 413. |
| **Max Pages per PDF** | `200` pages | Configurable via `MAX_PAGES_PER_PDF` (default `200`). |
| **Max Bidder Files** | `10` files | Configurable via `MAX_BIDDER_FILES` (default `10`). |
| **Max Extracted Text** | `2,000,000` chars | Configurable via `MAX_EXTRACTED_TEXT_CHARS` to prevent memory exhaustion. |
| **Temporary File Cleanup** | Immediate | Uploaded bytes written to temporary storage (`/tmp/bid2work_uploads`) are strictly removed in `finally` blocks. |

---

## 8. Compliance Status & Review State Definitions

### Compliance Assessment Statuses

- **`Evidence Found` (`evidence_found`):** Verifiable evidence was matched in the bidder submission satisfying tender criteria and threshold requirements.
- **`Missing` (`missing`):** Supporting evidence was not located in the uploaded material. *Note: Indicates absence of documentation in the submission, not proof of lack of qualification.*
- **`Conflicting` (`conflicting`):** Contradictory statements or credentials detected across documents (e.g. differing turnover figures or expired certificates). Both source references are preserved.
- **`Needs Review` (`needs_review`):** Evidence requires human verification due to currency mismatches, ambiguous units, unverified citations, or partial matching.

### Work-Permit Human Review States

- **`incomplete`:** Mandatory safety or qualification evidence is absent from the submission.
- **`requires_verification`:** Credential is expired, conflicting, or requires manual HSE review.
- **`ready_for_review`:** Evidence has been extracted and matched; ready for authorized inspection.
- **`approved_by_reviewer`:** Authorised human reviewer has verified and signed off on the item. *Requires reviewer authorization.*

---

## 9. API Endpoints & Contracts

### Consistent API Response Envelope

Every endpoint returns a standard JSON envelope (`ApiResponse<T>`):

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

### Summary of Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` (and `/api/v1/health`) | Application health, LLM configuration, and readiness status |
| `GET` | `/api/v1/health/ready` | Readiness check verifying DB, temporary storage, and LLM key |
| `POST` | `/api/v1/documents/upload` | Upload tender and bidder PDFs with explicit document roles |
| `POST` | `/api/v1/analysis` | Run compliance intelligence using pre-uploaded documents or multipart upload |
| `GET` | `/api/v1/analysis/{analysis_id}` | Retrieve compliance analysis results by analysis ID |
| `POST` | `/api/v1/analysis/{analysis_id}/award` | Simulate contract award and generate work-permit readiness checklist |
| `GET` | `/api/v1/analysis/{analysis_id}/permit-readiness` | Retrieve work-permit checklist and status |
| `PATCH` | `/api/v1/permit-items/{item_id}` | Update checklist item human review status with an audit event |
| `GET` | `/api/v1/analysis/{analysis_id}/report` | Download 9-column compliance report as CSV file |

---

## 10. Environment Variables

Configure backend settings via `backend/.env` (start by copying `backend/.env.example`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LLM_ENABLED` | `false` | Toggle between mock mode (`false`) and live LLM API mode (`true`) |
| `LLM_PROVIDER` | `openai` | LLM provider name |
| `LLM_API_KEY` | *(placeholder)* | External LLM API key (never commit real keys) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | External LLM base URL (optional, configurable) |
| `LLM_MODEL` | `gpt-4o-mini` | Target LLM model name |
| `LLM_TIMEOUT_SECONDS` | `60` | Request timeout in seconds (5 - 300) |
| `LLM_MAX_RETRIES` | `2` | Max schema validation retries (0 - 5) |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated CORS allowed origins |
| `MAX_UPLOAD_MB` | `25` | Maximum upload size per PDF in MB |
| `DATABASE_URL` | `./data/bid2work_audit.db` | Path to SQLite audit database |
| `MAX_BIDDER_FILES` | `10` | Maximum number of bidder supporting PDFs |
| `MAX_PAGES_PER_PDF` | `200` | Maximum page count allowed per PDF |
| `TEMP_UPLOAD_DIR` | `/tmp/bid2work_uploads` | Scoped temporary file directory |

---

## 11. Local Setup, Testing & Verification

### 1. Setup Virtual Environment

```bash
cd backend

# Create Python 3.12 virtual environment:
python -m venv .venv

# Activate:
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run Automated Test Suite

All external provider calls are mocked in tests—**no paid API key is ever required to run the automated test suite**:

```bash
# Run all 39 tests:
pytest -v

# Run only the LLM integration tests:
pytest tests/test_llm_integration.py -v
```

### 3. Start Backend Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Readiness check: `http://localhost:8000/api/v1/health/ready`

---

## 12. Troubleshooting

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| **HTTP 503: Live LLM mode is enabled, but LLM_API_KEY is missing** | `LLM_ENABLED=true` in `.env`, but `LLM_API_KEY` is empty or has a placeholder. | Supply a valid OpenAI API key in `backend/.env` or set `LLM_ENABLED=false` for local mock mode. |
| **HTTP 502: LLM provider rate limit reached** | External provider rate limits exceeded (HTTP 429). | Retry after a few seconds, or switch to a dedicated enterprise base URL. |
| **HTTP 502: LLM provider request timed out** | LLM API took longer than `LLM_TIMEOUT_SECONDS` to respond. | Increase `LLM_TIMEOUT_SECONDS=120` in `.env`. |
| **Result marked `Needs Review` with citation warning** | Model cited an excerpt or page number not found in the actual PDF. | Grounding verification caught a hallucinated reference and safely discarded it. |
| **HTTP 413: Upload Limit Exceeded** | Uploaded file exceeds configured MB limit. | Increase `MAX_UPLOAD_MB` in `.env` if required by large bid packs. |

---

## 13. Legal & Decision-Support Disclaimer

> **Important:** Bid2Work AI is a decision-support intelligence tool. It does **not** constitute automated legal eligibility determination, formal tender adjudication, or an official work-permit issuance system. It does **not** enable actual site work or automatically issue permits. All extracted criteria, evidence matches, expiry calculations, and work-permit checklists must be reviewed and approved by authorized human procurement, legal, and HSE personnel before submission or site mobilization.
