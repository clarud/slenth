import { useState } from "react";
import { usePolling } from "@/hooks/usePolling";
import { fetchTransactions } from "@/api/client";
import { motion } from "framer-motion";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import Spinner from "@/components/ui/Spinner";
import toast from "react-hot-toast";
import type { Transaction } from "@/types/api";

interface TransactionsPanelProps {
  onSelectTransaction: (id: string) => void;
  selectedId?: string;
}

// Helper function to get status badge variant
const getStatusBadge = (status: string) => {
  const statusLower = status.toLowerCase();
  
  switch (statusLower) {
    case "completed":
      return { variant: "default" as const, label: "Completed", color: "bg-green-500" };
    case "processing":
      return { variant: "secondary" as const, label: "Processing", color: "bg-blue-500" };
    case "pending":
      return { variant: "outline" as const, label: "Pending", color: "bg-yellow-500" };
    case "failed":
      return { variant: "destructive" as const, label: "Failed", color: "bg-red-500" };
    default:
      return { variant: "outline" as const, label: status, color: "bg-gray-500" };
  }
};

// Helper function to get border color based on risk_band
const getRiskBorderClass = (risk_band?: string | null) => {
  if (!risk_band) return "border-border";
  
  const riskLower = risk_band.toLowerCase();
  switch (riskLower) {
    case "low":
      return "border-l-4 border-l-green-500";
    case "medium":
      return "border-l-4 border-l-yellow-500";
    case "high":
      return "border-l-4 border-l-orange-500";
    case "critical":
      return "border-l-4 border-l-red-600";
    default:
      return "border-border";
  }
};

// Helper function to get background color based on risk_band
const getRiskBgClass = (risk_band?: string | null, isSelected?: boolean) => {
  if (isSelected) return "bg-primary/10";
  if (!risk_band) return "";
  
  const riskLower = risk_band.toLowerCase();
  switch (riskLower) {
    case "low":
      return "bg-green-50 hover:bg-green-100";
    case "medium":
      return "bg-yellow-50 hover:bg-yellow-100";
    case "high":
      return "bg-orange-50 hover:bg-orange-100";
    case "critical":
      return "bg-red-50 hover:bg-red-100";
    default:
      return "";
  }
};

const TransactionsPanel = ({
  onSelectTransaction,
  selectedId,
}: TransactionsPanelProps) => {
  const [isPolling, setIsPolling] = useState(true);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTransactions = async () => {
    try {
      setLoading(true);
      const data = await fetchTransactions();
      setTransactions(data);
    } catch (error) {
      toast.error("Failed to load transactions");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  usePolling(loadTransactions, 10000, isPolling);

  return (
    <div className="card h-full flex flex-col overflow-hidden">
      <div className="flex-shrink-0 p-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">Transactions</h2>
          {loading && <Spinner size="sm" />}
        </div>
        
        <div className="flex items-center gap-2">
          <Switch
            id="polling"
            checked={isPolling}
            onCheckedChange={setIsPolling}
          />
          <Label htmlFor="polling" className="cursor-pointer">
            {isPolling ? "Listening" : "Paused"}
          </Label>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-2">
        {transactions.length === 0 && !loading && (
          <div className="text-center py-12 text-muted-foreground">
            <p>No transactions yet</p>
            <p className="text-sm mt-1">
              {isPolling ? "Listening for new transactions..." : "Enable polling to start"}
            </p>
          </div>
        )}

        {transactions.map((tx, idx) => {
          const statusBadge = getStatusBadge(tx.status);
          const riskBorder = getRiskBorderClass(tx.risk_band);
          const riskBg = getRiskBgClass(tx.risk_band, selectedId === tx.transaction_id);
          
          return (
            <motion.button
              key={tx.transaction_id}
              type="button"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              onClick={() => onSelectTransaction(tx.transaction_id)}
              className={`w-full text-left px-4 py-3 rounded-lg border transition-all ${riskBorder} ${
                selectedId === tx.transaction_id
                  ? "border-primary shadow-sm"
                  : "hover:border-primary/50"
              } ${riskBg}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-foreground truncate">
                    {tx.transaction_id}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {tx.amount.toLocaleString()} {tx.currency}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {tx.originator_country} → {tx.beneficiary_country}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(tx.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <Badge variant={statusBadge.variant} className="whitespace-nowrap">
                    {statusBadge.label}
                  </Badge>
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
};

export default TransactionsPanel;
