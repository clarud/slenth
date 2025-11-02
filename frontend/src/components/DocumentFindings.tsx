import { motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle,
  FileText,
  Image,
  Search,
  Users,
  XCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState } from "react";

interface Finding {
  type: string;
  severity: string;
  description: string;
  confidence?: number;
}

interface DocumentFindingsProps {
  metadata: {
    total_findings?: number;
    processing_time_seconds?: number;
    ocr_text_length?: number;
    pages_processed?: number;
    workflow_state?: {
      format_findings?: Finding[];
      content_findings?: string[];
      image_findings?: Finding[];
      background_check_findings?: any[];
      cross_reference_findings?: any[];
      risk_factors?: string[];
    };
  };
}

const DocumentFindings = ({ metadata }: DocumentFindingsProps) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["format", "content"])
  );

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  const getSeverityColor = (severity?: string) => {
    if (!severity) return "text-muted-foreground";
    const sev = severity.toLowerCase();
    if (sev === "high" || sev === "critical") return "text-red-600 dark:text-red-400";
    if (sev === "medium") return "text-orange-600 dark:text-orange-400";
    return "text-yellow-600 dark:text-yellow-400";
  };

  const getSeverityBadge = (severity?: string) => {
    if (!severity) return "badge-muted";
    const sev = severity.toLowerCase();
    if (sev === "high" || sev === "critical") return "badge-destructive";
    if (sev === "medium") return "badge-secondary";
    return "badge-muted";
  };

  const formatFindings = metadata.workflow_state?.format_findings || [];
  const contentFindings = metadata.workflow_state?.content_findings || [];
  const imageFindings = metadata.workflow_state?.image_findings || [];
  const backgroundChecks = metadata.workflow_state?.background_check_findings || [];
  const crossReferences = metadata.workflow_state?.cross_reference_findings || [];

  const AgentSection = ({
    title,
    icon: Icon,
    count,
    sectionKey,
    children,
  }: {
    title: string;
    icon: any;
    count: number;
    sectionKey: string;
    children: React.ReactNode;
  }) => {
    const isExpanded = expandedSections.has(sectionKey);

    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="border border-border rounded-lg overflow-hidden"
      >
        <button
          onClick={() => toggleSection(sectionKey)}
          className="w-full flex items-center justify-between p-4 bg-muted/30 hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Icon className="h-5 w-5 text-primary" />
            <span className="font-semibold text-foreground">{title}</span>
            <span className={`badge ${count > 0 ? "badge-destructive" : "badge-success"}`}>
              {count} {count === 1 ? "finding" : "findings"}
            </span>
          </div>
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-5 w-5 text-muted-foreground" />
          )}
        </button>

        {isExpanded && <div className="p-4 bg-card">{children}</div>}
      </motion.div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-xs text-muted-foreground">Total Findings</p>
          <p className="text-2xl font-bold text-foreground">
            {metadata.total_findings || 0}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-muted-foreground">Processing Time</p>
          <p className="text-2xl font-bold text-foreground">
            {metadata.processing_time_seconds?.toFixed(1)}s
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-muted-foreground">Pages Processed</p>
          <p className="text-2xl font-bold text-foreground">
            {metadata.pages_processed || 1}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-muted-foreground">Text Extracted</p>
          <p className="text-2xl font-bold text-foreground">
            {((metadata.ocr_text_length || 0) / 1000).toFixed(1)}K chars
          </p>
        </div>
      </div>

      {/* Agent Findings */}
      <div className="space-y-3">
        {/* Format Validation */}
        <AgentSection
          title="Format Validation"
          icon={FileText}
          count={formatFindings.length}
          sectionKey="format"
        >
          {formatFindings.length > 0 ? (
            <div className="space-y-2">
              {formatFindings.map((finding, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 bg-muted/30 rounded-md"
                >
                  <AlertCircle className={`h-4 w-4 flex-shrink-0 mt-0.5 ${getSeverityColor(finding.severity)}`} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">
                        {finding.type}
                      </span>
                      <span className={`badge ${getSeverityBadge(finding.severity)}`}>
                        {finding.severity}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {finding.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm">No format issues detected</span>
            </div>
          )}
        </AgentSection>

        {/* NLP Validation */}
        <AgentSection
          title="NLP Validation (LLM Analysis)"
          icon={Search}
          count={contentFindings.length}
          sectionKey="content"
        >
          {contentFindings.length > 0 ? (
            <div className="space-y-2">
              {contentFindings.map((finding, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 bg-orange-50 dark:bg-orange-950/20 rounded-md border border-orange-200 dark:border-orange-800"
                >
                  <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5 text-orange-600 dark:text-orange-400" />
                  <p className="text-sm text-foreground">{finding}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm">Content is semantically consistent</span>
            </div>
          )}
        </AgentSection>

        {/* Image Forensics */}
        <AgentSection
          title="Image Forensics"
          icon={Image}
          count={imageFindings.length}
          sectionKey="image"
        >
          {imageFindings.length > 0 ? (
            <div className="space-y-2">
              {imageFindings.map((finding, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-950/20 rounded-md border border-red-200 dark:border-red-800"
                >
                  <XCircle className="h-4 w-4 flex-shrink-0 mt-0.5 text-red-600 dark:text-red-400" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">
                        {finding.type || "Image Forensics Finding"}
                      </span>
                      {finding.confidence && (
                        <span className="text-xs text-muted-foreground">
                          {(finding.confidence * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {finding.description || "Potential image manipulation or tampering detected"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm">No image tampering detected</span>
            </div>
          )}
        </AgentSection>

        {/* Background Check - Only show if there are findings */}
        {backgroundChecks.length > 0 && (
          <AgentSection
            title="Background Check (PEP/Sanctions)"
            icon={Users}
            count={backgroundChecks.length}
            sectionKey="background"
          >
            <div className="space-y-2">
              {backgroundChecks.map((check, idx) => {
                // Handle different data formats
                const displayName = typeof check === 'string' 
                  ? check 
                  : check?.name || check?.entity || JSON.stringify(check);
                const matchType = typeof check === 'object' ? check?.match_type || check?.type : null;
                
                return (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-3 bg-purple-50 dark:bg-purple-950/20 rounded-md border border-purple-200 dark:border-purple-800"
                  >
                    <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5 text-purple-600 dark:text-purple-400" />
                    <div className="text-sm text-foreground">
                      <strong>{displayName}</strong>
                      {matchType && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({matchType})
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </AgentSection>
        )}

        {/* Cross References - Only show if there are findings */}
        {crossReferences.length > 0 && (
          <AgentSection
            title="Cross References"
            icon={Search}
            count={crossReferences.length}
            sectionKey="crossref"
          >
            <div className="space-y-2">
              {crossReferences.map((ref: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-md border border-blue-200 dark:border-blue-800"
                >
                  <p className="text-sm text-foreground">{ref.description || JSON.stringify(ref)}</p>
                </div>
              ))}
            </div>
          </AgentSection>
        )}
      </div>
    </div>
  );
};

export default DocumentFindings;
