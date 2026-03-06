import json
import logging
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from invoice_auditor.core.schema import STATUS_TYPES, Invoice
from invoice_auditor.agent.auditor import run_audit, run_audit_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")
limiter = Limiter(key_func=get_remote_address)

_audit_store: dict[str, Invoice] = {}

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


class AuditListResponse(BaseModel):
    total: int
    audits: list[Invoice]


@router.post("/audits", response_model=Invoice)
@limiter.limit("5/minute;100/day")
async def create_audit(request: Request, file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    contents = await file.read()
    try:
        invoice = await run_audit(BytesIO(contents), file.filename, file.content_type)
    except Exception:
        logger.exception("run_audit failed for %s", file.filename)
        raise HTTPException(status_code=502, detail="Audit service failed")
    _audit_store[invoice.id] = invoice
    return invoice


@router.post("/audits/stream")
@limiter.limit("5/minute;100/day")
async def create_audit_stream(request: Request, file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    contents = await file.read()
    filename = file.filename
    content_type = file.content_type

    async def generate():
        async for event in run_audit_stream(BytesIO(contents), filename, content_type):
            if event.get("type") == "complete":
                invoice = Invoice(**event["invoice"])
                _audit_store[invoice.id] = invoice
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
