import { useState, useEffect } from "react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import EmptyState from "../../components/ui/EmptyState";
import AllocationBreakdown from "../../components/common/AllocationBreakdown";
import { Layers } from "lucide-react";

const STATUS_BADGE = {
  "Pending": "warning",
  "Accepted": "success",
  "Partially Allocated": "info",
  "Dispatched": "info",
  "Delivered": "success",
  "Rejected": "danger",
  "Confirmed": "success",
};

export default function WarehouseAllocations() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    warehouseService.getAllocations().then((d) => {
      setData(d);
      if (d.activeAllocations.length > 0) setSelected(d.activeAllocations[0]);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>;

  const allocations = data?.activeAllocations ?? [];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader title="Allocations" subtitle="Active inventory allocations across all shop orders." />

      {allocations.length === 0 ? (
        <EmptyState icon={Layers} title="No active allocations" description="Accepted and partially allocated orders will appear here." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar list */}
          <div className="space-y-2">
            {allocations.map((alloc) => (
              <button key={alloc.orderId} onClick={() => setSelected(alloc)}
                className={`w-full text-left p-4 rounded-xl border transition-all ${selected?.orderId === alloc.orderId ? "border-blue-500 bg-blue-50" : "border-gray-200 bg-white hover:border-gray-300"}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-sm font-semibold text-blue-700">{alloc.orderNumber}</span>
                  <Badge variant={STATUS_BADGE[alloc.status] || "neutral"}>{alloc.status}</Badge>
                </div>
                <p className="text-sm text-gray-700 mt-1 truncate">{alloc.shopName}</p>
                <p className="text-xs text-gray-500 mt-0.5">{alloc.allocations?.length} warehouse(s) allocated</p>
              </button>
            ))}
          </div>

          {/* Detail pane */}
          <div className="lg:col-span-2">
            {selected ? (
              <Card className="p-6 space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg">{selected.orderNumber}</h3>
                    <p className="text-sm text-gray-500">{selected.shopName}</p>
                  </div>
                  <Badge variant={STATUS_BADGE[selected.status] || "neutral"} className="text-sm">{selected.status}</Badge>
                </div>

                {/* Requested items */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Requested Items</h4>
                  <div className="overflow-x-auto border border-gray-200 rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          {["Product", "SKU", "Qty Requested", "Unit"].map((h) => (
                            <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-600">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {selected.items?.map((it, i) => (
                          <tr key={i} className="border-t border-gray-200">
                            <td className="px-4 py-2">{it.productName}</td>
                            <td className="px-4 py-2 font-mono text-gray-500">{it.sku}</td>
                            <td className="px-4 py-2 font-medium">{it.requestedQuantity}</td>
                            <td className="px-4 py-2 text-gray-500">{it.unit}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Allocation breakdown */}
                <AllocationBreakdown
                  allocations={selected.allocations || []}
                  unallocatedBalance={selected.unallocatedBalance || []}
                  onReroute={null}
                />
              </Card>
            ) : (
              <Card className="p-16 text-center text-gray-500">Select an allocation to view details</Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
