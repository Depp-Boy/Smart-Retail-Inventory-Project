import { useState, useEffect } from "react";
import { PlusCircle, Edit2 } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import Button from "../../components/ui/Button";
import Badge from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import DataTable from "../../components/common/DataTable";

const CATEGORIES = ["Grains & Cereals", "Sweeteners", "Flour & Grains", "Spices & Salt", "Edible Oils", "Dal & Pulses", "Beverages", "Packaged Foods", "Other"];

const EMPTY_FORM = { name: "", sku: "", category: "Grains & Cereals", brand: "", unit: "kg", basePrice: "", mrp: "", description: "" };

function ProductForm({ form, setForm, onSubmit, loading, isEdit }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { key: "name", label: "Product Name", required: true },
          { key: "sku", label: "SKU Code", required: true },
          { key: "brand", label: "Brand" },
          { key: "unit", label: "Unit (kg / litre / pcs)" },
          { key: "basePrice", label: "Base Price (₹)", type: "number" },
          { key: "mrp", label: "MRP (₹)", type: "number" },
        ].map(({ key, label, type, required }) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
            <input type={type || "text"} value={form[key] ?? ""} onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))} required={!!required}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        ))}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <select value={form.category || ""} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea value={form.description ?? ""} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} rows={2}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>
      <div className="flex justify-end">
        <Button type="submit" variant="primary" disabled={loading}>{loading ? "Saving…" : isEdit ? "Update Product" : "Add Product"}</Button>
      </div>
    </form>
  );
}

export default function WarehouseProducts() {
  const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [catFilter, setCatFilter] = useState("All");
  const [addOpen, setAddOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    warehouseService.getProducts().then(setProducts).finally(() => setLoading(false));
  }, []);

  const filtered = catFilter === "All" ? products : products.filter((p) => p.category === catFilter);

  const handleAdd = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const item = await warehouseService.addProduct({ ...form, basePrice: Number(form.basePrice), mrp: Number(form.mrp) });
      setProducts((p) => [item, ...p]);
      setAddOpen(false);
      setForm(EMPTY_FORM);
      toast.success("Product added to warehouse catalogue.");
    } catch { toast.error("Failed to add product."); }
    finally { setSaving(false); }
  };

  const columns = [
    { key: "name", label: "Product", sortable: true, render: (v, r) => (
      <div><p className="font-medium text-gray-900">{v}</p><p className="text-xs text-gray-500">{r.brand}</p></div>
    )},
    { key: "sku", label: "SKU", render: (v) => <span className="font-mono text-sm text-blue-700">{v}</span> },
    { key: "category", label: "Category", sortable: true, render: (v) => <Badge variant="info">{v}</Badge> },
    { key: "unit", label: "Unit" },
    { key: "basePrice", label: "Base Price", sortable: true, render: (v) => `₹${Number(v).toFixed(2)}` },
    { key: "mrp", label: "MRP", render: (v) => `₹${Number(v).toFixed(2)}` },
    { key: "description", label: "Description", render: (v) => <span className="text-gray-500 text-sm truncate max-w-xs block">{v}</span> },
  ];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader title="Product Catalogue" subtitle="Manage the product catalogue stored in this warehouse." />
        <Button variant="primary" size="sm" icon={PlusCircle} onClick={() => { setForm(EMPTY_FORM); setAddOpen(true); }}>Add Product</Button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm text-gray-500">Category:</label>
        {["All", ...CATEGORIES].map((c) => (
          <button key={c} onClick={() => setCatFilter(c)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${catFilter === c ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {c}
          </button>
        ))}
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        searchKeys={["name", "sku", "category", "brand"]}
        loading={loading}
        emptyMessage="No products found."
      />

      <Modal isOpen={addOpen} onClose={() => setAddOpen(false)} title="Add Product to Catalogue" size="lg">
        <ProductForm form={form} setForm={setForm} onSubmit={handleAdd} loading={saving} isEdit={false} />
      </Modal>

      {editItem && (
        <Modal isOpen onClose={() => setEditItem(null)} title={`Edit — ${editItem.name}`} size="lg">
          <ProductForm form={form} setForm={setForm} onSubmit={(e) => { e.preventDefault(); setEditItem(null); toast.info("Product update (demo mode)."); }} loading={saving} isEdit />
        </Modal>
      )}
    </div>
  );
}
