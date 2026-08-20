/**
 * API types mirroring the backend Pydantic schemas (app/api/schemas.py).
 * Regenerate with `npm run generate:api` when the backend contract changes.
 */

export interface Profile {
  id: number;
  language: string;
  name: string;
  gender: string;
  birthDate: string | null;
  age: number | null;
  country: string;
  location: string;
  activity: string;
  interests: string;
  mainGoal: string;
  currentProblem: string;
  plan: string;
  tokens: number;
  activeAgent: string | null;
}

export interface ProfileUpdate {
  name?: string;
  gender?: string;
  birthDate?: string;
  country?: string;
  location?: string;
  activity?: string;
  interests?: string;
  mainGoal?: string;
  currentProblem?: string;
  language?: string;
}

export interface Goal {
  id: string;
  text: string;
  status: "active" | "closed";
  created_at: string;
  closed_at: string | null;
}

export interface DiaryEntry {
  id: string;
  text: string;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
}

export interface StartDialogResponse {
  ok: boolean;
  agentName: string;
  botUsername: string;
}

export interface BillingStatus {
  plan: "Free" | "Trial" | "Pro";
  dailyMode: "prompt" | "rag";
  dailyUsed: number;
  dailyLimit: number;
  dailyRemaining: number;
  promptUsed: number;
  promptLimit: number;
  ragUsed: number;
  ragLimit: number;
  trialTotalUsed: number;
  trialTotalLimit: number;
  councilUsed: number;
  councilLimit: number;
  councilRemaining: number;
  canStartTrial: boolean;
  trialStartedAt: string | null;
  trialExpiresAt: string | null;
  proExpiresAt: string | null;
  proAutoRenew: boolean;
  proPriceStars: number;
}

export interface Checkout {
  invoiceLink: string;
  priceStars: number;
}
