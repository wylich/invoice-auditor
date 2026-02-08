# core/auditor.py
import json
import os
import base64
import io
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

# Image processing
from PIL import Image

# Import our helper modules
from .schema import Invoice, AuditFlag, LineItem
from .vat_manager import VatManager
from .cvr_manager import CvrManager

# API Client (e.g., OpenAI / OpenRouter)
from openai import OpenAI 
from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env

SYSTEM_PROMPT = """
    You are "Invoice Agent," an expert AI Financial Auditor for Danish SMEs. 
    Your goal is to extract structured financial data from receipts and invoices with 100% precision. 

    ### 1. CONTEXT & ROLE
    - You are auditing for Danish companies.
    - You must handle Danish formatting (e.g., "1.250,00" means 1250.00).
    - You must identify specific VAT (Moms) codes found on receipts (e.g., 'A', 'B', 'Momsfri').

    ### 2. EXTRACTION RULES

    **A. Vendor Details**
    - **Name:** Extract the business name (e.g., "Netto", "7-Eleven").
    - **CVR:** Look for "CVR", "SE-nr", or "VAT-nr". It is always an 8-digit number. If not found, return null.
        Make sure you do not take the customer's CVR by mistake. You must not invent a CVR.

    **B. Dates & Currency**
    - **Date:** Return in ISO 8601 format (YYYY-MM-DD).
    - **Time:** Extract timestamp if available (HH:MM:SS). Crucial for duplicate detection.
    - **Currency:** Detect currency (DKK, EUR, USD). If symbol is "kr.", assume DKK.

    **C. Line Items (CRITICAL)**
    - You MUST extract every single line item for grocery/supermarket receipts.
    - **Split VAT Logic:**
    - Look for indicators like "Pant", "Avis", "Frimærker", or "Momsfri".
    - If an item is "Pant" (Bottle deposit), set `vat_rate` to 0.0 and `vat_category` to "Exempt".
    - If an item is standard goods, set `vat_rate` to 0.25 and `vat_category` to "Standard (25%)".
    - Use the receipt's own tax codes (e.g., "A" vs "B" next to price) to guide you.

    **D. Totals**
    - `total_amount_raw`: The final amount to be paid (inclusive of VAT).
    - `total_vat_raw`: The total VAT amount shown on the receipt.

    ### 3. OUTPUT SCHEMA
    You must output ONLY valid JSON matching this structure. Do not include markdown formatting or chatter.

    {
    "vendor_name": "string",
    "vendor_cvr": "string or null",
    "invoice_date": "YYYY-MM-DD",
    "invoice_time": "HH:MM:SS or null",
    "currency": "DKK",
    "total_amount_raw": float,
    "total_vat_raw": float,
    "line_items": [
        {
        "description": "string",
        "quantity": float,
        "unit_price": float,
        "total_price": float,
        "vat_rate": float (e.g. 0.25),
        "vat_category": "Standard (25%)" or "Exempt" or "Reduced (0%)",
        "ai_confidence": float (0.0 to 1.0)
        }
    ]
    }

    ### 4. EDGE CASES
    - If the image is blurry, set `ai_confidence` low.
    - If handwritten, do your best guess but flag confidence < 0.8.
    - If multiple currencies appear, use the final payment currency.
    """

