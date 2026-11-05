import { useState, useEffect } from 'react';
import { Plus, Edit2, AlertTriangle, Eye, Package, ArrowRight } from 'lucide-react';
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

export default function ShopInventory() {
  const { toast } = useToast();
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('All Categories');
  const [selectedStatus, setSelectedStatus] = useState('All Statuses');

  // Modals
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [activeItem, setActiveItem] = useState(null);

  // Form states
  const [editQuantity, setEditQuantity] = useState('');
  const [editThreshold, setEditThreshold] = useState('');
  const [newItem, setNewItem] = useState({
    productName: '',
    sku: '',
    category: 'Grains & Cereals',
    quantity: '',
    reorderThreshold: '50',
    unit: 'kg',
    unitPrice: '',
  });

  const loadInventory = async () => {
    try {
      setLoading(true);
      const data = await shopService.getInventory();
      setInventory(data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load inventory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInventory();
  }, []);

  // Filter by category and stock status
  const filteredData = inventory.filter((item) => {
    const matchCategory = selectedCategory === 'All Categories' || item.category === selectedCategory;
    const matchStatus = selectedStatus === 'All Statuses' || item.status === selectedStatus;
    return matchCategory && matchStatus;
  });

  const handleEditClick = (item) => {
    setActiveItem(item);
    setEditQuantity(String(item.quantity));
    setEditThreshold(String(item.reorderThreshold));
    setEditModalOpen(true);
  };

  const handleViewClick = (item) => {
    setActiveItem(item);
    setViewModalOpen(true);
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!activeItem) return;
    try {
      await shopService.updateInventoryItem(activeItem.id, {
        quantity: editQuantity,
        reorderThreshold: editThreshold,
      });
      toast.success(`Inventory for ${activeItem.productName} updated.`);
      setEditModalOpen(false);
      loadInventory();
    } catch (err) {
      toast.error('Failed to update inventory.');
    }
  };

  const handleAddItem = async (e) => {
    e.preventDefault();
    if (!newItem.productName || !newItem.sku) {
      toast.error('Please enter product name and SKU.');
      return;
    }
    try {
      await shopService.addInventoryItem(newItem);
      toast.success(`Added ${newItem.productName} to inventory.`);
      setAddModalOpen(false);
      setNewItem({
        productName: '',
        sku: '',
        category: 'Grains & Cereals',
        quantity: '',
        reorderThreshold: '50',
        unit: 'kg',
        unitPrice: '',
      });
      loadInventory();
    } catch (err) {
      toast.error('Failed to add inventory item.');
    }
  };

  const columns = [
    {
      key: 'productName',
      label: 'Product',
      sortable: true,
      render: (val, row) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-base flex-shrink-0">
            {row.imagePlaceholder || '📦'}
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-xs sm:text-sm">{val}</p>
            <p className="text-[11px] font-mono text-gray-400">SKU: {row.sku}</p>
          </div>
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
      key: 'quantity',
      label: 'Available Stock',
      sortable: true,
      render: (val, row) => (
        <span className={[
          'font-bold text-xs sm:text-sm',
          val === 0 ? 'text-red-600' : val <= row.reorderThreshold ? 'text-orange-600' : 'text-gray-900',
        ].join(' ')}>
          {val} {row.unit}
        </span>
      ),
    },
    {
      key: 'reorderThreshold',
      label: 'Reorder Level',
      sortable: true,
      render: (val, row) => <span className="text-gray-500 text-xs">{val} {row.unit}</span>,
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (val) => (
        <Badge
          variant={
            val === 'In Stock' ? 'success' :
            val === 'Low Stock' ? 'warning' : 'danger'
          }
          dot
        >
          {val}
        </Badge>
      ),
    },
    {
      key: 'lastUpdated',
      label: 'Last Updated',
      sortable: true,
      render: (val) => <span className="text-gray-400 text-[11px] font-mono">{val}</span>,
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="My Inventory"
        subtitle="Manage product stock levels, set reorder thresholds, and monitor low-stock alerts."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Inventory' }]}
        action={
          <Button
            size="sm"
            variant="primary"
            icon={Plus}
            onClick={() => setAddModalOpen(true)}
          >
            Add Inventory Entry
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
          data={filteredData}
          searchPlaceholder="Search by product name or SKU..."
          searchKeys={['productName', 'sku', 'category']}
          pageSize={8}
          filterComponent={
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="text-xs px-2.5 py-2 rounded-lg border border-gray-300 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {productCategories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>

              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="text-xs px-2.5 py-2 rounded-lg border border-gray-300 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="All Statuses">All Statuses</option>
                <option value="In Stock">In Stock</option>
                <option value="Low Stock">Low Stock</option>
                <option value="Out of Stock">Out of Stock</option>
              </select>
            </div>
          }
          actions={(row) => (
            <div className="flex items-center justify-end gap-1.5">
              <button
                onClick={(e) => { e.stopPropagation(); handleViewClick(row); }}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-gray-100 transition-colors"
                title="View Details"
              >
                <Eye size={15} />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleEditClick(row); }}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-gray-100 transition-colors"
                title="Adjust Stock"
              >
                <Edit2 size={15} />
              </button>
            </div>
          )}
        />
      )}

      {/* View Item Details Modal */}
      {activeItem && (
        <Modal
          isOpen={viewModalOpen}
          onClose={() => setViewModalOpen(false)}
          title={`Inventory Details: ${activeItem.productName}`}
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-between">
              <div>
                <span className="text-[11px] text-gray-400 uppercase">Product SKU</span>
                <p className="font-mono font-bold text-gray-900 text-sm">{activeItem.sku}</p>
              </div>
              <Badge
                variant={
                  activeItem.status === 'In Stock' ? 'success' :
                  activeItem.status === 'Low Stock' ? 'warning' : 'danger'
                }
                dot
              >
                {activeItem.status}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-2.5 border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Current Available</span>
                <span className="text-lg font-bold text-gray-900">{activeItem.quantity} {activeItem.unit}</span>
              </div>
              <div className="p-2.5 border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Reorder Threshold</span>
                <span className="text-lg font-bold text-gray-700">{activeItem.reorderThreshold} {activeItem.unit}</span>
              </div>
              <div className="p-2.5 border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Retail Selling Price</span>
                <span className="text-sm font-semibold text-gray-900">₹{activeItem.unitPrice?.toFixed(2) || '—'} / {activeItem.unit}</span>
              </div>
              <div className="p-2.5 border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[11px]">Wholesale Cost Price</span>
                <span className="text-sm font-semibold text-gray-900">₹{activeItem.costPrice?.toFixed(2) || '—'} / {activeItem.unit}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button size="sm" variant="secondary" onClick={() => setViewModalOpen(false)}>
                Close
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  setViewModalOpen(false);
                  handleEditClick(activeItem);
                }}
              >
                Adjust Stock
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Edit / Adjust Stock Modal */}
      {activeItem && (
        <Modal
          isOpen={editModalOpen}
          onClose={() => setEditModalOpen(false)}
          title={`Adjust Inventory: ${activeItem.productName}`}
        >
          <form onSubmit={handleSaveEdit} className="space-y-4">
            <Input
              label={`Current Quantity (${activeItem.unit})`}
              type="number"
              min="0"
              required
              value={editQuantity}
              onChange={(e) => setEditQuantity(e.target.value)}
              hint="Enter the actual verified stock count currently in your shop."
            />
            <Input
              label={`Reorder Threshold Level (${activeItem.unit})`}
              type="number"
              min="1"
              required
              value={editThreshold}
              onChange={(e) => setEditThreshold(e.target.value)}
              hint="When available stock falls below this number, a replenishment alert is triggered."
            />
            <div className="pt-3 border-t border-gray-100 flex justify-end gap-2">
              <Button type="button" size="sm" variant="secondary" onClick={() => setEditModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" variant="primary">
                Save Adjustments
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Add New Inventory Entry Modal */}
      <Modal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title="Add New Inventory Stock Entry"
      >
        <form onSubmit={handleAddItem} className="space-y-4">
          <Input
            label="Product Name"
            placeholder="e.g. Sona Masoori Raw Rice"
            required
            value={newItem.productName}
            onChange={(e) => setNewItem({ ...newItem, productName: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="SKU Code"
              placeholder="e.g. RICE-SM-025"
              required
              value={newItem.sku}
              onChange={(e) => setNewItem({ ...newItem, sku: e.target.value })}
            />
            <Select
              label="Category"
              value={newItem.category}
              onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
            >
              {productCategories.filter((c) => c !== 'All Categories').map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </Select>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Initial Quantity"
              type="number"
              min="0"
              required
              value={newItem.quantity}
              onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
            />
            <Input
              label="Unit of Measure"
              placeholder="kg, pack, litre"
              required
              value={newItem.unit}
              onChange={(e) => setNewItem({ ...newItem, unit: e.target.value })}
            />
            <Input
              label="Reorder Level"
              type="number"
              min="1"
              required
              value={newItem.reorderThreshold}
              onChange={(e) => setNewItem({ ...newItem, reorderThreshold: e.target.value })}
            />
          </div>
          <div className="pt-3 border-t border-gray-100 flex justify-end gap-2">
            <Button type="button" size="sm" variant="secondary" onClick={() => setAddModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" size="sm" variant="primary">
              Add to Stock
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
