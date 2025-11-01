import axios from "axios";
import { API } from "@/config";
import type {
  Transaction,
  TransactionStatus,
  ComplianceReport,
  UploadedDocument,
  RulesResponse,
  RulesFilters,
  InternalRulesPayload,
  InternalRulesUploadResponse,
} from "@/types/api";

const api = axios.create({
  baseURL: API.BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Transactions
export const fetchTransactions = async (): Promise<Transaction[]> => {
  const { data } = await api.get(API.LIST_TRANSACTIONS_PATH);
  return data;
};

export const fetchTransactionStatus = async (
  id: string
): Promise<TransactionStatus> => {
  const { data } = await api.get(API.TRANSACTION_STATUS_PATH(id));
  return data;
};

export const fetchTransactionCompliance = async (
  id: string
): Promise<ComplianceReport> => {
  const { data } = await api.get(API.TRANSACTION_COMPLIANCE_PATH(id));
  return data;
};

// Documents
export const uploadDocument = async (file: File): Promise<UploadedDocument> => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post(API.DOCUMENT_UPLOAD_PATH, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

// Rules
export const fetchRules = async (
  filters: RulesFilters = {}
): Promise<RulesResponse> => {
  const params: Record<string, any> = {};
  
  if (filters.search) params.search = filters.search;
  if (filters.rule_type && filters.rule_type !== "all")
    params.rule_type = filters.rule_type;
  if (filters.regulator) params.regulator = filters.regulator;
  if (filters.jurisdiction) params.jurisdiction = filters.jurisdiction;
  if (filters.section) params.section = filters.section;
  if (filters.is_active !== undefined) params.is_active = filters.is_active;
  if (filters.page) params.page = filters.page;
  if (filters.page_size) params.page_size = filters.page_size;

  const { data } = await api.get(API.RULES_ALL_PATH, { params });
  return data;
};

// Internal Rules Upload
export const createInternalRulesFromText = async (
  payload: InternalRulesPayload
): Promise<InternalRulesUploadResponse> => {
  try {
    // Try JSON POST first (preferred)
    const { data } = await api.post(API.INTERNAL_RULES_TEXT_PATH, payload);
    return data;
  } catch (error) {
    if (axios.isAxiosError(error) && (error.response?.status === 404 || error.response?.status === 405)) {
      // Fallback to multipart upload
      const jsonString = JSON.stringify(payload, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      const file = new File([blob], "internal_rules.json", {
        type: "application/json",
      });
      
      const formData = new FormData();
      formData.append("file", file);
      
      const { data } = await api.post(API.INTERNAL_RULES_UPLOAD_PATH, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    }
    throw error;
  }
};
