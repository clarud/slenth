import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { uploadDocument } from "@/api/client";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import Spinner from "@/components/ui/Spinner";
import { Upload, FileText } from "lucide-react";
import type { TransactionDetail, UploadedDocument } from "@/types/api";

type TabMode = "compliance" | "upload" | "integration";

interface ReportViewProps {
  transactionDetail?: TransactionDetail;
  loading?: boolean;
}

const ReportView = ({
  transactionDetail,
  loading = false,
}: ReportViewProps) => {
  const [activeTab, setActiveTab] = useState<TabMode>("compliance");
  const [uploadingForTransaction, setUploadingForTransaction] = useState(false);
  const [uploadedDocument, setUploadedDocument] = useState<UploadedDocument | undefined>();

  const onDropForTransaction = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    if (!transactionDetail?.transaction_id) return;
    
    const file = acceptedFiles[0];
    if (!file.type.match(/^(application\/pdf|image\/(jpeg|png))$/)) {
      toast.error("Only PDF, JPEG, and PNG files are accepted");
      return;
    }

    setUploadingForTransaction(true);
    try {
      const doc = await uploadDocument(file, transactionDetail.transaction_id);
      setUploadedDocument(doc);
      setActiveTab("upload"); // Switch to upload tab to show results
      toast.success(`Document uploaded and processed successfully`);
    } catch (error) {
      toast.error("Failed to upload document");
      console.error(error);
    } finally {
      setUploadingForTransaction(false);
    }
  }, [transactionDetail]);

  const { 
    getRootProps: getRootPropsForTransaction, 
    getInputProps: getInputPropsForTransaction, 
    isDragActive: isDragActiveForTransaction 
  } = useDropzone({
    onDrop: onDropForTransaction,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
    },
    multiple: false,
    disabled: uploadingForTransaction,
  });

  const getRiskBadgeClass = (risk?: string) => {
    if (!risk) return "badge-muted";
    const riskLower = risk.toLowerCase();
    if (riskLower === "low") return "badge-success";
    if (riskLower === "medium") return "badge-secondary";
    if (riskLower === "high" || riskLower === "critical")
      return "badge-destructive";
    return "badge-muted";
  };

  return (
    <div className="card h-full flex flex-col overflow-hidden">
      <div className="flex-shrink-0 p-4 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground mb-4">Transaction Report</h2>
        
        {/* Tabs - Only show when transaction has compliance report */}
        {transactionDetail?.compliance && (
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab("compliance")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "compliance"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              Compliance
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "upload"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              Document Upload
            </button>
            {/* Integration tab - only show if document has been uploaded */}
            {uploadedDocument && (
              <button
                onClick={() => setActiveTab("integration")}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === "integration"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                Integration
              </button>
            )}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-4">
        {/* Compliance Tab */}
        {transactionDetail && activeTab === "compliance" && (
          <motion.div
            key="compliance"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            {/* Transaction Metadata */}
            <div>
              <p className="text-sm font-semibold text-foreground mb-3">Transaction Details</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Transaction ID</p>
                  <p className="font-medium text-foreground text-xs break-all">
                    {transactionDetail.transaction_id}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <p className="font-medium text-foreground capitalize">
                    {transactionDetail.status}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Created At</p>
                  <p className="font-medium text-foreground text-xs">
                    {new Date(transactionDetail.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Updated At</p>
                  <p className="font-medium text-foreground text-xs">
                    {new Date(transactionDetail.updated_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Compliance Report - Only show if available */}
            {transactionDetail.compliance ? (
              <>
                {/* Risk Assessment */}
                <div>
                  <p className="text-sm font-semibold text-foreground mb-3">Risk Assessment</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Risk Band</p>
                      <span className={`badge ${getRiskBadgeClass(transactionDetail.compliance.risk_band)}`}>
                        {transactionDetail.compliance.risk_band}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Risk Score</p>
                      <p className="font-medium text-foreground">
                        {transactionDetail.compliance.risk_score.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Rules Evaluated</p>
                      <p className="font-medium text-foreground">
                        {transactionDetail.compliance.rules_evaluated}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Rules Violated</p>
                      <p className="font-medium text-foreground">
                        {transactionDetail.compliance.rules_violated}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Processing Time</p>
                      <p className="font-medium text-foreground">
                        {transactionDetail.compliance.processing_time_seconds.toFixed(2)}s
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Processed At</p>
                      <p className="font-medium text-foreground text-xs">
                        {new Date(transactionDetail.compliance.processed_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Bayesian Risk Analysis */}
                {transactionDetail.compliance.bayesian_posterior && (
                  <div>
                    <p className="text-sm font-semibold text-foreground mb-3">Bayesian Risk Analysis</p>
                    <div className="card p-4">
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-muted-foreground">Overall Risk Value:</span>
                          <span className="font-medium text-foreground">
                            {(transactionDetail.compliance.bayesian_posterior.risk_value * 100).toFixed(2)}%
                          </span>
                        </div>
                        {transactionDetail.compliance.bayesian_posterior.low > 0 && (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-muted-foreground">Low Risk:</span>
                            <span className="badge badge-success">
                              {(transactionDetail.compliance.bayesian_posterior.low * 100).toFixed(2)}%
                            </span>
                          </div>
                        )}
                        {transactionDetail.compliance.bayesian_posterior.medium > 0 && (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-muted-foreground">Medium Risk:</span>
                            <span className="badge badge-secondary">
                              {(transactionDetail.compliance.bayesian_posterior.medium * 100).toFixed(2)}%
                            </span>
                          </div>
                        )}
                        {transactionDetail.compliance.bayesian_posterior.high > 0 && (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-muted-foreground">High Risk:</span>
                            <span className="badge badge-destructive">
                              {(transactionDetail.compliance.bayesian_posterior.high * 100).toFixed(2)}%
                            </span>
                          </div>
                        )}
                        {transactionDetail.compliance.bayesian_posterior.critical > 0 && (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-muted-foreground">Critical Risk:</span>
                            <span className="badge badge-destructive">
                              {(transactionDetail.compliance.bayesian_posterior.critical * 100).toFixed(2)}%
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Applicable Rules */}
                {transactionDetail.compliance.applicable_rules && 
                 transactionDetail.compliance.applicable_rules.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-foreground mb-3">
                      Applicable Rules ({transactionDetail.compliance.applicable_rules.length})
                    </p>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {transactionDetail.compliance.applicable_rules.map((rule) => (
                        <div key={rule.rule_id} className="card p-4">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="text-sm font-medium text-foreground">{rule.title}</h4>
                            <span className={`badge ${getRiskBadgeClass(rule.severity)}`}>
                              {rule.severity}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mb-2">{rule.source}</p>
                          <p className="text-sm text-foreground mb-2">{rule.description}</p>
                          <div className="flex gap-2 text-xs">
                            <span className="badge badge-outline">
                              {rule.jurisdiction}
                            </span>
                            <span className="badge badge-outline">
                              {rule.rule_type}
                            </span>
                            {rule.score > 0 && (
                              <span className="badge badge-outline">
                                Score: {rule.score}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Patterns Detected */}
                {transactionDetail.compliance.patterns_detected && 
                 transactionDetail.compliance.patterns_detected.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-foreground mb-3">
                      Patterns Detected ({transactionDetail.compliance.patterns_detected.length})
                    </p>
                    <div className="space-y-2">
                      {transactionDetail.compliance.patterns_detected.map((pattern, idx) => (
                        <div key={idx} className="card p-3">
                          <p className="text-sm text-foreground">{JSON.stringify(pattern)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Compliance Summary - Only show if not empty */}
                {transactionDetail.compliance.compliance_summary && 
                 transactionDetail.compliance.compliance_summary.trim() !== "" && (
                  <div>
                    <p className="text-sm font-semibold text-foreground mb-2">
                      Compliance Summary
                    </p>
                    <div className="card p-4">
                      <p className="text-sm text-foreground whitespace-pre-wrap">
                        {transactionDetail.compliance.compliance_summary}
                      </p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="card p-4 border-dashed">
                <p className="text-sm text-muted-foreground text-center">
                  {transactionDetail.status.toLowerCase() === "pending" 
                    ? "⏳ Compliance report will be generated once processing begins..."
                    : transactionDetail.status.toLowerCase() === "processing"
                    ? "⚙️ Compliance analysis in progress..."
                    : "Compliance report not available"}
                </p>
              </div>
            )}
          </motion.div>
        )}

        {/* Upload Tab */}
        {transactionDetail && activeTab === "upload" && (
          <motion.div
            key="upload"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div>
              <p className="text-sm font-semibold text-foreground mb-2">
                Upload Supporting Document
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                Upload a document (PDF, JPEG, or PNG) to perform corroboration analysis with the transaction.
              </p>
              <div
                {...getRootPropsForTransaction()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActiveForTransaction
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-muted/30"
                }`}
              >
                <input {...getInputPropsForTransaction()} />
                {uploadingForTransaction ? (
                  <div className="flex flex-col items-center gap-2">
                    <Spinner />
                    <p className="text-sm text-muted-foreground">Uploading and processing...</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="h-10 w-10 text-muted-foreground" />
                    <p className="text-sm font-medium text-foreground">
                      {isDragActiveForTransaction
                        ? "Drop the document here"
                        : "Drag & drop a document, or click to select"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      PDF, JPEG, or PNG for corroboration analysis
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Show uploaded document result if available */}
            {uploadedDocument && (
              <div className="mt-4">
                <p className="text-sm font-semibold text-foreground mb-3">Document Analysis Result</p>
                <div className="card p-4">
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Document ID</p>
                      <p className="font-medium text-foreground text-xs">{uploadedDocument.document_id}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Filename</p>
                      <p className="font-medium text-foreground text-xs">{uploadedDocument.filename}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Risk Level</p>
                      <span className={`badge ${getRiskBadgeClass(uploadedDocument.risk_level)}`}>
                        {uploadedDocument.risk_level}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Risk Score</p>
                      <p className="font-medium text-foreground">{uploadedDocument.risk_score}</p>
                    </div>
                  </div>
                  {uploadedDocument.report_text && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Report</p>
                      <p className="text-sm text-foreground whitespace-pre-wrap">{uploadedDocument.report_text}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Integration Tab */}
        {transactionDetail && activeTab === "integration" && uploadedDocument && (
          <motion.div
            key="integration"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div>
              <p className="text-sm font-semibold text-foreground mb-2">
                Combined Analysis
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                Integrated analysis combining transaction compliance and document corroboration.
              </p>
              <div className="card p-4 border-dashed">
                <p className="text-sm text-muted-foreground text-center">
                  🔄 Integration analysis in progress...
                </p>
                <p className="text-xs text-muted-foreground text-center mt-2">
                  The combined report will appear here once processing is complete.
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {!transactionDetail && !loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>Select a transaction to view details</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Spinner size="lg" />
              <p className="text-sm text-muted-foreground mt-4">Loading transaction details...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportView;
