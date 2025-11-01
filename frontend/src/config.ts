// Slenth Configuration - Centralized endpoints and brand tokens

export const BRAND = {
  name: "Slenth",
  tagline: "Compliance Intelligence Platform",
  logoUrl: "https://placeholder.svg?height=40&width=40", // Replace with actual logo
} as const;

export const API = {
  BASE_URL: "http://localhost:8000",
  
  // Dashboard - Transactions
  LIST_TRANSACTIONS_PATH: "/transactions",
  TRANSACTION_STATUS_PATH: (id: string) => `/transactions/${id}/status`,
  TRANSACTION_COMPLIANCE_PATH: (id: string) => `/transactions/${id}/compliance`,
  
  // Dashboard - Documents
  DOCUMENT_UPLOAD_PATH: "/documents/upload",
  
  // Rules - Fetch
  RULES_ALL_PATH: "/rules/all",
  RULES_EXTERNAL_PATH: "/rules/external",
  RULES_INTERNAL_PATH: "/rules/internal",
  
  // Rules - Create/Upload
  INTERNAL_RULES_TEXT_PATH: "/internal_rules", // Preferred: JSON POST
  INTERNAL_RULES_UPLOAD_PATH: "/internal_rules/upload", // Fallback: multipart file upload
} as const;

export const POLLING_INTERVAL = 10000; // 10 seconds
export const SEARCH_DEBOUNCE_MS = 300;
