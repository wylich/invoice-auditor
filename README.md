# AI Invoice Agent

**The AI-Powered CFO for Danish SMEs.**
A "Human-in-the-Loop" auditing tool that extracts data from invoices, validates Danish CVR numbers, handles split-VAT logic for grocery receipts, and flags anomalies before they hit your accounting software.

Built with **Pydantic AI** for structured LLM extraction with tool calling, **FastAPI** for the REST API, and **React** for the frontend.

**Deployed app:** https://invoice-auditor-production.up.railway.app/

## Quick Start

This project uses [uv](https://github.com/astral-sh/uv) for Python package management.

### 1. Install Dependencies

```bash
uv sync
```

### 2. Setup Configuration

Create a `.env` file in the root directory with your OpenAI API key:

```bash
OPENAI_API_KEY="your_key_here"
```

### 3. Run the App

**Backend API:**

```bash
uv run uvicorn invoice_auditor.api.app:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

**React frontend:**

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Requires the backend running on port 8000.

## Architecture

```
Browser
  └─► React frontend          Drag-and-drop upload, result display
        └─► FastAPI (REST)     Receives image, returns structured Invoice JSON
              └─► Image preprocessing      Normalise to standardised JPEG
                    └─► Pydantic AI agent  LLM extraction with two tools:
                          ├─ lookup_vat    Checks line items against Danish VAT rules
                          └─ validate_cvr  Validates vendor CVR via the Danish registry
                                └─► Deterministic post-audit
                                      VAT math verification, currency conversion,
                                      and Green / Review / Red status assignment
```

The key design split: the **LLM agent** handles the inherently fuzzy work (reading handwriting, parsing unstructured layouts, inferring missing fields). Everything that can be expressed as a rule - VAT arithmetic, CVR lookup, status thresholds - runs as plain Python in the post-audit layer, keeping it testable and reliable.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/audits` | Upload invoice image, run audit |
| `GET` | `/api/v1/audits` | List audits (filter by `status`, paginate with `limit`/`offset`) |
| `GET` | `/api/v1/audits/{audit_id}` | Get a single audit by ID |

## How It Works

1. **Image preprocessing** - uploaded images are converted to standardized JPEG
2. **Pydantic AI agent** - a GPT-5-mini agent extracts structured data from the image, calling tools:
   - `lookup_vat` - checks each line item against Danish VAT rules
   - `validate_cvr` - validates vendor CVR numbers against the Danish business registry
3. **Deterministic post-processing** - VAT math verification, currency handling, and status assignment run as plain Python (not LLM) for reliability
4. **Result** - the invoice is classified as Green (auto-approved), Review, or Red (issues found)

## Disclaimer

This is an **MVP**. Data is processed locally or via API. Ensure you comply with GDPR and the Danish Bookkeeping Act when handling real financial data.