class Auditor:
    def __init__(self, api_key: Optional[str] = None):
        self.vat_agent = VatManager()
        self.cvr_agent = CvrManager()
        self.api_key = api_key

        # Initialize API Client
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def run_audit(self, file_object: Any, filename: str) -> Invoice:
            """
            Orchestrates the entire flow: Pre-process -> Vision -> Logic -> Compliance
            
            Args:
                file_object: The bytes/buffer from Streamlit (st.uploaded_file)
                filename: The original filename (for metadata)
            """
            print(f"🕵️ Auditor: Starting analysis on {filename}...")

            # STEP 0: IMAGE PRE-PROCESSING (Crucial for WebP/AVIF support)
            # We convert everything to a standardized, compressed JPEG Base64 string.
            # This ensures the LLM can read it, regardless of original format.
            base64_image = self._process_image(file_object)

            # STEP 1: VISION EXTRACTION (The LLM Call)
            # In mock mode, we ignore the image and return fake data.
            # In real mode, we pass 'base64_image' to the API.
            real = True # Toggle for real vs mock
            if real:
                print("🚀 Sending to OpenAI (gpt-4o-mini)...")
                raw_data = self._call_llm(base64_image)
                print(raw_data) # Debug: See raw LLM output
            else:
                print("🛠️ No API Key found. Using mock data.")
                raw_data = self._mock_vision_extraction(filename)
            
            # --- FIX: INJECT MISSING FIELDS BEFORE VALIDATION ---
            # The AI doesn't know about these app-specific fields, so we add them here.
            
            # 1. Generate ID
            raw_data["id"] = str(uuid.uuid4())
            
            # 2. Add Filename
            raw_data["filename"] = filename
            
            # 3. Initialize DKK amount (Will be recalculated in _audit_currency if needed)
            # We default it to the raw amount so Pydantic is happy.
            if "total_amount_dkk" not in raw_data:
                raw_data["total_amount_dkk"] = raw_data.get("total_amount_raw", 0.0)
            # -----------------------------------------------------

            # STEP 2: BUILD THE INVOICE OBJECT (Schema Enforcement)
            try:
                invoice = Invoice(**raw_data)
            except Exception as e:
                print(f"❌ JSON Validation Failed: {e}")
                raise ValueError("AI output could not be parsed. Try a clearer image.")

            # STEP 3: LOGIC CHECKS
            self._audit_vat_logic(invoice)
            self._audit_compliance(invoice)
            self._audit_currency(invoice)

            # STEP 4: FINAL STATUS
            if invoice.audit_flags:
                invoice.status = "Red" if any(f.severity == "High" for f in invoice.audit_flags) else "Review"
            else:
                invoice.status = "Green"

            return invoice
    
    # V2: Actual LLM Call
    def _call_llm(self, image_base64):
        """
        Calls Official OpenAI API with the System Prompt and Image.
        """
        # --- SAFETY GUARD START ---
        if not self.client:
            raise ValueError("OpenAI Client is not initialized. API Key is missing.")
        # --- SAFETY GUARD END ---

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Analyze this receipt image and extract data as JSON."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]}
            ],
            response_format={"type": "json_object"} # Ensures JSON output
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def _process_image(self, file_object) -> str:
            """
            Standardizes input images (AVIF, WebP, PNG) to JPEG Base64.
            """
            try:
                # 1. Open Image (PIL handles formats automatically)
                image = Image.open(file_object)
                
                # 2. Convert to RGB (Required for JPEG saving, removes Transparency)
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                
                # 3. Resize if massive (Optional optimization for cost)
                max_size = (1024, 1024)
                image.thumbnail(max_size)

                # 4. Save to Buffer as JPEG
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=85)
                buffer.seek(0)
                
                # 5. Encode to Base64
                return base64.b64encode(buffer.read()).decode('utf-8')
                
            except Exception as e:
                print(f"❌ Image Processing Error: {e}")
                raise ValueError("Could not process image. File might be corrupted or unsupported.")

    def _audit_vat_logic(self, invoice: Invoice):
        """
        Checks if the extracted VAT makes sense mathematically and legally.
        """
        calculated_vat = 0.0
        
        for item in invoice.line_items:
            # 1. Check against our VAT Dictionary (The "Pant" Rule)
            rule_rate, _, reason = self.vat_agent.lookup_item(item.description)
            
            # 2. If the AI extracted 25% but our Rule says 0% (e.g., Pant), we flag it.
            # (In a V2, we might auto-correct this, but for now we flag).
            if item.vat_rate != rule_rate:
                invoice.add_flag(
                    category="Data Integrity", 
                    severity="Medium", 
                    message=f"VAT Mismatch on '{item.description}'. AI saw {item.vat_rate*100}%, but rule '{reason}' expects {rule_rate*100}%."
                )
            
            calculated_vat += item.total_price * item.vat_rate

        # 3. Check Totals (allowing for small rounding errors)
        if abs(calculated_vat - invoice.total_vat_raw) > 0.05:
            invoice.add_flag(
                category="Data Integrity", 
                severity="High", 
                message=f"Math Error: Line items sum to {calculated_vat:.2f} VAT, but invoice total says {invoice.total_vat_raw:.2f}."
            )

    def _audit_compliance(self, invoice: Invoice):
        """
        Checks CVR Registry.
        """
        if invoice.vendor_cvr:
            risk_report = self.cvr_agent.validate_cvr(invoice.vendor_cvr)
            
            if not risk_report['valid']:
                invoice.add_flag(
                    category="Compliance",
                    severity=risk_report.get('risk_level', "High"),
                    message=f"CVR Alert: {risk_report.get('message')}"
                )
        else:
             invoice.add_flag("Compliance", "Medium", "No CVR number found on receipt.")

    def _audit_currency(self, invoice: Invoice):
        """
        Simple check to ensure we are converting foreign receipts.
        """
        if invoice.currency != "DKK":
            # For MVP, we just flag that conversion happened. 
            # In V2, this calls the Nationalbanken API.
            invoice.total_amount_dkk = invoice.total_amount_raw * invoice.exchange_rate_used
            invoice.add_flag("Forex", "Low", f"Converted from {invoice.currency} (Rate: {invoice.exchange_rate_used})")
        else:
            invoice.total_amount_dkk = invoice.total_amount_raw

    def _mock_vision_extraction(self, file_path) -> Dict:
        """
        Simulates what GPT-4o returns.
        """
        return {
            "id": "uuid-1234-5678",
            "filename": os.path.basename(file_path),
            "vendor_name": "Netto",
            "vendor_cvr": "35954716", # Valid Netto CVR
            "invoice_date": "2025-10-27",
            "invoice_time": "12:45:00",
            "currency": "DKK",
            "total_amount_raw": 150.00,
            "total_vat_raw": 30.00, # Intentionally wrong to trigger math check (should be <37.5)
            "total_amount_dkk": 150.00,
            "line_items": [
                {
                    "description": "Arla Sødmælk",
                    "quantity": 2,
                    "unit_price": 12.00,
                    "total_price": 24.00,
                    "vat_rate": 0.25,
                    "vat_category": "Standard (25%)",
                    "ai_confidence": 0.99
                },
                {
                    "description": "Coca Cola + Pant A", # Contains keyword "Pant"
                    "quantity": 1,
                    "unit_price": 20.00,
                    "total_price": 20.00,
                    "vat_rate": 0.25, # AI wrongly guesses 25% here to test our VAT Logic
                    "vat_category": "Standard (25%)",
                    "ai_confidence": 0.95
                }
            ]
        }