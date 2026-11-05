import { useState, useEffect } from "react";
import { Eye, ArrowRight } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import DataTable from "../../components/common/DataTable";
import OrderTimeline from "../../components/common/OrderTimeline";

const STATUS_BADGE = {
  "Pending": "warning",
  "Accepted": "success",
  "Partially Allocated": "info",
  "Dispatched": "info",
  "Delivered": "success",
  "Rejected": "danger",
};

const NEXT_STATUS = {
  "Accepted": "Dispatched",
  "Partially Allocated": "Dispatched",
  "Dispatched": "Delivered",
};

export default function WarehouseOrders() {
  const { toast } = useToast();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("All");
  const [viewOrder, setViewOrder] = useState(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    warehouseService.getOrders().then(setOrders).finally(() => setLoading(false));
  }, []);

  const tabs = ["All", "Pending", "Accepted", "Partially Allocated", "Dispatched", "Delivered", "Rejected"];
  const filtered = statusFilter === "All" ? orders : orders.filter((o) => o.status === statusFilter);

  const handleStatusUpdate = async (order, newStatus) => {
    setUpdating(true);
    try {
      const updated = await warehouseService.updateOrderStatus(order.id, newStatus, `Order marked as ${newStatus} by warehouse manager.`);
      setOrders((p) => p.map((o) => o.id === updated.id ? updated : o));
      if (viewOrder?.id === updated.id) setViewOrder(updated);
      toast.success(`Order ${order.orderNumber} marked as ${newStatus}.`);
    } catch { toast.error("Failed to update order status."); }
    finally { setUpdating(false); }
  };

  const columns = [
    { key: "orderNumber", label: "Order #", sortable: true, render: (v) => <span className="font-mono text-blue-700 font-semibold">{v}</span> },
    { key: "shopName", label: "Shop", sortable: true, render: (v) => <span className="text-sm text-gray-800">{v}</span> },
    { key: "requestDate", label: "Requested", sortable: true, render: (v) => <span className="text-sm text-gray-500">{v}</span> },
    { key: "items", label: "Items", render: (v) => `${v?.length ?? 0} SKUs` },
    { key: "totalRequestedUnits", label: "Total Units", sortable: true },
    { key: "priority", label: "Priority", render: (v) => <Badge variant={v === "High" ? "danger" : v === "Normal" ? "info" : "neutral"}>{v}</Badge> },
    { key: "status", label: "Status", sortable: true, render: (v) => <Badge variant={STATUS_BADGE[v] || "neutral"}>{v}</Badge> },
  ];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader title="Orders" subtitle="Manage all active and completed warehouse fulfilment orders." />

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button key={t} onClick={() => setStatusFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === t ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {t}
          </button>
        ))}
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        searchKeys={["orderNumber", "shopName"]}
        loading={loading}
        emptyMessage="No orders found."
        actions={(row) => (
          <button onClick={() => setViewOrder(row)} className="text-blue-600 hover:text-blue-800 p-1 rounded" title="View details">
            <Eye className="w-4 h-4" />
          </button>
        )}
      />

      {/* Order Detail Modal */}
      <Modal isOpen={!!viewOrder} onClose={() => setViewOrder(null)} title={`Order ${viewOrder?.orderNumber || ""}`} size="xl">
        {viewOrder && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
              {[
                ["Shop", viewOrder.shopName],
                ["Priority", viewOrder.priority],
                ["Date", viewOrder.requestDate],
                ["Status", viewOrder.status],
                ["Total Units", viewOrder.totalRequestedUnits],
                ["Notes", viewOrder.notes || "—"],
              ].map(([label, value]) => (
                <div key={label} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-0.5">{label}</p>
                  <p className="font-medium text-gray-900 text-sm">{value}</p>
                </div>
              ))}
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Requested Items</h4>
              <div className="overflow-x-auto border border-gray-200 rounded-lg">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      {["Product", "SKU", "Qty", "Unit"].map((h) => (
                        <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {viewOrder.items?.map((it, i) => (
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

            <OrderTimeline timeline={viewOrder.timeline} status={viewOrder.status} />

            {NEXT_STATUS[viewOrder.status] && (
              <div className="flex justify-end">
                <Button variant="primary" icon={ArrowRight} disabled={updating}
                  onClick={() => handleStatusUpdate(viewOrder, NEXT_STATUS[viewOrder.status])}>
                  {updating ? "Updating…" : `Mark as ${NEXT_STATUS[viewOrder.status]}`}
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
