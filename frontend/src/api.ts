import type { Invoice, AuditListResponse, Status } from "./types";

const BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const API = `${BASE_URL}/api/v1`;

export async function createAudit(file: File): Promise<Invoice> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API}/audits`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Upload failed (${res.status})`);
  }

  return res.json();
}

export async function listAudits(params?: {
  status?: Status;
  limit?: number;
  offset?: number;
}): Promise<AuditListResponse> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.offset != null) search.set("offset", String(params.offset));

  const qs = search.toString();
  const res = await fetch(`${API}/audits${qs ? `?${qs}` : ""}`);

  if (!res.ok) {
    throw new Error(`Failed to list audits (${res.status})`);
  }

  return res.json();
}

export async function getAudit(id: string): Promise<Invoice> {
  const res = await fetch(`${API}/audits/${encodeURIComponent(id)}`);

  if (!res.ok) {
    throw new Error(`Failed to fetch audit (${res.status})`);
  }

  return res.json();
}
