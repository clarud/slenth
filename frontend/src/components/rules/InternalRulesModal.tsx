import { useState, useEffect } from "react";
import { X, CheckCircle, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { createInternalRulesFromText } from "@/api/client";
import toast from "react-hot-toast";
import Spinner from "@/components/ui/Spinner";
import type { InternalRulesPayload } from "@/types/api";

interface InternalRulesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const InternalRulesModal = ({ isOpen, onClose, onSuccess }: InternalRulesModalProps) => {
  const [text, setText] = useState("");
  const [isValid, setIsValid] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    
    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  const validateJSON = () => {
    if (!text.trim()) {
      setIsValid(false);
      setValidationError("");
      return;
    }

    try {
      const parsed = JSON.parse(text);
      
      // Normalize to { rules: [...] } format
      let normalized: InternalRulesPayload;
      if (Array.isArray(parsed)) {
        normalized = { rules: parsed };
      } else if (parsed.rules && Array.isArray(parsed.rules)) {
        normalized = parsed;
      } else {
        throw new Error("JSON must be an array or an object with a 'rules' array");
      }

      // Validate at least one rule
      if (normalized.rules.length === 0) {
        throw new Error("At least one rule is required");
      }

      // Basic validation of rule structure
      normalized.rules.forEach((rule, idx) => {
        // Required fields: text, effective_date
        if (!rule.text) {
          throw new Error(`Rule ${idx + 1}: 'text' is required`);
        }
        if (!rule.effective_date) {
          throw new Error(`Rule ${idx + 1}: 'effective_date' is required (format: YYYY-MM-DD)`);
        }
        
        // Validate date format if provided
        if (rule.effective_date && !/^\d{4}-\d{2}-\d{2}$/.test(rule.effective_date)) {
          throw new Error(`Rule ${idx + 1}: 'effective_date' must be in YYYY-MM-DD format`);
        }
        if (rule.sunset_date && !/^\d{4}-\d{2}-\d{2}$/.test(rule.sunset_date)) {
          throw new Error(`Rule ${idx + 1}: 'sunset_date' must be in YYYY-MM-DD format`);
        }
      });

      setIsValid(true);
      setValidationError("");
    } catch (error) {
      setIsValid(false);
      setValidationError(error instanceof Error ? error.message : "Invalid JSON");
    }
  };

  const handleSubmit = async () => {
    if (!isValid) return;

    setSubmitting(true);
    try {
      const parsed = JSON.parse(text);
      let payload: InternalRulesPayload;
      
      if (Array.isArray(parsed)) {
        payload = { rules: parsed };
      } else {
        payload = parsed;
      }

      const response = await createInternalRulesFromText(payload);
      
      const parts = [];
      if (response.total_rules) parts.push(`Total: ${response.total_rules}`);
      if (response.created) parts.push(`Created: ${response.created}`);
      if (response.updated) parts.push(`Updated: ${response.updated}`);
      if (response.skipped) parts.push(`Skipped: ${response.skipped}`);
      
      toast.success(
        parts.length > 0
          ? `Rules uploaded successfully! ${parts.join(", ")}`
          : response.message || "Rules uploaded successfully!"
      );
      
      setText("");
      setIsValid(false);
      onSuccess();
      onClose();
    } catch (error) {
      toast.error("Failed to upload rules");
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Overlay */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-4xl max-h-[90vh] mx-4 bg-card rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-foreground">
                  Add Internal Rules
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Paste your rules JSON below (array or object with "rules" key)
                </p>
              </div>
              <button
                onClick={onClose}
                className="btn-ghost p-2 shrink-0"
                aria-label="Close modal"
                disabled={submitting}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <div className="space-y-2">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={`Paste your JSON here:\n\n{\n  "rules": [\n    {\n      "text": "Transactions that deviate from customer patterns must be flagged for review",\n      "section": "AML_UNUSUAL_ACTIVITY_MONITORING",\n      "obligation_type": "mandatory",\n      "conditions": ["transaction_frequency > 2x average_past_3_months", "amount > 50000"],\n      "expected_evidence": ["Case escalation record", "EDD report"],\n      "penalty_level": "high",\n      "effective_date": "2025-01-01",\n      "version": "v1.0",\n      "source": "Internal AML Monitoring Framework"\n    }\n  ]\n}`}
                className="w-full h-80 p-4 font-mono text-sm rounded-lg border border-input bg-background resize-none focus-ring"
                disabled={submitting}
              />
              
              {validationError && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                  <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                  <p className="text-sm text-destructive">{validationError}</p>
                </div>
              )}

              {isValid && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-success/10 border border-success/20">
                  <CheckCircle className="h-4 w-4 text-success shrink-0 mt-0.5" />
                  <p className="text-sm text-success-foreground">
                    Valid JSON structure detected
                  </p>
                </div>
              )}
            </div>

            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
                Expected JSON format (click to expand)
              </summary>
              <div className="mt-2 p-4 rounded-lg bg-muted/50 border border-border">
                <pre className="text-xs overflow-x-auto">
{`// Option A: Wrapper object (recommended)
{
  "rules": [
    {
      "text": "Transactions that significantly deviate from a customer's historical patterns must be flagged for enhanced review",
      "section": "AML_UNUSUAL_ACTIVITY_MONITORING",
      "obligation_type": "mandatory",
      "conditions": [
        "transaction_frequency > 2x average_past_3_months",
        "amount > 50000",
        "destination_country in ['HighRiskList']"
      ],
      "expected_evidence": [
        "Case escalation record",
        "Enhanced Due Diligence (EDD) report",
        "Customer risk profile summary"
      ],
      "penalty_level": "high",
      "effective_date": "2025-01-01",
      "version": "v1.0",
      "source": "Internal AML Monitoring Framework"
    }
  ]
}

// Option B: Bare array (auto-wrapped)
[
  {
    "text": "All cash transactions exceeding CHF 100,000 must be reported",
    "section": "AML_CASH_REPORTING",
    "obligation_type": "mandatory",
    "conditions": ["amount > 100000"],
    "expected_evidence": ["Transaction receipt", "CTR filing"],
    "penalty_level": "high",
    "effective_date": "2025-01-01",
    "version": "v1.0",
    "source": "Internal Policy Manual"
  }
]

// Required fields: text, effective_date
// Optional fields: rule_id (for updates), section, obligation_type, conditions,
//                  expected_evidence, penalty_level, sunset_date, version, source, metadata
// Note: If rule_id is provided, will update existing rule by ID`}
                </pre>
              </div>
            </details>
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border flex justify-end gap-3">
            <button
              onClick={onClose}
              className="btn-ghost"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={validateJSON}
              className="btn-outline"
              disabled={!text.trim() || submitting}
            >
              Validate
            </button>
            <button
              onClick={handleSubmit}
              className="btn-primary min-w-24"
              disabled={!isValid || submitting}
            >
              {submitting ? <Spinner size="sm" /> : "Submit"}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default InternalRulesModal;
