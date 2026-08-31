import type { Proposal, ProposalCreate, ProposalListItem } from "../types/proposal";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // fall back to default detail
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function createProposal(payload: ProposalCreate): Promise<Proposal> {
  return request<Proposal>("/api/proposals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listProposals(): Promise<ProposalListItem[]> {
  return request<ProposalListItem[]>("/api/proposals");
}

export function getProposal(id: number): Promise<Proposal> {
  return request<Proposal>(`/api/proposals/${id}`);
}

export function generateProposal(id: number): Promise<Proposal> {
  return request<Proposal>(`/api/proposals/${id}/generate`, { method: "POST" });
}

export function approveProposal(id: number): Promise<Proposal> {
  return request<Proposal>(`/api/proposals/${id}/approve`, { method: "POST" });
}

export function sendProposal(id: number): Promise<Proposal> {
  return request<Proposal>(`/api/proposals/${id}/send`, { method: "POST" });
}
