from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from invoice_auditor.api.app import create_app
from invoice_auditor.api.routes import _audit_store
from invoice_auditor.core.schema import Invoice


@pytest.fixture()
def client():
    return TestClient(create_app())


@pytest.fixture()
def sample_invoice() -> Invoice:
    return Invoice(
        id="test-uuid-1234",
        filename="receipt.jpg",
        upload_timestamp=datetime(2026, 2, 16, 10, 0, 0),
        vendor_name="Netto",
        vendor_cvr="12345678",
        invoice_date=date(2026, 2, 15),
        currency="DKK",
        prices_include_vat=True,
        total_amount_raw=125.0,
        total_vat_raw=25.0,
        total_amount_dkk=125.0,
        exchange_rate_used=1.0,
        status="Green",
        line_items=[],
        audit_flags=[],
    )


@pytest.fixture(autouse=True)
def _clear_store():
    _audit_store.clear()
    yield
    _audit_store.clear()


@pytest.fixture()
def mock_run_audit(sample_invoice):
    with patch(
        "invoice_auditor.api.routes.run_audit",
        new_callable=AsyncMock,
        return_value=sample_invoice,
    ) as mock:
        yield mock


@pytest.fixture()
def populated_store(client, mock_run_audit):
    resp = client.post(
        "/api/v1/audits",
        files={"file": ("receipt.jpg", b"\xff\xd8\xff\xe0fake-jpeg", "image/jpeg")},
    )
    assert resp.status_code == 200
    return resp.json()
