import { tg } from "./telegram";
import type { Agent, DiaryEntry, Goal, Profile, ProfileUpdate, StartDialogResponse } from "./types";

/**
 * Backend base URL. Empty in dev (Vite proxies /api to the local backend) and
 * when the backend serves the frontend on the same origin. On split deploys
 * (frontend on Vercel, backend on Railway) set VITE_API_URL to the backend URL.
 */
const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `tma ${tg?.initData ?? ""}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  getProfile: () => request<Profile>("/api/me"),
  updateProfile: (payload: ProfileUpdate) =>
    request<Profile>("/api/me", { method: "PATCH", body: JSON.stringify(payload) }),

  getGoal: () => request<Goal | null>("/api/goal"),
  setGoal: (text: string) =>
    request<Goal>("/api/goal", { method: "POST", body: JSON.stringify({ text }) }),
  closeGoal: () => request<Goal>("/api/goal/close", { method: "POST" }),

  getDiary: () => request<DiaryEntry[]>("/api/diary"),
  addDiaryEntry: (text: string) =>
    request<DiaryEntry>("/api/diary", { method: "POST", body: JSON.stringify({ text }) }),
  deleteDiaryEntry: (id: string) => request<void>(`/api/diary/${id}`, { method: "DELETE" }),

  getAgents: () => request<Agent[]>("/api/agents"),
  startDialog: (agentId: string, message = "") =>
    request<StartDialogResponse>(`/api/agents/${agentId}/dialog`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
