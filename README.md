# AI Invoice Agent

**The AI-Powered CFO for Danish SMEs.**
A "Human-in-the-Loop" auditing tool that extracts data from invoices, validates Danish CVR numbers, handles split-VAT logic for grocery receipts, and flags anomalies before they hit your accounting software.

Built with **Pydantic AI** for structured LLM extraction with tool calling, and **Streamlit** for the UI.

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

```bash
uv run streamlit run app.py
```

Then upload an invoice image from `data/example_invoices/` to test.

## Project Structure

```
invoice-auditor/
├── app.py                                  # Streamlit UI
├── pyproject.toml                          # Dependencies & build config
├── .env                                    # API keys (not committed)
├── data/
│   └── example_invoices/                   # Sample invoices for testing
└── src/invoice_auditor/
    ├── agent/
    │   └── auditor.py                      # Pydantic AI agent, tools & orchestration
    ├── api/
    │   └── cvr_manager.py                  # Async CVR registry validation
    ├── core/
    │   ├── schema.py                       # Pydantic models (Invoice, AuditResult, LineItem, etc.)
    │   └── vat_manager.py                  # VAT rule lookup engine
    └── storage/
        ├── vat_lookup.json                 # VAT exemption rules ("Pant", "Avis", etc.)
        └── cvr_cache.json                  # Local CVR response cache
```

## How It Works

1. **Image preprocessing** — uploaded images are converted to standardized JPEG
2. **Pydantic AI agent** — a GPT-4o-mini agent extracts structured data from the image, calling tools:
   - `lookup_vat` — checks each line item against Danish VAT rules
   - `validate_cvr` — validates vendor CVR numbers against the Danish business registry
3. **Deterministic post-processing** — VAT math verification, currency handling, and status assignment run as plain Python (not LLM) for reliability
4. **Result** — the invoice is classified as Green (auto-approved), Review, or Red (issues found)

## Disclaimer

This is an **MVP**. Data is processed locally or via API. Ensure you comply with GDPR and the Danish Bookkeeping Act when handling real financial data.
