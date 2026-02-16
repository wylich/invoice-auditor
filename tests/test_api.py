from invoice_auditor.core.schema import Invoice


# -- Health check --


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# -- POST /api/v1/audits --


def test_create_audit(client, mock_run_audit):
    resp = client.post(
        "/api/v1/audits",
        files={"file": ("receipt.jpg", b"\xff\xd8\xff\xe0fake-jpeg", "image/jpeg")},
    )
    assert resp.status_code == 200
    invoice = Invoice(**resp.json())
    assert invoice.vendor_name == "Netto"
    mock_run_audit.assert_called_once()


def test_create_audit_invalid_content_type(client, mock_run_audit):
    resp = client.post(
        "/api/v1/audits",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    mock_run_audit.assert_not_called()


def test_create_audit_filename_preserved(client, mock_run_audit, sample_invoice):
    resp = client.post(
        "/api/v1/audits",
        files={"file": ("receipt.jpg", b"\xff\xd8\xff\xe0fake-jpeg", "image/jpeg")},
    )
    assert resp.json()["filename"] == sample_invoice.filename


# -- GET /api/v1/audits --


def test_list_audits_empty(client):
    resp = client.get("/api/v1/audits")
    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "audits": []}


def test_list_audits(client, populated_store):
    resp = client.get("/api/v1/audits")
    body = resp.json()
    assert body["total"] == 1
    assert body["audits"][0]["id"] == populated_store["id"]


def test_list_audits_filter_by_status(client, mock_run_audit, sample_invoice):
    # Create an audit (status="Green" from sample_invoice)
    client.post(
        "/api/v1/audits",
        files={"file": ("a.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg")},
    )

    resp = client.get("/api/v1/audits", params={"status": "Green"})
    assert resp.json()["total"] == 1

    resp = client.get("/api/v1/audits", params={"status": "Red"})
    assert resp.json()["total"] == 0


def test_list_audits_pagination(client, mock_run_audit, sample_invoice):
    # Insert 3 audits with distinct IDs
    for i in range(3):
        sample_invoice_copy = sample_invoice.model_copy(update={"id": f"id-{i}"})
        mock_run_audit.return_value = sample_invoice_copy
        client.post(
            "/api/v1/audits",
            files={"file": (f"{i}.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg")},
        )

    resp = client.get("/api/v1/audits", params={"limit": 2, "offset": 0})
    body = resp.json()
    assert body["total"] == 3
    assert len(body["audits"]) == 2

    resp = client.get("/api/v1/audits", params={"limit": 2, "offset": 2})
    body = resp.json()
    assert body["total"] == 3
    assert len(body["audits"]) == 1


# -- GET /api/v1/audits/{audit_id} --


def test_get_audit(client, populated_store):
    audit_id = populated_store["id"]
    resp = client.get(f"/api/v1/audits/{audit_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == audit_id


def test_get_audit_not_found(client):
    resp = client.get("/api/v1/audits/nonexistent")
    assert resp.status_code == 404
