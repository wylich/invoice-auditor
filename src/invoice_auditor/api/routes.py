from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile
from pydantic import BaseModel

from invoice_auditor.core.schema import STATUS_TYPES, Invoice
from invoice_auditor.agent.auditor import run_audit

router = APIRouter(prefix="/api/v1")

_audit_store: dict[str, Invoice] = {}

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class AuditListResponse(BaseModel):
    total: int
    audits: list[Invoice]


@router.post("/audits", response_model=Invoice)
async def create_audit(file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    contents = await file.read()
    invoice = await run_audit(BytesIO(contents), file.filename)
    _audit_store[invoice.id] = invoice
    return invoice


@router.get("/audits", response_model=AuditListResponse)
async def list_audits(
    status: Optional[STATUS_TYPES] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    audits = sorted(
        _audit_store.values(),
        key=lambda inv: inv.upload_timestamp,
        reverse=True,
    )

    if status is not None:
        audits = [a for a in audits if a.status == status]

    total = len(audits)
    audits = audits[offset : offset + limit]
    return AuditListResponse(total=total, audits=audits)


@router.get("/audits/{audit_id}", response_model=Invoice)
async def get_audit(audit_id: str):
    invoice = _audit_store.get(audit_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    return invoice
