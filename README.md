# AI Invoice Agent

**The AI-Powered CFO for Danish SMEs.**
A "Human-in-the-Loop" auditing tool that extracts data from invoices, validates Danish CVR numbers, handles split-VAT logic for grocery receipts, and flags anomalies before they hit your accounting software.

Built with **Pydantic AI** for structured LLM extraction with tool calling, **FastAPI** for the REST API, **React** for the frontend, and **Streamlit** as a legacy UI.

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

**Streamlit UI** (legacy):

```bash
uv run streamlit run app.py
```

Upload an invoice image from `data/example_invoices/` to test.

## Project Structure

```
invoice-auditor/
├── app.py                                  # Streamlit UI (legacy)
├── pyproject.toml                          # Dependencies & build config
├── .env                                    # API keys (not committed)
├── frontend/                               # React frontend
│   ├── src/
│   │   ├── App.tsx                         # Main app component
│   │   ├── api.ts                          # API client (fetch wrapper)
│   │   ├── types.ts                        # TypeScript types matching Python schema
│   │   └── components/
│   │       ├── Header.tsx                  # Top bar
│   │       ├── FileUpload.tsx              # Drag-and-drop upload zone
│   │       ├── AuditResult.tsx             # Invoice result card
│   │       └── PrivacyNotice.tsx           # GDPR warning banner
│   ├── package.json
│   └── vite.config.ts
├── data/
│   ├── example_invoices/                   # Sample invoices for testing
│   └── lookup_dicts/
│       └── vat_lookup.json                 # VAT exemption rules ("Pant", "Avis", etc.)
└── src/invoice_auditor/
    ├── agent/
    │   ├── auditor.py                      # Pydantic AI agent, tools & orchestration
    │   └── prompt.py                       # System prompt for the agent
    ├── api/
    │   ├── app.py                          # FastAPI application factory
    │   └── routes.py                       # REST API endpoints (/api/v1/audits)
    ├── core/
    │   ├── cvr_manager.py                  # Async CVR registry validation
    │   ├── schema.py                       # Pydantic models (Invoice, AuditResult, LineItem, etc.)
    │   └── vat_manager.py                  # VAT rule lookup engine
    ├── processing/
    │   ├── image.py                        # Image preprocessing
    │   └── post_audit.py                   # Post-audit verification & status assignment
    └── storage/
        └── cvr_cache.json                  # Local CVR response cache
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/audits` | Upload invoice image, run audit |
| `GET` | `/api/v1/audits` | List audits (filter by `status`, paginate with `limit`/`offset`) |
| `GET` | `/api/v1/audits/{audit_id}` | Get a single audit by ID |

## How It Works

1. **Image preprocessing** — uploaded images are converted to standardized JPEG
2. **Pydantic AI agent** — a GPT-4o-mini agent extracts structured data from the image, calling tools:
   - `lookup_vat` — checks each line item against Danish VAT rules
   - `validate_cvr` — validates vendor CVR numbers against the Danish business registry
3. **Deterministic post-processing** — VAT math verification, currency handling, and status assignment run as plain Python (not LLM) for reliability
4. **Result** — the invoice is classified as Green (auto-approved), Review, or Red (issues found)

## Disclaimer

This is an **MVP**. Data is processed locally or via API. Ensure you comply with GDPR and the Danish Bookkeeping Act when handling real financial data.
