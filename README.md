# 🕵️ AI Invoice Agent (V1)

**The AI-Powered CFO for Danish SMEs.**
A "Human-in-the-Loop" auditing tool that extracts data from invoices, validates Danish CVR numbers, handles split-VAT logic for grocery receipts, and flags anomalies before they hit your accounting software.

## 🚀 Quick Start (using `uv`)

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

### 1. Initialize & Install Dependencies
Run the following commands to set up your environment and install the required packages (`streamlit`, `pydantic`, `httpx`, `cryptography`, `pillow`, `python-dotenv`, `openai`):

```bash
# Clone the repo (if applicable) or create directory
mkdir invoice-agent && cd invoice-agent

# Initialize uv project
uv init

# Install core dependencies
uv add streamlit pydantic httpx cryptography pillow python-dotenv openai
```

### 2. Setup Configuration
Create a .env file in the root directory for your API keys (optional for Mock Mode, required for Live Mode):

```bash
# .env
OPENAI_API_KEY="your_key_here"
# CVR_API_TOKEN="optional_if_using_paid_tier"
```

### 3. Run the App
Launch the Streamlit dashboard:

```bash
uv run streamlit run app.py
```

## 📂 Project Structure
```plaintext
invoice-agent/
├── app.py                # Frontend (Streamlit)
├── .env                  # API Keys
├── pyproject.toml        # Dependencies (managed by uv)
└── core/
    ├── auditor.py        # Main Logic (Orchestrator)
    ├── schema.py         # Pydantic Models (Data Contracts)
    ├── cvr_manager.py    # Compliance & CVR API Integration
    ├── vat_manager.py    # Split-VAT Logic
    └── vat_lookup.json   # Dictionary for "Pant" & "Avis" rules
```

## 🛠 Features (V1)
* __Agentic Workflow__: Simulates "Thinking" steps for UX purposes. This will be streamed from the API call in V2 when applicable.
* __Compliance Check__: Validates vendors against cvrapi.dk (Checks for Bankruptcy/Dissolution).
* __Split-VAT Logic__: Detailed rule-based checking for supermarket receipts (e.g., detecting "Pant" at 0% VAT).
* __Mock Mode__: Runs without an API key for demonstration purposes.

## ⚠️ Disclaimer
This is an __MVP (Minimum Viable Product)__. Data is processed locally or via API. Ensure you comply with GDPR and the Danish Bookkeeping Act when handling real financial data.
