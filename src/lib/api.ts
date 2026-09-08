/**
 * API client — thin wrapper around fetch for the FastAPI backend.
 * All errors bubble up as thrown Error objects with descriptive messages.
 */

import { API_BASE_URL } from "@/constants";
import type {
  Document,
  Fact,
  Relationship,
  ProcessingStatus,
} from "@/types";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const isFormData = options.body instanceof FormData;

  const headers = isFormData
    ? { ...options.headers } // let the browser set Content-Type + multipart boundary itself
    : { "Content-Type": "application/json", ...options.headers };

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;

  return res.json() as Promise<T>;
}

// --------------------------------------------------------------------------- //
//  Documents
// --------------------------------------------------------------------------- //

export const documentsApi = {
  list: (): Promise<Document[]> =>
    request<Document[]>("/documents/"),

  get: (id: number): Promise<Document> =>
    request<Document>(`/documents/${id}`),

  upload: (file: File): Promise<Document> => {
    const form = new FormData();
    form.append("file", file);
    return request<Document>("/documents/upload", {
      method: "POST",
      headers: {},
      body: form,
    });
  },

  delete: (id: number): Promise<void> =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),

  status: (id: number): Promise<ProcessingStatus> =>
    request<ProcessingStatus>(`/documents/${id}/status`),
};

// --------------------------------------------------------------------------- //
//  Facts
// --------------------------------------------------------------------------- //

export const factsApi = {
  list: (params?: { document_id?: number; skip?: number; limit?: number }): Promise<Fact[]> => {
    const qs = new URLSearchParams();
    if (params?.document_id !== undefined)
      qs.set("document_id", String(params.document_id));
    if (params?.skip !== undefined) qs.set("skip", String(params.skip));
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    const query = qs.toString() ? `?${qs}` : "";
    return request<Fact[]>(`/facts/${query}`);
  },

  get: (id: number): Promise<Fact> => request<Fact>(`/facts/${id}`),
};

// --------------------------------------------------------------------------- //
//  Relationships
// --------------------------------------------------------------------------- //

export const relationshipsApi = {
  list: (params?: {
    category?: string;
    document_id?: number;
    skip?: number;
    limit?: number;
  }): Promise<Relationship[]> => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.document_id !== undefined)
      qs.set("document_id", String(params.document_id));
    if (params?.skip !== undefined) qs.set("skip", String(params.skip));
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    const query = qs.toString() ? `?${qs}` : "";
    return request<Relationship[]>(`/relationships/${query}`);
  },

  get: (id: number): Promise<Relationship> =>
    request<Relationship>(`/relationships/${id}`),
};
