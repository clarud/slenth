import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { uploadDocument } from "@/api/client";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import Spinner from "@/components/ui/Spinner";
import { Upload, FileText } from "lucide-react";
import type { TransactionDetail, UploadedDocument } from "@/types/api";

interface ReportViewProps {
  transactionDetail?: TransactionDetail;
  uploadedDoc?: UploadedDocument;
  mode: "transaction" | "upload";
  onModeChange: (mode: "transaction" | "upload") => void;
}

const ReportView = ({
  transactionDetail,
  uploadedDoc,
  mode,
  onModeChange,
}: ReportViewProps) => {
  const [uploading, setUploading] = useState(false);
  const [currentDoc, setCurrentDoc] = useState<UploadedDocument | undefined>(
    uploadedDoc
  );

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    
    const file = acceptedFiles[0];
    if (!file.type.match(/^(application\/pdf|image\/(jpeg|png))$/)) {
      toast.error("Only PDF, JPEG, and PNG files are accepted");
      return;
    }

    setUploading(true);
    try {
      const doc = await uploadDocument(file);
      setCurrentDoc(doc);
      onModeChange("upload");
      toast.success("Document uploaded successfully");
    } catch (error) {
      toast.error("Failed to upload document");
      console.error(error);
    } finally {
      setUploading(false);
    }
  }, [onModeChange]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
    },
    multiple: false,
    disabled: uploading,
  });

  const getRiskBadgeClass = (risk: string) => {
    const riskLower = risk.toLowerCase();
    if (riskLower === "low") return "badge-success";
    if (riskLower === "medium") return "badge-secondary";
    if (riskLower === "high" || riskLower === "critical")
      return "badge-destructive";
    return "badge-muted";
  };

  return (
    <div className="card h-full flex flex-col">
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground mb-4">Report</h2>
        
        <div className="flex gap-2">
          <button
            onClick={() => onModeChange("transaction")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === "transaction"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            Transaction
          </button>
          <button
            onClick={() => onModeChange("upload")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === "upload"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            Upload
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {mode === "transaction" && transactionDetail && (
          <motion.div
            key="transaction"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="font-medium text-foreground">
                  {transactionDetail.status}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Progress</p>
                <p className="font-medium text-foreground">
                  {transactionDetail.progress_percentage}%
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Risk Band</p>
                <span className={`badge ${getRiskBadgeClass(transactionDetail.risk_band)}`}>
                  {transactionDetail.risk_band}
                </span>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Risk Score</p>
                <p className="font-medium text-foreground">
                  {transactionDetail.risk_score}
                </p>
              </div>
            </div>

            <div>
              <p className="text-sm text-muted-foreground mb-2">
                Compliance Summary
              </p>
              <div className="card p-4" id="report-context">
                <p className="text-sm text-foreground whitespace-pre-wrap">
                  {transactionDetail.compliance.compliance_summary}
                </p>
              </div>
            </div>

            {transactionDetail.compliance.report_text && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">Full Report</p>
                <div className="card p-4" id="report-context">
                  <p className="text-sm text-foreground whitespace-pre-wrap">
                    {transactionDetail.compliance.report_text}
                  </p>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {mode === "transaction" && !transactionDetail && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>Select a transaction to view details</p>
            </div>
          </div>
        )}

        {mode === "upload" && (
          <motion.div
            key="upload"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 hover:bg-muted/30"
              }`}
            >
              <input {...getInputProps()} />
              {uploading ? (
                <div className="flex flex-col items-center gap-2">
                  <Spinner />
                  <p className="text-sm text-muted-foreground">Uploading...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload className="h-10 w-10 text-muted-foreground" />
                  <p className="text-sm font-medium text-foreground">
                    {isDragActive
                      ? "Drop the file here"
                      : "Drag & drop a document, or click to select"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    PDF, JPEG, or PNG (max 20MB)
                  </p>
                </div>
              )}
            </div>

            {currentDoc && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Document ID</p>
                    <p className="font-medium text-foreground text-sm">
                      {currentDoc.document_id}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Filename</p>
                    <p className="font-medium text-foreground text-sm">
                      {currentDoc.filename}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Risk Level</p>
                    <span className={`badge ${getRiskBadgeClass(currentDoc.risk_level)}`}>
                      {currentDoc.risk_level}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Risk Score</p>
                    <p className="font-medium text-foreground">
                      {currentDoc.risk_score}
                    </p>
                  </div>
                </div>

                {currentDoc.report_text && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Analysis</p>
                    <div className="card p-4" id="report-context">
                      <p className="text-sm text-foreground whitespace-pre-wrap">
                        {currentDoc.report_text}
                      </p>
                    </div>
                  </div>
                )}

                <p className="text-xs text-muted-foreground">
                  Completed: {new Date(currentDoc.processing_completed_at).toLocaleString()}
                </p>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default ReportView;
