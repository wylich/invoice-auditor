# core/schema.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from datetime import date, datetime

# 1. ENUMS & CONSTANTS
# We define fixed options so the AI doesn't invent new currencies or status types.
CURRENCY_TYPES = Literal["DKK", "USD", "EUR", "GBP", "SEK", "NOK"]
VAT_TYPES = Literal["Standard (25%)", "Reduced (0%)", "Exempt", "Unknown"]
STATUS_TYPES = Literal["Pending", "Green", "Red", "Review"]

class AuditFlag(BaseModel):
    """
    Represents a specific issue found during the audit.
    Example: severity="High", message="Vendor CVR is inactive."
    """
    category: Literal["Compliance", "Forex", "Anomaly", "Data Integrity"]
    severity: Literal["Low", "Medium", "High"]
    message: str
    is_resolved: bool = False

class LineItem(BaseModel):
    """
    Granular detail for split-VAT scenarios (e.g., a Føtex receipt).
    """
    description: str = Field(..., description="Name of the item, e.g., 'Arla Mælk'")
    quantity: float = Field(default=1.0)
    unit_price: float
    total_price: float
    vat_rate: float = Field(..., description="The VAT percentage, e.g., 0.25 for 25%")
    vat_category: VAT_TYPES = Field(..., description="Classification of the tax rule")

    # AI Prediction Confidence
    ai_confidence: float = Field(..., ge=0, le=1, description="0.0 to 1.0 confidence score")

class AuditResult(BaseModel):
    """What the Pydantic AI agent returns — extraction output without app metadata."""
    vendor_name: str
    vendor_cvr: Optional[str] = None
    invoice_date: date
    invoice_time: Optional[str] = None
    currency: CURRENCY_TYPES
    prices_include_vat: bool = Field(..., description="True if line item prices are VAT-inclusive (most Danish receipts), False if prices are shown excluding VAT (some B2B invoices)")
    total_amount_raw: float
    total_vat_raw: float
    line_items: List[LineItem]
    audit_flags: List[AuditFlag] = Field(default_factory=list)


class Invoice(BaseModel):
    """
    The Master Object. This serves as the 'Single Source of Truth'.
    """
    # -- METADATA --
    id: str = Field(..., description="Unique UUID for internal tracking")
    filename: str
    upload_timestamp: datetime = Field(default_factory=datetime.now)

    # -- EXTRACTED DATA (The "Raw" Reads) --
    vendor_name: str = Field(..., description="Name as it appears on the receipt")
    vendor_cvr: Optional[str] = Field(None, description="8-digit Danish CVR number")
    invoice_date: date
    # We capture time to prevent duplicates (e.g., lunch at 12:43:01)
    invoice_time: Optional[str] = Field(None, description="HH:MM:SS if available")

    currency: CURRENCY_TYPES
    prices_include_vat: bool = Field(..., description="True if line item prices are VAT-inclusive")
    total_amount_raw: float = Field(..., description="Total amount in original currency")
    total_vat_raw: float = Field(..., description="Total VAT in original currency")

    # -- CALCULATED / NORMALIZED DATA (The "Logic" Layer) --
    # Everything here is converted to DKK for the Danish accounting system
    total_amount_dkk: float
    exchange_rate_used: float = Field(default=1.0, description="Rate used for conversion. 1.0 if DKK")

    # -- AGENTIC ANALYSIS --
    line_items: List[LineItem] = Field(default_factory=list)
    audit_flags: List[AuditFlag] = Field(default_factory=list)

    # -- FINAL STATUS --
    status: STATUS_TYPES = "Pending"
    user_notes: Optional[str] = None

    # -- VALIDATORS (Python logic that runs automatically) --

    @field_validator('vendor_cvr')
    def validate_cvr(cls, v):
        if v and (len(v) != 8 or not v.isdigit()):
            raise ValueError('CVR must be exactly 8 digits')
        return v

    def add_flag(self, category, severity, message):
        """Helper to easily add a red flag during processing."""
        self.audit_flags.append(AuditFlag(
            category=category,
            severity=severity,
            message=message
        ))
