import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { uploadDocument, fetchDocumentDetails } from "@/api/client";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import Shell from "@/components/layout/Shell";
import Spinner from "@/components/ui/Spinner";
import DocumentFindings from "@/components/DocumentFindings";
import { Upload as UploadIcon, FileText, CheckCircle } from "lucide-react";
import type { UploadedDocument, DocumentDetails } from "@/types/api";

const Upload = () => {
  const [uploading, setUploading] = useState(false);
  const [uploadedDoc, setUploadedDoc] = useState<UploadedDocument>();
  const [documentDetails, setDocumentDetails] = useState<DocumentDetails>();
  const [loadingDetails, setLoadingDetails] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    
    const file = acceptedFiles[0];
    if (!file.type.match(/^(application\/pdf|image\/(jpeg|png))$/)) {
      toast.error("Only PDF, JPEG, and PNG files are accepted");
      return;
    }

    setUploading(true);
    setDocumentDetails(undefined);
    
    try {
      // Upload without transaction_id for standalone document analysis
      const doc = await uploadDocument(file);
      setUploadedDoc(doc);
      toast.success("Document uploaded and analyzed successfully");
      
      // Fetch detailed findings
      setLoadingDetails(true);
      try {
        const details = await fetchDocumentDetails(doc.document_id);
        setDocumentDetails(details);
      } catch (error) {
        console.error("Failed to fetch document details:", error);
        toast.error("Could not load detailed findings");
      } finally {
        setLoadingDetails(false);
      }
    } catch (error) {
      toast.error("Failed to upload document");
      console.error(error);
    } finally {
      setUploading(false);
    }
  }, []);

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
    <Shell>
      <div className="h-full flex flex-col md:flex-row gap-6">
        {/* Upload Section */}
        <div className="flex-1">
          <div className="card h-full flex flex-col overflow-hidden">
            <div className="flex-shrink-0 p-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Document Upload (Part 2)</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Upload documents for standalone corroboration analysis
              </p>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0 p-4">
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors min-h-[300px] flex items-center justify-center ${
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-muted/30"
                }`}
              >
                <input {...getInputProps()} />
                {uploading ? (
                  <div className="flex flex-col items-center gap-3">
                    <Spinner size="lg" />
                    <p className="text-sm text-muted-foreground">Uploading and processing document...</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <UploadIcon className="h-16 w-16 text-muted-foreground" />
                    <div>
                      <p className="text-base font-medium text-foreground">
                        {isDragActive
                          ? "Drop the document here"
                          : "Drag & drop a document, or click to select"}
                      </p>
                      <p className="text-sm text-muted-foreground mt-2">
                        PDF, JPEG, or PNG (max 20MB)
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {uploadedDoc && !uploading && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-6 card p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800"
                >
                  <div className="flex items-start gap-3">
                    <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-medium text-green-900 dark:text-green-100">
                        Document processed successfully
                      </p>
                      <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                        {uploadedDoc.filename}
                      </p>
                      <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                        Document ID: {uploadedDoc.document_id}
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </div>

        {/* Results Section */}
        <div className="flex-1">
          <div className="card h-full flex flex-col overflow-hidden">
            <div className="flex-shrink-0 p-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Analysis Results</h2>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0 p-4">
              {uploadedDoc ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-4"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Document ID</p>
                      <p className="font-medium text-foreground text-sm break-all">
                        {uploadedDoc.document_id}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Filename</p>
                      <p className="font-medium text-foreground text-sm truncate">
                        {uploadedDoc.filename}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Risk Level</p>
                      <span className={`badge ${getRiskBadgeClass(uploadedDoc.risk_level)}`}>
                        {uploadedDoc.risk_level || "N/A"}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Risk Score</p>
                      <p className="font-medium text-foreground">
                        {uploadedDoc.risk_score || "N/A"}
                      </p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-sm text-muted-foreground">Processed At</p>
                      <p className="font-medium text-foreground text-sm">
                        {new Date(uploadedDoc.processing_completed_at).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  {/* Agent Findings */}
                  {loadingDetails ? (
                    <div className="flex items-center justify-center p-8">
                      <Spinner size="lg" />
                      <span className="ml-3 text-sm text-muted-foreground">
                        Loading detailed findings...
                      </span>
                    </div>
                  ) : documentDetails?.workflow_metadata ? (
                    <DocumentFindings metadata={documentDetails.workflow_metadata} />
                  ) : (
                    <div className="card p-4 text-center text-muted-foreground">
                      <p>No detailed findings available</p>
                    </div>
                  )}
                </motion.div>
              ) : (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-muted-foreground">
                    <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>Upload a document to see analysis results</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
};

export default Upload;
