import { useState, useEffect } from "react";
import { PlusCircle, Truck, ArrowRight, Edit2 } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import DataTable from "../../components/common/DataTable";

const STATUS_BADGE = {
  "Staged": "neutral",
  "Ready for Dispatch": "warning",
  "In Transit": "info",
  "Delivered": "success",
};

const NEXT_STATUS = {
  "Staged": "Ready for Dispatch",
  "Ready for Dispatch": "In Transit",
  "In Transit": "Delivered",
};

const EMPTY_FORM = {
  orderNumber: "", shopName: "", deliveryAddress: "", contactPerson: "",
  carrierName: "", vehicleNumber: "", driverName: "", totalItemsCount: 1, totalWeightKg: 0
};

export default function WarehouseDispatch() {
  const { toast } = useToast();
  const [dispatches, setDispatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("All");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  useEffect(() => {
    warehouseService.getDispatches().then(setDispatches).finally(() => setLoading(false));
  }, []);

  const tabs = ["All", "Staged", "Ready for Dispatch", "In Transit", "Delivered"];
  const filtered = statusFilter === "All" ? dispatches : dispatches.filter((d) => d.status === statusFilter);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const disp = await warehouseService.createDispatch({ ...form, totalItemsCount: Number(form.totalItemsCount), totalWeightKg: Number(form.totalWeightKg) });
      setDispatches((p) => [disp, ...p]);
      setCreateOpen(false);
      setForm(EMPTY_FORM);
      toast.success("Dispatch created successfully.");
    } catch { toast.error("Failed to create dispatch."); }
    finally { setSaving(false); }
  };

  const handleStatusUpdate = async (d) => {
    const next = NEXT_STATUS[d.status];
    if (!next) return;
    setUpdatingId(d.id);
    try {
      const updated = await warehouseService.updateDispatchStatus(d.id, next);
      setDispatches((p) => p.map((disp) => disp.id === updated.id ? updated : disp));
      toast.success(`Dispatch ${d.id} → ${next}`);
    } catch { toast.error("Failed to update dispatch status."); }
    finally { setUpdatingId(null); }
  };

  const columns = [
    { key: "id", label: "Dispatch ID", render: (v) => <span className="font-mono text-sm text-gray-700">{v}</span> },
    { key: "orderNumber", label: "Order #", render: (v) => <span className="font-mono text-blue-700 font-semibold">{v}</span> },
    { key: "shopName", label: "Shop", sortable: true },
    { key: "carrierName", label: "Carrier" },
    { key: "vehicleNumber", label: "Vehicle", render: (v) => <span className="font-mono text-sm">{v}</span> },
    { key: "totalWeightKg", label: "Weight", render: (v) => `${v} kg` },
    { key: "dispatchedAt", label: "Dispatched At", render: (v) => <span className="text-xs text-gray-500">{v}</span> },
    { key: "status", label: "Status", sortable: true, render: (v) => <Badge variant={STATUS_BADGE[v] || "neutral"}>{v}</Badge> },
  ];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader title="Dispatch" subtitle="Prepare, schedule, and track outgoing deliveries to shops." />
        <Button variant="primary" size="sm" icon={PlusCircle} onClick={() => { setForm(EMPTY_FORM); setCreateOpen(true); }}>Create Dispatch</Button>
      </div>

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
        searchKeys={["id", "orderNumber", "shopName", "carrierName"]}
        loading={loading}
        emptyMessage="No dispatches found."
        actions={(row) => (
          NEXT_STATUS[row.status] ? (
            <button
              onClick={() => handleStatusUpdate(row)}
              disabled={updatingId === row.id}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50"
            >
              {updatingId === row.id ? "…" : <><ArrowRight className="w-3 h-3" /> {NEXT_STATUS[row.status]}</>}
            </button>
          ) : (
            <span className="text-xs text-gray-400">Completed</span>
          )
        )}
      />

      {/* Create Dispatch Modal */}
      <Modal isOpen={createOpen} onClose={() => setCreateOpen(false)} title="Create New Dispatch" size="lg">
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { key: "orderNumber", label: "Order Number", required: true },
              { key: "shopName", label: "Shop Name", required: true },
              { key: "carrierName", label: "Carrier", required: true },
              { key: "vehicleNumber", label: "Vehicle Number", required: true },
              { key: "driverName", label: "Driver Name" },
              { key: "contactPerson", label: "Contact Person" },
              { key: "totalItemsCount", label: "Total Items", type: "number" },
              { key: "totalWeightKg", label: "Weight (kg)", type: "number" },
            ].map(({ key, label, type, required }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
                <input type={type || "text"} value={form[key] ?? ""} onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))} required={!!required}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            ))}
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Delivery Address</label>
              <textarea value={form.deliveryAddress ?? ""} onChange={(e) => setForm((p) => ({ ...p, deliveryAddress: e.target.value }))} rows={2}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary" icon={Truck} disabled={saving}>{saving ? "Creating…" : "Create Dispatch"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
