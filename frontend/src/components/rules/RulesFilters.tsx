import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { X, Plus } from "lucide-react";
import type { RulesFilters as FiltersType } from "@/types/api";

interface RulesFiltersProps {
  filters: FiltersType;
  onChange: (filters: FiltersType) => void;
  onReset: () => void;
  onAddRules: () => void;
}

const RulesFilters = ({ filters, onChange, onReset, onAddRules }: RulesFiltersProps) => {
  return (
    <div className="card p-4 space-y-4 sticky top-20 z-10 bg-card/95 backdrop-blur-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <Input
            placeholder="Search rules..."
            value={filters.search || ""}
            onChange={(e) => onChange({ ...filters, search: e.target.value, page: 1 })}
            className="w-full"
          />
        </div>
        <button onClick={onAddRules} className="btn-primary whitespace-nowrap">
          <Plus className="h-4 w-4 mr-2" />
          Add Internal Rules
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Rule Type */}
        <div className="space-y-2">
          <Label>Rule Type</Label>
          <div className="flex gap-2">
            {["all", "internal", "external"].map((type) => (
              <button
                key={type}
                onClick={() => onChange({ ...filters, rule_type: type as any, page: 1 })}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  (filters.rule_type || "all") === type
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Regulator */}
        <div className="space-y-2">
          <Label htmlFor="regulator">Regulator</Label>
          <Select
            value={filters.regulator || "all"}
            onValueChange={(value) =>
              onChange({ ...filters, regulator: value === "all" ? undefined : value as any, page: 1 })
            }
          >
            <SelectTrigger id="regulator">
              <SelectValue placeholder="All Regulators" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Regulators</SelectItem>
              <SelectItem value="HKMA">HKMA</SelectItem>
              <SelectItem value="MAS">MAS</SelectItem>
              <SelectItem value="FINMA">FINMA</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Jurisdiction */}
        <div className="space-y-2">
          <Label htmlFor="jurisdiction">Jurisdiction</Label>
          <Select
            value={filters.jurisdiction || "all"}
            onValueChange={(value) =>
              onChange({ ...filters, jurisdiction: value === "all" ? undefined : value as any, page: 1 })
            }
          >
            <SelectTrigger id="jurisdiction">
              <SelectValue placeholder="All Jurisdictions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Jurisdictions</SelectItem>
              <SelectItem value="HK">Hong Kong</SelectItem>
              <SelectItem value="SG">Singapore</SelectItem>
              <SelectItem value="CH">Switzerland</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch
              id="active"
              checked={filters.is_active !== false}
              onCheckedChange={(checked) =>
                onChange({ ...filters, is_active: checked, page: 1 })
              }
            />
            <Label htmlFor="active" className="cursor-pointer">
              Active only
            </Label>
          </div>

          <div className="flex items-center gap-2">
            <Label htmlFor="pageSize">Page Size:</Label>
            <Select
              value={String(filters.page_size || 25)}
              onValueChange={(value) =>
                onChange({ ...filters, page_size: Number(value), page: 1 })
              }
            >
              <SelectTrigger id="pageSize" className="w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="25">25</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <button onClick={onReset} className="btn-ghost">
          <X className="h-4 w-4 mr-2" />
          Reset
        </button>
      </div>
    </div>
  );
};

export default RulesFilters;
