import { useState, useEffect } from 'react';
import { Plus, Edit3, Eye, Package, DollarSign, Tag, Layers } from 'lucide-react';
import { shopService } from '../../services/shopService';
import { productCategories } from '../../data/mockProducts';
import PageHeader from '../../components/ui/PageHeader';
import DataTable from '../../components/common/DataTable';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Modal from '../../components/ui/Modal';
import { Input, Select } from '../../components/ui/Input';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { useToast } from '../../context/ToastContext';

export default function ShopProducts() {
  const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('All Categories');

  // Modals
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [activeProduct, setActiveProduct] = useState(null);

  // Form
  const [form, setForm] = useState({
    name: '',
    sku: '',
    category: 'Grains & Cereals',
    unit: 'kg',
    unitPrice: '',
    costPrice: '',
    minThreshold: '50',
    description: '',
    storageTemp: 'Dry ambient',
  });

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await shopService.getProducts();
      setProducts(data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load products.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const filteredProducts = products.filter((p) => {
    return selectedCategory === 'All Categories' || p.category === selectedCategory;
  });

  const handleOpenAdd = () => {
    setForm({
      name: '',
      sku: `SKU-${Math.floor(100 + Math.random() * 900)}`,
      category: 'Grains & Cereals',
      unit: 'kg',
      unitPrice: '',
      costPrice: '',
      minThreshold: '50',
      description: '',
      storageTemp: 'Dry ambient',
    });
    setAddModalOpen(true);
  };

  const handleOpenEdit = (p) => {
    setActiveProduct(p);
    setForm({
      name: p.name,
      sku: p.sku,
      category: p.category,
      unit: p.unit,
      unitPrice: String(p.unitPrice || ''),
      costPrice: String(p.costPrice || ''),
      minThreshold: String(p.minThreshold || 50),
      description: p.description || '',
      storageTemp: p.storageTemp || 'Dry ambient',
    });
    setEditModalOpen(true);
  };

  const handleSaveAdd = async (e) => {
    e.preventDefault();
    try {
      await shopService.addProduct(form);
      toast.success(`Product "${form.name}" created successfully.`);
      setAddModalOpen(false);
      loadProducts();
    } catch (err) {
      toast.error('Failed to create product.');
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!activeProduct) return;
    try {
      await shopService.updateProduct(activeProduct.id, form);
      toast.success(`Product "${form.name}" updated successfully.`);
      setEditModalOpen(false);
      loadProducts();
    } catch (err) {
      toast.error('Failed to update product.');
    }
  };

  const columns = [
    {
      key: 'name',
      label: 'Product Name',
      sortable: true,
      render: (val, row) => (
        <div>
          <p className="font-semibold text-gray-900 text-xs sm:text-sm">{val}</p>
          <p className="text-[11px] font-mono text-gray-400">SKU: {row.sku}</p>
        </div>
      ),
    },
    {
      key: 'category',
      label: 'Category',
      sortable: true,
      render: (val) => <span className="text-gray-600 text-xs">{val}</span>,
    },
    {
      key: 'unit',
      label: 'Unit of Measure',
      sortable: true,
      render: (val) => <span className="text-gray-700 text-xs font-mono">{val}</span>,
    },
    {
      key: 'unitPrice',
      label: 'Retail Price (₹)',
      sortable: true,
      render: (val, row) => (
        <span className="font-bold text-gray-900 text-xs sm:text-sm">
          ₹{val?.toFixed(2)} <span className="text-[10px] text-gray-400 font-normal">/{row.unit}</span>
        </span>
      ),
    },
    {
      key: 'costPrice',
      label: 'Wholesale Cost (₹)',
      sortable: true,
      render: (val, row) => (
        <span className="text-gray-600 text-xs">
          ₹{val?.toFixed(2)} <span className="text-[10px] text-gray-400">/{row.unit}</span>
        </span>
      ),
    },
    {
      key: 'storageTemp',
      label: 'Storage Protocol',
      sortable: false,
      render: (val) => <span className="text-gray-500 text-[11px]">{val || 'Ambient'}</span>,
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Product Catalogue"
        subtitle="Manage master grocery items, categories, retail pricing, and units of measurement."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Products' }]}
        action={
          <Button
            size="sm"
            variant="primary"
            icon={Plus}
            onClick={handleOpenAdd}
          >
            Add New Product
          </Button>
        }
      />

      {loading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={filteredProducts}
          searchPlaceholder="Search product by name or SKU..."
          searchKeys={['name', 'sku', 'category']}
          pageSize={8}
          filterComponent={
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="text-xs px-2.5 py-2 rounded-lg border border-gray-300 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {productCategories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          }
          actions={(row) => (
            <div className="flex items-center justify-end gap-1.5">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveProduct(row);
                  setViewModalOpen(true);
                }}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-gray-100 transition-colors"
                title="View Product"
              >
                <Eye size={15} />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleOpenEdit(row);
                }}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-gray-100 transition-colors"
                title="Edit Product"
              >
                <Edit3 size={15} />
              </button>
            </div>
          )}
        />
      )}

      {/* View Product Details Modal */}
      {activeProduct && (
        <Modal
          isOpen={viewModalOpen}
          onClose={() => setViewModalOpen(false)}
          title={`Product: ${activeProduct.name}`}
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-gray-400 uppercase">Master SKU</span>
                <p className="font-mono font-bold text-gray-900 text-sm">{activeProduct.sku}</p>
              </div>
              <Badge variant="info">{activeProduct.category}</Badge>
            </div>

            <p className="text-gray-600 leading-relaxed">
              {activeProduct.description || 'No description provided.'}
            </p>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="p-2.5 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Retail Selling Price</span>
                <span className="text-base font-bold text-gray-900">₹{activeProduct.unitPrice?.toFixed(2)}</span>
              </div>
              <div className="p-2.5 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Wholesale Cost</span>
                <span className="text-base font-bold text-gray-700">₹{activeProduct.costPrice?.toFixed(2)}</span>
              </div>
              <div className="p-2.5 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Unit of Measure</span>
                <span className="text-xs font-semibold text-gray-800">{activeProduct.unit}</span>
              </div>
              <div className="p-2.5 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Storage Specification</span>
                <span className="text-xs font-semibold text-gray-800">{activeProduct.storageTemp}</span>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-100 flex justify-end gap-2">
              <Button size="sm" variant="secondary" onClick={() => setViewModalOpen(false)}>
                Close
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  setViewModalOpen(false);
                  handleOpenEdit(activeProduct);
                }}
              >
                Edit Parameters
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Add / Edit Product Modal */}
      {(addModalOpen || editModalOpen) && (
        <Modal
          isOpen={addModalOpen || editModalOpen}
          onClose={() => { setAddModalOpen(false); setEditModalOpen(false); }}
          title={addModalOpen ? 'Add New Product to Catalogue' : `Edit Product: ${form.name}`}
          size="lg"
        >
          <form onSubmit={addModalOpen ? handleSaveAdd : handleSaveEdit} className="space-y-4">
            <Input
              label="Product Full Name"
              placeholder="e.g. Sona Masoori Raw Rice"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="SKU Code"
                placeholder="e.g. RICE-SM-025"
                required
                value={form.sku}
                onChange={(e) => setForm({ ...form, sku: e.target.value })}
              />
              <Select
                label="Category"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                {productCategories.filter((c) => c !== 'All Categories').map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </Select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Input
                label="Unit of Measure"
                placeholder="kg, litre, pack"
                required
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
              />
              <Input
                label="Retail Price (₹)"
                type="number"
                step="0.01"
                min="0"
                required
                value={form.unitPrice}
                onChange={(e) => setForm({ ...form, unitPrice: e.target.value })}
              />
              <Input
                label="Wholesale Cost (₹)"
                type="number"
                step="0.01"
                min="0"
                value={form.costPrice}
                onChange={(e) => setForm({ ...form, costPrice: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Min Safety Stock Threshold"
                type="number"
                min="1"
                value={form.minThreshold}
                onChange={(e) => setForm({ ...form, minThreshold: e.target.value })}
              />
              <Input
                label="Storage Requirement"
                placeholder="e.g. Cool dry place, Dry ambient"
                value={form.storageTemp}
                onChange={(e) => setForm({ ...form, storageTemp: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description / Notes
              </label>
              <textarea
                rows={3}
                className="w-full text-xs sm:text-sm p-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Product origin, packaging details, brand specifications..."
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            <div className="pt-3 border-t border-gray-100 flex justify-end gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => { setAddModalOpen(false); setEditModalOpen(false); }}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" variant="primary">
                {addModalOpen ? 'Create Product' : 'Save Changes'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
