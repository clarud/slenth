import { useEffect } from "react";
import { X, ExternalLink, Calendar, FileText, Tag } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { RuleItem } from "@/types/api";

interface RuleDetailModalProps {
  rule: RuleItem | null;
  onClose: () => void;
}

const RuleDetailModal = ({ rule, onClose }: RuleDetailModalProps) => {
  useEffect(() => {
    if (!rule) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    
    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [rule, onClose]);

  if (!rule) return null;

  const getBadgeClass = (type: string) => {
    return type === "internal" ? "badge-primary" : "badge-secondary";
  };

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
          className="relative w-full max-w-3xl max-h-[90vh] mx-4 bg-card rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-2">
                <h2 className="text-2xl font-bold text-foreground">{rule.title}</h2>
                <div className="flex flex-wrap gap-2">
                  <span className={`badge ${getBadgeClass(rule.rule_type)}`}>
                    {rule.rule_type}
                  </span>
                  {rule.regulator && (
                    <span className="badge-muted">{rule.regulator}</span>
                  )}
                  {rule.jurisdiction && (
                    <span className="badge-muted">{rule.jurisdiction}</span>
                  )}
                  {rule.section && (
                    <span className="badge-muted">{rule.section}</span>
                  )}
                  {rule.is_active && (
                    <span className="badge-success">Active</span>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="btn-ghost p-2 shrink-0"
                aria-label="Close modal"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Metadata Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-start gap-2">
                <Tag className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs text-muted-foreground">Rule ID</p>
                  <p className="text-sm font-mono text-foreground">{rule.rule_id}</p>
                </div>
              </div>

              {rule.effective_date && (
                <div className="flex items-start gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs text-muted-foreground">Effective Date</p>
                    <p className="text-sm font-medium text-foreground">
                      {rule.effective_date}
                    </p>
                  </div>
                </div>
              )}

              {rule.version && (
                <div className="flex items-start gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs text-muted-foreground">Version</p>
                    <p className="text-sm font-medium text-foreground">{rule.version}</p>
                  </div>
                </div>
              )}

              <div className="flex items-start gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs text-muted-foreground">Created</p>
                  <p className="text-sm font-medium text-foreground">
                    {new Date(rule.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>

            {rule.source && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Source</p>
                <a
                  href={rule.source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline flex items-center gap-1 text-sm"
                >
                  {rule.source}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}

            {rule.description && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Description
                </p>
                <p className="text-sm text-foreground">{rule.description}</p>
              </div>
            )}

            {/* Full Text */}
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Full Text</p>
              <div className="card p-4 bg-muted/30">
                <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
                  {rule.text}
                </p>
              </div>
            </div>

            {rule.metadata && Object.keys(rule.metadata).length > 0 && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Additional Metadata
                </p>
                <div className="card p-4 bg-muted/30">
                  <pre className="text-xs text-foreground overflow-x-auto">
                    {JSON.stringify(rule.metadata, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default RuleDetailModal;
