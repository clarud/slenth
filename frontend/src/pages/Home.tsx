import { useState } from "react";
import { fetchTransactionStatus, fetchTransactionCompliance } from "@/api/client";
import Shell from "@/components/layout/Shell";
import TransactionsPanel from "@/components/TransactionsPanel";
import ReportView from "@/components/ReportView";
import toast from "react-hot-toast";
import type { TransactionDetail, UploadedDocument } from "@/types/api";

const Home = () => {
  const [selectedTxId, setSelectedTxId] = useState<string>();
  const [transactionDetail, setTransactionDetail] = useState<TransactionDetail>();
  const [loading, setLoading] = useState(false);

  const handleSelectTransaction = async (id: string) => {
    // Set selection state immediately - don't clear existing detail yet
    setSelectedTxId(id);
    setLoading(true);

    try {
      // First, fetch and display the status immediately
      const status = await fetchTransactionStatus(id);

      // Show status first (even if pending)
      setTransactionDetail({
        ...status,
        compliance: undefined,
      });
      setLoading(false);

      // Only fetch compliance if status indicates completion
      const statusLower = (status.status || "").toLowerCase();
      if (statusLower === "completed" || statusLower === "complete") {
        try {
          const compliance = await fetchTransactionCompliance(id);
          setTransactionDetail({
            ...status,
            compliance,
          });
        } catch (complianceError) {
          // Compliance endpoint might still 404 or error; keep status-only view
          console.log("Compliance fetch failed after completed status:", complianceError);
        }
      } else {
        // Do not call compliance endpoint when pending/processing/failed
        console.log(`Skipping compliance fetch; status=${status.status}`);
      }
    } catch (error) {
      // Even if status fetch fails, keep the transaction selected
      console.error("Failed to load transaction details:", error);
      toast.error("Failed to load transaction details");
      setLoading(false);
    }
  };

  return (
    <Shell>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
        <TransactionsPanel
          onSelectTransaction={handleSelectTransaction}
          selectedId={selectedTxId}
        />
        <ReportView
          transactionDetail={transactionDetail}
          loading={loading}
        />
      </div>
    </Shell>
  );
};

export default Home;
