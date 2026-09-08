export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

export const RELATIONSHIP_LABELS: Record<string, string> = {
  corroboration: "Corroboration",
  contradiction: "Contradiction",
  context_explained: "Context-Explained",
};

export const RELATIONSHIP_DESCRIPTIONS: Record<string, string> = {
  corroboration:
    "The same fact confirmed across two or more documents.",
  contradiction:
    "A genuine conflict between facts that cannot be reconciled by context.",
  context_explained:
    "An apparent conflict reconciled by time period, data vintage, scope, or units.",
};

export const STATUS_LABELS: Record<string, string> = {
  uploaded: "Queued",
  processing: "Processing",
  done: "Complete",
  error: "Error",
};

export const POLL_INTERVAL_MS = 3000;
