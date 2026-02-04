# core/auditor.py
import json
import os
from datetime import datetime
from typing import Optional, Dict

# Import our helper modules
from .schema import Invoice, AuditFlag, LineItem
from .vat_manager import VatManager
from .cvr_manager import CvrManager

# Placeholder for our LLM Client (e.g., OpenAI / Anthropic)
# from openai import OpenAI 

class Auditor:
    def __init__(self, api_key: Optional[str] = None):
        self.vat_agent = VatManager()
        self.cvr_agent = CvrManager()
        self.api_key = api_key
        # self.client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    def run_audit(self, file_path: str) -> Invoice:
        """
        Orchestrates the entire flow: Vision -> Logic -> Compliance -> Result
        """
        print(f"🕵️ Auditor: Starting analysis on {os.path.basename(file_path)}...")

        # STEP 1: VISION EXTRACTION (The LLM Call)
        # In the final app, this sends the image to an LLM (e.g. GPT-4o).
        # Here, we simulate the AI's raw JSON output for demonstration.
        raw_data = self._mock_vision_extraction(file_path)
        
        # STEP 2: BUILD THE INVOICE OBJECT (Schema Enforcement)
        # This automatically validates data types (e.g., that date is a date)
        invoice = Invoice(**raw_data)

        # STEP 3: LOGIC CHECKS (The "Human-in-the-Loop" Rules)
        self._audit_vat_logic(invoice)
        self._audit_compliance(invoice)
        self._audit_currency(invoice)

        # STEP 4: FINAL STATUS DETERMINATION
        if invoice.audit_flags:
            invoice.status = "Red" if any(f.severity == "High" for f in invoice.audit_flags) else "Review"
        else:
            invoice.status = "Green"

        return invoice

    def _audit_vat_logic(self, invoice: Invoice):
        """
        Checks if the extracted VAT makes sense mathematically and legally.
        """
        calculated_vat = 0.0
        
        for item in invoice.line_items:
            # 1. Check against our VAT Dictionary (The "Pant" Rule)
            rule_rate, rule_cat, reason = self.vat_agent.lookup_item(item.description)
            
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
        Checks CVR and Vendor risks.
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