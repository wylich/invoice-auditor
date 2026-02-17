export type Status = "Pending" | "Green" | "Red" | "Review";

export type Currency = "DKK" | "USD" | "EUR" | "GBP" | "SEK" | "NOK";

export type FlagCategory = "Compliance" | "Forex" | "Anomaly" | "Data Integrity";

export type FlagSeverity = "Low" | "Medium" | "High";

export type VatCategory =
  | "Standard (25%)"
  | "Reduced (0%)"
  | "Exempt"
  | "Unknown";

export interface AuditFlag {
  category: FlagCategory;
  severity: FlagSeverity;
  message: string;
  is_resolved: boolean;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number | null;
  total_price: number | null;
  vat_rate: number | null;
  vat_category: VatCategory | null;
  ai_confidence: number;
}

export interface Invoice {
  id: string;
  filename: string;
  upload_timestamp: string;
  vendor_name: string;
  vendor_cvr: string | null;
  invoice_date: string;
  invoice_time: string | null;
  currency: Currency;
  prices_include_vat: boolean;
  total_amount_raw: number;
  total_vat_raw: number;
  total_amount_dkk: number;
  exchange_rate_used: number;
  line_items: LineItem[];
  audit_flags: AuditFlag[];
  status: Status;
  user_notes: string | null;
}

export interface AuditListResponse {
  total: number;
  audits: Invoice[];
}
