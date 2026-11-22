import { useState, useEffect } from 'react';
import { Plus, Trash2, Eye, FileText, IndianRupee, ShoppingBag, Calendar, CheckCircle2 } from 'lucide-react';
import { shopService } from '../../services/shopService';
import PageHeader from '../../components/ui/PageHeader';
import DataTable from '../../components/common/DataTable';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Modal from '../../components/ui/Modal';
import { Input, Select } from '../../components/ui/Input';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { useToast } from '../../context/ToastContext';

export default function ShopSales() {
  const { toast } = useToast();
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modals
  const [recordModalOpen, setRecordModalOpen] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [activeSale, setActiveSale] = useState(null);

  // Record Sale Form state
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('UPI / QR');
  const [saleItems, setSaleItems] = useState([
    { productId: '', productName: '', quantity: 1, unit: 'kg', unitPrice: 0, total: 0 },
  ]);
  const [discountAmount, setDiscountAmount] = useState('0');

  const loadData = async () => {
    try {
      setLoading(true);
      const [salesData, prodData] = await Promise.all([
        shopService.getSales(),
        shopService.getProducts(),
      ]);
      setSales(salesData);
      setProducts(prodData);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load sales history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Multi-item sales form handlers
  const handleAddItemRow = () => {
    setSaleItems([
      ...saleItems,
      { productId: '', productName: '', quantity: 1, unit: 'kg', unitPrice: 0, total: 0 },
    ]);
  };

  const handleRemoveItemRow = (index) => {
    if (saleItems.length === 1) return;
    setSaleItems(saleItems.filter((_, i) => i !== index));
  };

  const handleProductSelect = (index, prodId) => {
    const prod = products.find((p) => p.id === prodId);
    if (!prod) return;
    const items = [...saleItems];
    const qty = items[index].quantity || 1;
    const price = prod.unitPrice || 0;
    items[index] = {
      productId: prod.id,
      productName: prod.name,
      quantity: qty,
      unit: prod.unit,
      unitPrice: price,
      total: qty * price,
    };
    setSaleItems(items);
  };

  const handleQuantityChange = (index, qty) => {
    const num = Math.max(1, Number(qty) || 1);
    const items = [...saleItems];
    items[index].quantity = num;
    items[index].total = num * (items[index].unitPrice || 0);
    setSaleItems(items);
  };

  const subtotal = saleItems.reduce((sum, item) => sum + (item.total || 0), 0);
  const discount = Number(discountAmount) || 0;
  const grandTotal = Math.max(0, subtotal - discount);

  const handleRecordSaleSubmit = async (e) => {
    e.preventDefault();
    const validItems = saleItems.filter((item) => item.productId && item.quantity > 0);
    if (validItems.length === 0) {
      toast.error('Please select at least one product with quantity.');
      return;
    }

    try {
      const payload = {
        customerName: customerName || 'Walk-in Customer',
        customerPhone: customerPhone || '—',
        paymentMethod,
        items: validItems,
        subtotal,
        discount,
        tax: 0,
        total: grandTotal,
      };

      await shopService.recordSale(payload);
      toast.success('Sale transaction recorded and inventory updated!');
      setRecordModalOpen(false);
      // Reset form
      setCustomerName('');
      setCustomerPhone('');
      setDiscountAmount('0');
      setSaleItems([{ productId: '', productName: '', quantity: 1, unit: 'kg', unitPrice: 0, total: 0 }]);
      loadData();
    } catch (err) {
      toast.error('Failed to record sale.');
    }
  };

  // Metrics summary
  const totalSalesCount = sales.length;
  const totalRevenue = sales.reduce((sum, s) => sum + (s.total || 0), 0);
  const averageTicket = totalSalesCount > 0 ? totalRevenue / totalSalesCount : 0;

  const columns = [
    {
      key: 'saleNumber',
      label: 'Invoice #',
      sortable: true,
      render: (val, row) => (
        <div>
          <span className="font-mono font-bold text-gray-900 text-xs sm:text-sm">{val}</span>
          <p className="text-[11px] text-gray-400 font-mono">{row.timestamp}</p>
        </div>
      ),
    },
    {
      key: 'customerName',
      label: 'Customer',
      sortable: true,
      render: (val, row) => (
        <div>
          <p className="font-medium text-gray-800 text-xs sm:text-sm">{val}</p>
          <p className="text-[11px] text-gray-400">{row.customerPhone}</p>
        </div>
      ),
    },
    {
      key: 'items',
      label: 'Items Summary',
      render: (val) => (
        <span className="text-gray-600 text-xs line-clamp-1 max-w-xs">
          {val?.map((i) => `${i.productName} (${i.quantity} ${i.unit})`).join(', ') || '—'}
        </span>
      ),
    },
    {
      key: 'paymentMethod',
      label: 'Payment',
      sortable: true,
      render: (val) => <span className="text-xs text-gray-700 bg-gray-100 px-2 py-0.5 rounded">{val}</span>,
    },
    {
      key: 'total',
      label: 'Total Paid (₹)',
      sortable: true,
      render: (val) => (
        <span className="font-bold text-gray-900 text-xs sm:text-sm">
          ₹{val?.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (val) => <Badge variant="success" dot>{val || 'Completed'}</Badge>,
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Sales Management"
        subtitle="Record customer transactions, track revenue history, and automatically update shop stock."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Sales' }]}
        action={
          <Button
            size="sm"
            variant="primary"
            icon={Plus}
            onClick={() => setRecordModalOpen(true)}
          >
            Record New Sale
          </Button>
        }
      />

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Total Invoices</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{totalSalesCount}</p>
          <span className="text-[11px] text-gray-500">Recorded transactions</span>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Total Sales Volume</p>
          <p className="text-2xl font-bold text-green-700 mt-1">₹{totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
          <span className="text-[11px] text-gray-500">Cumulative store revenue</span>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Average Basket Size</p>
          <p className="text-2xl font-bold text-blue-700 mt-1">₹{averageTicket.toFixed(2)}</p>
          <span className="text-[11px] text-gray-500">Per bill average</span>
        </div>
      </div>

      {loading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={sales}
          searchPlaceholder="Search sale by invoice # or customer..."
          searchKeys={['saleNumber', 'customerName', 'paymentMethod']}
          pageSize={8}
          actions={(row) => (
            <button
              onClick={() => {
                setActiveSale(row);
                setDetailsModalOpen(true);
              }}
              className="text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1"
            >
              <Eye size={14} /> Receipt
            </button>
          )}
        />
      )}

      {/* Record New Sale Modal (Multi-item support) */}
      <Modal
        isOpen={recordModalOpen}
        onClose={() => setRecordModalOpen(false)}
        title="Record New Customer Sale"
        size="lg"
      >
        <form onSubmit={handleRecordSaleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              label="Customer Name"
              placeholder="e.g. Ramesh Kumar"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
            />
            <Input
              label="Phone Number"
              placeholder="+91 98450..."
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
            />
            <Select
              label="Payment Method"
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
            >
              <option value="UPI / QR">UPI / QR (PhonePe/GPay)</option>
              <option value="Cash">Cash</option>
              <option value="Credit Card">Credit / Debit Card</option>
              <option value="Store Credit">Store Credit (Khata)</option>
            </Select>
          </div>

          {/* Sale Items Section */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                Sale Line Items ({saleItems.length})
              </label>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <Plus size={14} /> Add Product
              </button>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {saleItems.map((item, idx) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200 flex flex-col sm:flex-row items-stretch sm:items-center gap-2 text-xs">
                  <div className="flex-1 min-w-44">
                    <select
                      value={item.productId}
                      onChange={(e) => handleProductSelect(idx, e.target.value)}
                      required
                      className="w-full text-xs p-2 rounded-lg border border-gray-300 bg-white"
                    >
                      <option value="">-- Choose Product --</option>
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} (₹{p.unitPrice}/{p.unit})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => handleQuantityChange(idx, e.target.value)}
                      placeholder="Qty"
                      className="w-16 p-2 rounded-lg border border-gray-300 text-xs text-center"
                    />
                    <span className="text-[11px] text-gray-500 min-w-10">{item.unit || 'units'}</span>
                    <span className="font-bold text-gray-900 min-w-20 text-right">
                      ₹{(item.total || 0).toFixed(2)}
                    </span>
                    {saleItems.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveItemRow(idx)}
                        className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Billing Calculations */}
          <div className="p-3 bg-blue-50/50 rounded-xl border border-blue-100 space-y-1.5 text-xs">
            <div className="flex justify-between text-gray-600">
              <span>Subtotal:</span>
              <span>₹{subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center text-gray-600">
              <span>Discount (₹):</span>
              <input
                type="number"
                min="0"
                value={discountAmount}
                onChange={(e) => setDiscountAmount(e.target.value)}
                className="w-20 p-1 text-right text-xs rounded border border-gray-300 bg-white"
              />
            </div>
            <div className="flex justify-between text-sm font-bold text-gray-900 pt-1.5 border-t border-blue-200">
              <span>Grand Total:</span>
              <span className="text-blue-700">₹{grandTotal.toFixed(2)}</span>
            </div>
          </div>

          <div className="pt-3 border-t border-gray-100 flex justify-end gap-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => setRecordModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" variant="primary">
              Confirm & Print Receipt
            </Button>
          </div>
        </form>
      </Modal>

      {/* View Sale Details Receipt Modal */}
      {activeSale && (
        <Modal
          isOpen={detailsModalOpen}
          onClose={() => setDetailsModalOpen(false)}
          title={`Invoice ${activeSale.saleNumber}`}
        >
          <div className="space-y-4 text-xs">
            <div className="text-center pb-3 border-b border-gray-200">
              <h3 className="font-bold text-gray-900 text-sm">Sri Lakshmi Retail Provisions</h3>
              <p className="text-[11px] text-gray-500">Malleshwaram, Bengaluru · GSTIN: 29AABCL1429Q1Z8</p>
              <p className="text-[10px] text-gray-400 mt-1 font-mono">Date: {activeSale.timestamp}</p>
            </div>

            <div className="flex justify-between text-gray-600">
              <span>Customer: <strong>{activeSale.customerName}</strong></span>
              <span>Paid via: <strong className="text-blue-700">{activeSale.paymentMethod}</strong></span>
            </div>

            <table className="w-full text-left">
              <thead className="bg-gray-50 text-gray-500 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="p-2">Item</th>
                  <th className="p-2 text-center">Qty</th>
                  <th className="p-2 text-right">Rate</th>
                  <th className="p-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {activeSale.items?.map((it, idx) => (
                  <tr key={idx}>
                    <td className="p-2 font-medium text-gray-900">{it.productName}</td>
                    <td className="p-2 text-center text-gray-600">{it.quantity} {it.unit}</td>
                    <td className="p-2 text-right text-gray-600">₹{it.unitPrice?.toFixed(2)}</td>
                    <td className="p-2 text-right font-semibold text-gray-900">₹{(it.total || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="p-3 bg-gray-50 rounded-lg space-y-1">
              <div className="flex justify-between text-gray-500">
                <span>Subtotal:</span>
                <span>₹{(activeSale.subtotal || activeSale.total).toFixed(2)}</span>
              </div>
              {activeSale.discount > 0 && (
                <div className="flex justify-between text-green-700">
                  <span>Discount:</span>
                  <span>-₹{activeSale.discount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between text-sm font-bold text-gray-900 pt-1 border-t border-gray-200">
                <span>Total Amount:</span>
                <span className="text-blue-700">₹{activeSale.total.toFixed(2)}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button size="sm" variant="secondary" onClick={() => setDetailsModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
