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
  const [uploadedDoc, setUploadedDoc] = useState<UploadedDocument>();
  const [reportMode, setReportMode] = useState<"transaction" | "upload">("transaction");

  const handleSelectTransaction = async (id: string) => {
    try {
      setSelectedTxId(id);
      setReportMode("transaction");
      
      const [status, compliance] = await Promise.all([
        fetchTransactionStatus(id),
        fetchTransactionCompliance(id),
      ]);

      setTransactionDetail({
        ...status,
        compliance,
      });
    } catch (error) {
      toast.error("Failed to load transaction details");
      console.error(error);
    }
  };

  const handleUploadView = () => {
    setReportMode("upload");
  };

  return (
    <Shell>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[calc(100vh-12rem)]">
        <TransactionsPanel
          onSelectTransaction={handleSelectTransaction}
          selectedId={selectedTxId}
          onUploadView={handleUploadView}
        />
        <ReportView
          transactionDetail={transactionDetail}
          uploadedDoc={uploadedDoc}
          mode={reportMode}
          onModeChange={setReportMode}
        />
      </div>
    </Shell>
  );
};

export default Home;
