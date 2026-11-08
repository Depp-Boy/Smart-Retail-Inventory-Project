import { useState, useEffect } from "react";
import { PlusCircle, Edit2, Package } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import DataTable from "../../components/common/DataTable";

const STATUS_BADGE = { "In Stock": "success", "Low Stock": "warning", "Out of Stock": "danger" };
const CATEGORIES = ["All", "Grains & Cereals", "Sweeteners", "Flour & Grains", "Spices & Salt", "Edible Oils", "Dal & Pulses"];

function InventoryForm({ form, setForm, onSubmit, loading, isEdit }) {
  const fields = [
    { key: "productName", label: "Product Name", required: true },
    { key: "sku", label: "SKU", required: true },
    { key: "category", label: "Category", required: false },
    { key: "totalQuantity", label: "Total Quantity", type: "number", required: true },
    { key: "reservedQuantity", label: "Reserved Quantity", type: "number", required: false },
    { key: "unit", label: "Unit (e.g. kg)", required: false },
    { key: "aisleLocation", label: "Aisle Location", required: false },
    { key: "supplierId", label: "Supplier ID", required: false },
  ];
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {fields.map(({ key, label, type, required }) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
            <input
              type={type || "text"}
              value={form[key] ?? ""}
              onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
              required={required}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button type="submit" variant="primary" disabled={loading}>{loading ? "Saving…" : isEdit ? "Update Stock" : "Add Entry"}</Button>
      </div>
    </form>
  );
}

export default function WarehouseInventory() {
  const { toast } = useToast();
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [addOpen, setAddOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    warehouseService.getInventory().then(setInventory).finally(() => setLoading(false));
  }, []);

  const filtered = inventory.filter((i) => {
    const catOk = categoryFilter === "All" || i.category === categoryFilter;
    const stsOk = statusFilter === "All" || i.status === statusFilter;
    return catOk && stsOk;
  });

  const handleAdd = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const item = await warehouseService.addStockEntry(form);
      setInventory((p) => [item, ...p]);
      setAddOpen(false);
      setForm({});
      toast.success("Stock entry added.");
    } catch { toast.error("Failed to add entry."); }
    finally { setSaving(false); }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const item = await warehouseService.updateStock(editItem.id, form);
      setInventory((p) => p.map((i) => i.id === item.id ? item : i));
      setEditItem(null);
      toast.success("Stock updated.");
    } catch { toast.error("Failed to update stock."); }
    finally { setSaving(false); }
  };

  const openEdit = (row) => { setEditItem(row); setForm({ ...row }); };

  const columns = [
    { key: "productName", label: "Product", sortable: true, render: (v, r) => (
      <div><p className="font-medium text-gray-900">{v}</p><p className="text-xs text-gray-500 font-mono">{r.sku}</p></div>
    )},
    { key: "category", label: "Category", sortable: true },
    { key: "totalQuantity", label: "Total", sortable: true, render: (v, r) => `${v} ${r.unit}` },
    { key: "reservedQuantity", label: "Reserved", sortable: true, render: (v, r) => `${v} ${r.unit}` },
    { key: "availableQuantity", label: "Available", sortable: true, render: (v, r) => (
      <span className={v <= 50 ? "text-orange-700 font-semibold" : "text-green-700 font-semibold"}>{v} {r.unit}</span>
    )},
    { key: "aisleLocation", label: "Aisle", render: (v) => <span className="text-gray-600 text-sm">{v}</span> },
    { key: "status", label: "Status", render: (v) => <Badge variant={STATUS_BADGE[v] || "neutral"}>{v}</Badge> },
    { key: "lastAuditDate", label: "Last Audit", render: (v) => <span className="text-xs text-gray-500">{v}</span> },
  ];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader title="Warehouse Inventory" subtitle="Manage all warehouse stock — view, update, and audit inventory counts." />
        <Button variant="primary" size="sm" icon={PlusCircle} onClick={() => { setForm({}); setAddOpen(true); }}>Add Stock Entry</Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div>
            <label className="text-xs text-gray-500 mr-1">Category:</label>
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mr-1">Status:</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {["All", "In Stock", "Low Stock", "Out of Stock"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <span className="text-sm text-gray-500 ml-auto">{filtered.length} products</span>
        </div>
      </Card>

      <DataTable
        columns={columns}
        data={filtered}
        searchKeys={["productName", "sku", "category"]}
        loading={loading}
        emptyMessage="No inventory items found."
        actions={(row) => (
          <button onClick={() => openEdit(row)} className="text-blue-600 hover:text-blue-800 p-1 rounded">
            <Edit2 className="w-4 h-4" />
          </button>
        )}
      />

      {/* Add Modal */}
      <Modal isOpen={addOpen} onClose={() => setAddOpen(false)} title="Add Stock Entry" size="lg">
        <InventoryForm form={form} setForm={setForm} onSubmit={handleAdd} loading={saving} isEdit={false} />
      </Modal>

      {/* Edit Modal */}
      <Modal isOpen={!!editItem} onClose={() => setEditItem(null)} title={`Update Stock — ${editItem?.productName || ""}`} size="lg">
        <InventoryForm form={form} setForm={setForm} onSubmit={handleEdit} loading={saving} isEdit />
      </Modal>
    </div>
  );
}
