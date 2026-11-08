import { useState, useEffect } from "react";
import { Lock } from "lucide-react";
import { workerService } from "../../services/workerService";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import DataTable from "../../components/common/DataTable";

const STATUS_BADGE = { "In Stock": "success", "Low Stock": "warning", "Out of Stock": "danger" };

export default function WorkerInventory() {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    workerService.getAuthorizedInventory().then(setInventory).finally(() => setLoading(false));
  }, []);

  const columns = [
    { key: "productName", label: "Product", sortable: true, render: (v, r) => (
      <div><p className="font-medium text-gray-900">{v}</p><p className="text-xs text-gray-500 font-mono">{r.sku}</p></div>
    )},
    { key: "category", label: "Category", sortable: true },
    { key: "availableQuantity", label: "Available", sortable: true, render: (v, r) => (
      <span className={`font-semibold ${v <= 0 ? "text-red-700" : v <= 50 ? "text-orange-700" : "text-green-700"}`}>{v} {r.unit}</span>
    )},
    { key: "aisleLocation", label: "Aisle Location", render: (v) => <span className="text-sm text-gray-600 font-mono">{v}</span> },
    { key: "status", label: "Status", render: (v) => <Badge variant={STATUS_BADGE[v] || "neutral"}>{v}</Badge> },
  ];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <PageHeader title="Inventory View" subtitle="Read-only view of warehouse stock relevant to your picking tasks." />
        <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-100 rounded-lg px-3 py-2">
          <Lock className="w-4 h-4" />
          <span>View only — modifications require manager access</span>
        </div>
      </div>

      <Card className="p-4 bg-blue-50 border border-blue-200">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> This inventory view shows current available quantities to assist you during picking tasks. For stock discrepancies, report to your supervisor immediately.
        </p>
      </Card>

      <DataTable
        columns={columns}
        data={inventory}
        searchKeys={["productName", "sku", "category", "aisleLocation"]}
        loading={loading}
        emptyMessage="No inventory data available."
      />
    </div>
  );
}
