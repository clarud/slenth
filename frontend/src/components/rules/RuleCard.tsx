import { motion } from "framer-motion";
import { ExternalLink } from "lucide-react";
import type { RuleItem } from "@/types/api";

interface RuleCardProps {
  rule: RuleItem;
  onClick: () => void;
}

const RuleCard = ({ rule, onClick }: RuleCardProps) => {
  const getBadgeClass = (type: string) => {
    return type === "internal" ? "badge-primary" : "badge-secondary";
  };

  const preview = rule.text.slice(0, 150) + (rule.text.length > 150 ? "..." : "");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-interactive p-4 space-y-3"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-foreground line-clamp-2">{rule.title}</h3>
        <span className={`badge ${getBadgeClass(rule.rule_type)} shrink-0`}>
          {rule.rule_type}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {rule.regulator && (
          <span className="badge-muted">{rule.regulator}</span>
        )}
        {rule.jurisdiction && (
          <span className="badge-muted">{rule.jurisdiction}</span>
        )}
        {rule.section && (
          <span className="badge-muted">{rule.section}</span>
        )}
      </div>

      {rule.description && (
        <p className="text-sm text-muted-foreground line-clamp-2">
          {rule.description}
        </p>
      )}

      <p className="text-sm text-foreground/80 line-clamp-3">{preview}</p>

      <div className="flex items-center justify-between pt-2 border-t border-border">
        <div className="flex gap-2 text-xs text-muted-foreground">
          {rule.effective_date && <span>{rule.effective_date}</span>}
          {rule.version && <span>• {rule.version}</span>}
        </div>
        <button className="text-primary text-sm font-medium hover:underline flex items-center gap-1">
          View details
          <ExternalLink className="h-3 w-3" />
        </button>
      </div>
    </motion.div>
  );
};

export default RuleCard;
