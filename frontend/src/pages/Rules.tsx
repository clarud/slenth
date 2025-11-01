import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchRules } from "@/api/client";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { SEARCH_DEBOUNCE_MS } from "@/config";
import Shell from "@/components/layout/Shell";
import RulesFilters from "@/components/rules/RulesFilters";
import RuleCard from "@/components/rules/RuleCard";
import RuleDetailModal from "@/components/rules/RuleDetailModal";
import InternalRulesModal from "@/components/rules/InternalRulesModal";
import Pagination from "@/components/rules/Pagination";
import Spinner from "@/components/ui/Spinner";
import toast from "react-hot-toast";
import { motion } from "framer-motion";
import type { RulesFilters as FiltersType, RuleItem, RulesResponse } from "@/types/api";

const Rules = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<FiltersType>({
    search: searchParams.get("search") || "",
    rule_type: (searchParams.get("rule_type") as any) || "all",
    regulator: (searchParams.get("regulator") as any) || undefined,
    jurisdiction: (searchParams.get("jurisdiction") as any) || undefined,
    section: searchParams.get("section") || "",
    is_active: searchParams.get("is_active") !== "false",
    page: Number(searchParams.get("page")) || 1,
    page_size: Number(searchParams.get("page_size")) || 25,
  });

  const [response, setResponse] = useState<RulesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedRule, setSelectedRule] = useState<RuleItem | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  const debouncedSearch = useDebouncedValue(filters.search, SEARCH_DEBOUNCE_MS);

  // Sync filters to URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.search) params.set("search", filters.search);
    if (filters.rule_type && filters.rule_type !== "all")
      params.set("rule_type", filters.rule_type);
    if (filters.regulator) params.set("regulator", filters.regulator);
    if (filters.jurisdiction) params.set("jurisdiction", filters.jurisdiction);
    if (filters.section) params.set("section", filters.section);
    if (!filters.is_active) params.set("is_active", "false");
    if (filters.page && filters.page > 1) params.set("page", String(filters.page));
    if (filters.page_size !== 25) params.set("page_size", String(filters.page_size));

    setSearchParams(params, { replace: true });
  }, [filters, setSearchParams]);

  // Fetch rules
  useEffect(() => {
    const loadRules = async () => {
      setLoading(true);
      try {
        const data = await fetchRules({
          ...filters,
          search: debouncedSearch,
        });
        setResponse(data);
      } catch (error) {
        toast.error("Failed to load rules");
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadRules();
  }, [debouncedSearch, filters.rule_type, filters.regulator, filters.jurisdiction, filters.section, filters.is_active, filters.page, filters.page_size]);

  const handleReset = () => {
    setFilters({
      search: "",
      rule_type: "all",
      is_active: true,
      page: 1,
      page_size: 25,
    });
  };

  const handleAddSuccess = () => {
    // Refresh the list
    setFilters((prev) => ({ ...prev, page: 1 }));
  };

  const totalPages = response
    ? Math.ceil(response.total / (filters.page_size || 25))
    : 0;

  return (
    <Shell>
      <div className="space-y-6">
        <RulesFilters
          filters={filters}
          onChange={setFilters}
          onReset={handleReset}
          onAddRules={() => setShowAddModal(true)}
        />

        {/* Counts - only show if there are rules */}
        {response && response.total > 0 && (
          <div className="flex gap-3">
            <div className="badge-primary px-4 py-2">
              Total: {response.total}
            </div>
            {response.internal_count !== undefined && (
              <div className="badge-muted px-4 py-2">
                Internal: {response.internal_count}
              </div>
            )}
            {response.external_count !== undefined && (
              <div className="badge-muted px-4 py-2">
                External: {response.external_count}
              </div>
            )}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        )}

        {/* Empty State */}
        {!loading && response && response.rules.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="card p-12"
          >
            <div className="max-w-md mx-auto text-center space-y-4">
              <div className="h-16 w-16 mx-auto rounded-full bg-primary/10 flex items-center justify-center">
                <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  {response.total === 0 && !filters.search && filters.rule_type === "all"
                    ? "No rules in the system yet"
                    : "No rules match your filters"}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {response.total === 0 && !filters.search && filters.rule_type === "all"
                    ? "Get started by adding your first internal rules"
                    : "Try adjusting your search or filter criteria"}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="btn-primary"
                >
                  Add Internal Rules
                </button>
                {(filters.search || filters.rule_type !== "all" || filters.regulator || filters.jurisdiction || filters.section) && (
                  <button
                    onClick={handleReset}
                    className="btn-outline"
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {/* Rules Grid */}
        {!loading && response && response.rules.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {response.rules.map((rule) => (
                <RuleCard
                  key={rule.rule_id}
                  rule={rule}
                  onClick={() => setSelectedRule(rule)}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="card p-4">
                <Pagination
                  currentPage={filters.page || 1}
                  totalPages={totalPages}
                  pageSize={filters.page_size || 25}
                  totalItems={response.total}
                  onPageChange={(page) => setFilters((prev) => ({ ...prev, page }))}
                />
              </div>
            )}
          </>
        )}
      </div>

      <RuleDetailModal rule={selectedRule} onClose={() => setSelectedRule(null)} />
      <InternalRulesModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAddSuccess}
      />
    </Shell>
  );
};

export default Rules;
