import { useEffect, useState } from "react";
import { X, AlertTriangle, CheckCircle2, XCircle, Clock, Shield } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { Alert, RemediationResponse } from "@/types/api";
import {
  fetchTransactionAlerts,
  triggerRemediationWorkflow,
  rejectRemediationWorkflow,
} from "@/api/client";

interface AlertsModalProps {
  transactionId: string;
  onClose: () => void;
}

const AlertsModal = ({ transactionId, onClose }: AlertsModalProps) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<Record<string, RemediationResponse | null>>({});

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  useEffect(() => {
    loadAlerts();
    loadWorkflowStatus();
  }, [transactionId]);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await fetchTransactionAlerts(transactionId);
      setAlerts(data.alerts);
    } catch (err) {
      console.error("Failed to load alerts:", err);
      setError("Failed to load alerts");
    } finally {
      setLoading(false);
    }
  };

  const loadWorkflowStatus = () => {
    // Load workflow status from localStorage
    const stored = localStorage.getItem(`workflow_status_${transactionId}`);
    if (stored) {
      try {
        setWorkflowStatus(JSON.parse(stored));
      } catch (err) {
        console.error("Failed to parse stored workflow status:", err);
      }
    }
  };

  const saveWorkflowStatus = (status: Record<string, RemediationResponse | null>) => {
    // Save workflow status to localStorage
    localStorage.setItem(`workflow_status_${transactionId}`, JSON.stringify(status));
  };

  const handleTriggerWorkflow = async (alertId: string) => {
    try {
      const response = await triggerRemediationWorkflow(alertId);
      const newStatus = { ...workflowStatus, [alertId]: response };
      setWorkflowStatus(newStatus);
      saveWorkflowStatus(newStatus);
    } catch (err) {
      console.error("Failed to trigger remediation:", err);
    }
  };

  const handleRejectWorkflow = async (alertId: string) => {
    try {
      const response = await rejectRemediationWorkflow(alertId);
      const newStatus = { ...workflowStatus, [alertId]: response };
      setWorkflowStatus(newStatus);
      saveWorkflowStatus(newStatus);
    } catch (err) {
      console.error("Failed to reject remediation:", err);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-red-600 bg-red-50 border-red-200";
      case "high":
        return "text-orange-600 bg-orange-50 border-orange-200";
      case "medium":
        return "text-yellow-600 bg-yellow-50 border-yellow-200";
      case "low":
        return "text-blue-600 bg-blue-50 border-blue-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case "compliance":
        return "text-purple-700 bg-purple-100";
      case "legal":
        return "text-indigo-700 bg-indigo-100";
      case "front":
        return "text-green-700 bg-green-100";
      default:
        return "text-gray-700 bg-gray-100";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "resolved":
        return "text-green-700 bg-green-100";
      case "in_progress":
        return "text-blue-700 bg-blue-100";
      case "acknowledged":
        return "text-yellow-700 bg-yellow-100";
      case "escalated":
        return "text-red-700 bg-red-100";
      default:
        return "text-gray-700 bg-gray-100";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
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
          className="relative z-50 w-full max-w-4xl max-h-[90vh] bg-white rounded-lg shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b bg-gradient-to-r from-blue-50 to-purple-50">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-purple-600" />
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  Transaction Alerts
                </h2>
                <p className="text-sm text-gray-600">
                  Transaction ID: {transactionId}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-600">{error}</p>
              </div>
            )}

            {!loading && !error && alerts.length === 0 && (
              <div className="text-center py-12">
                <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
                <p className="text-gray-600 text-lg">
                  No alerts found for this transaction
                </p>
              </div>
            )}

            {!loading && !error && alerts.length > 0 && (
              <div className="space-y-4">
                {alerts.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className={`border rounded-lg p-5 ${getSeverityColor(alert.severity)}`}
                  >
                    {/* Alert Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-bold text-lg">{alert.title}</h3>
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded ${getRoleColor(
                              alert.role
                            )}`}
                          >
                            {alert.role.toUpperCase()}
                          </span>
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded ${getStatusColor(
                              alert.status
                            )}`}
                          >
                            {alert.status.replace("_", " ").toUpperCase()}
                          </span>
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded ${getSeverityColor(
                              alert.severity
                            )}`}
                          >
                            {alert.severity.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm mb-2">{alert.description}</p>
                      </div>
                    </div>

                    {/* Alert Details */}
                    <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        <span>Created: {formatDate(alert.created_at)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        <span>SLA: {formatDate(alert.sla_deadline)}</span>
                      </div>
                      {alert.acknowledged_at && (
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>
                            Acknowledged: {formatDate(alert.acknowledged_at)}
                          </span>
                        </div>
                      )}
                      {alert.resolved_at && (
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Resolved: {formatDate(alert.resolved_at)}</span>
                        </div>
                      )}
                    </div>

                    {/* Remediation Workflow */}
                    {alert.remediation_workflow && (
                      <div className="mb-3 p-3 bg-white/50 rounded border">
                        <div className="flex items-center gap-2 mb-2">
                          <Shield className="w-4 h-4" />
                          <span className="font-semibold text-sm">
                            Remediation Workflow
                          </span>
                        </div>
                        <p className="text-sm">{alert.remediation_workflow}</p>
                      </div>
                    )}

                    {/* Remediation Actions */}
                    {workflowStatus[alert.alert_id] ? (
                      <div
                        className={`p-3 rounded ${
                          workflowStatus[alert.alert_id]?.workflow_status ===
                          "triggered"
                            ? "bg-green-100 border border-green-300"
                            : "bg-red-100 border border-red-300"
                        }`}
                      >
                        <p className="font-semibold text-sm">
                          {workflowStatus[alert.alert_id]?.message}
                        </p>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleTriggerWorkflow(alert.alert_id)}
                          className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-medium transition-colors flex items-center justify-center gap-2"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          Trigger Remediation Workflow
                        </button>
                        <button
                          onClick={() => handleRejectWorkflow(alert.alert_id)}
                          className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors flex items-center justify-center gap-2"
                        >
                          <XCircle className="w-4 h-4" />
                          Reject Remediation Workflow
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 p-6 border-t bg-gray-50">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default AlertsModal;
