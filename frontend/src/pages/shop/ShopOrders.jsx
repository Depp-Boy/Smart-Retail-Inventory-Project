import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShoppingCart, Plus, Trash2, ArrowRight, ArrowLeft, CheckCircle2,
  Warehouse, Star, Clock, AlertCircle, FileText
} from 'lucide-react';
import { shopService } from '../../services/shopService';
import PageHeader from '../../components/ui/PageHeader';
import DataTable from '../../components/common/DataTable';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { useToast } from '../../context/ToastContext';

export default function ShopOrders() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [activeTab, setActiveTab] = useState('create'); // 'create' or 'history'
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  // Workflow steps: 1 = Products, 2 = Quantities & Notes, 3 = Review & Destination
  const [step, setStep] = useState(1);

  // Selected Order Line Items: Array of { productId, productName, sku, unit, requestedQuantity, unitPrice }
  const [orderItems, setOrderItems] = useState([]);
  const [orderNotes, setOrderNotes] = useState('');
  const [priority, setPriority] = useState('Normal');
  const [selectedWarehouseId, setSelectedWarehouseId] = useState('');

  // Confirmation state
  const [confirmedOrder, setConfirmedOrder] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [prods, whs, ords] = await Promise.all([
        shopService.getProducts(),
        shopService.getWarehouses(),
        shopService.getOrders(),
      ]);
      setProducts(prods);
      setWarehouses(whs);
      setOrders(ords);

      const pref = whs.find((w) => w.isPreferred) || whs[0];
      if (pref) setSelectedWarehouseId(pref.id);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load order data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleProduct = (prod) => {
    const existing = orderItems.find((item) => item.productId === prod.id);
    if (existing) {
      setOrderItems(orderItems.filter((item) => item.productId !== prod.id));
    } else {
      setOrderItems([
        ...orderItems,
        {
          productId: prod.id,
          productName: prod.name,
          sku: prod.sku,
          unit: prod.unit,
          unitPrice: prod.costPrice || prod.unitPrice,
          requestedQuantity: 50, // default batch
        },
      ]);
    }
  };

  const handleQuantityChange = (prodId, qty) => {
    const num = Math.max(1, Number(qty) || 1);
    setOrderItems(
      orderItems.map((item) =>
        item.productId === prodId ? { ...item, requestedQuantity: num } : item
      )
    );
  };

  const selectedWarehouse = warehouses.find((w) => w.id === selectedWarehouseId);
  const totalItemsCount = orderItems.length;
  const totalRequestedUnits = orderItems.reduce((s, i) => s + (i.requestedQuantity || 0), 0);
  const estimatedOrderCost = orderItems.reduce((s, i) => s + ((i.requestedQuantity || 0) * (i.unitPrice || 0)), 0);

  const handleSubmitOrder = async () => {
    if (orderItems.length === 0) {
      toast.error('Please select at least one product for restocking.');
      return;
    }
    if (!selectedWarehouse) {
      toast.error('Please select destination warehouse.');
      return;
    }

    try {
      const payload = {
        destinationWarehouseId: selectedWarehouse.id,
        destinationWarehouseName: selectedWarehouse.name,
        items: orderItems,
        notes: orderNotes,
        priority,
      };

      const newOrder = await shopService.createRestockOrder(payload);
      setConfirmedOrder(newOrder);
      toast.success(`Restock order ${newOrder.orderNumber} successfully submitted!`);
      loadData();
    } catch (err) {
      toast.error('Failed to submit restock order.');
    }
  };

  const handleResetWizard = () => {
    setConfirmedOrder(null);
    setOrderItems([]);
    setOrderNotes('');
    setStep(1);
  };

  const orderColumns = [
    {
      key: 'orderNumber',
      label: 'Order Reference',
      sortable: true,
      render: (val, row) => (
        <div>
          <span className="font-mono font-bold text-gray-900 text-xs sm:text-sm">{val}</span>
          <p className="text-[11px] text-gray-400 font-mono">{row.orderDate}</p>
        </div>
      ),
    },
    {
      key: 'destinationWarehouseName',
      label: 'Target Warehouse',
      sortable: true,
      render: (val) => (
        <div className="flex items-center gap-1.5 text-xs text-gray-800">
          <Warehouse size={14} className="text-blue-500" />
          <span>{val}</span>
        </div>
      ),
    },
    {
      key: 'items',
      label: 'Requested Items',
      render: (val) => (
        <span className="text-gray-600 text-xs line-clamp-1 max-w-xs">
          {val?.map((i) => `${i.productName} (${i.requestedQuantity} ${i.unit})`).join(', ')}
        </span>
      ),
    },
    {
      key: 'totalRequestedUnits',
      label: 'Quantity',
      sortable: true,
      render: (val, row) => (
        <span className="font-semibold text-xs text-gray-900">
          {row.totalAllocatedUnits || 0} / {val} units
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (val) => (
        <Badge
          variant={
            val === 'Delivered' ? 'success' :
            val === 'Dispatched' ? 'info' :
            val === 'Partially Allocated' ? 'warning' :
            val === 'Rejected' ? 'danger' : 'neutral'
          }
          dot
        >
          {val}
        </Badge>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="py-24 flex justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Restock Orders"
        subtitle="Replenishment requisition workflow connecting to your preferred warehouse."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Restock Orders' }]}
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setActiveTab('create'); handleResetWizard(); }}
              className={[
                'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                activeTab === 'create' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
              ].join(' ')}
            >
              Order Creation Wizard
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={[
                'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                activeTab === 'history' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
              ].join(' ')}
            >
              Order History ({orders.length})
            </button>
          </div>
        }
      />

      {/* TAB 1: ORDER CREATION WORKFLOW */}
      {activeTab === 'create' && (
        <div className="space-y-6">
          {/* Confirmation Screen */}
          {confirmedOrder ? (
            <div className="bg-white rounded-2xl border border-green-200 p-8 text-center max-w-xl mx-auto shadow-sm space-y-4">
              <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto text-green-600">
                <CheckCircle2 size={32} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">
                  Restock Requisition Submitted!
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  Your replenishment request has been forwarded to <strong>{confirmedOrder.destinationWarehouseName}</strong>.
                </p>
              </div>

              <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 text-xs space-y-2 text-left">
                <div className="flex justify-between">
                  <span className="text-gray-400">Order Reference:</span>
                  <span className="font-mono font-bold text-gray-900">{confirmedOrder.orderNumber}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Requested Units:</span>
                  <span className="font-bold text-gray-900">{confirmedOrder.totalRequestedUnits} units</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Estimated Requisition Value:</span>
                  <span className="font-bold text-blue-700">₹{confirmedOrder.totalAmount?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Current Status:</span>
                  <Badge variant="neutral" dot>{confirmedOrder.status}</Badge>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <Button
                  fullWidth
                  variant="secondary"
                  onClick={handleResetWizard}
                >
                  Create Another Order
                </Button>
                <Button
                  fullWidth
                  variant="primary"
                  onClick={() => navigate('/shop/tracking')}
                >
                  Track Order in Real-Time →
                </Button>
              </div>
            </div>
          ) : (
            <div>
              {/* Wizard Step Indicators */}
              <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs mb-6">
                <div className="flex items-center justify-between max-w-2xl mx-auto relative">
                  <div className="absolute top-4 left-10 right-10 h-0.5 bg-gray-200 -z-0" />
                  {[
                    { s: 1, title: '1. Select Products' },
                    { s: 2, title: '2. Quantities & Notes' },
                    { s: 3, title: '3. Destination & Review' },
                  ].map((stepItem) => {
                    const isActive = step === stepItem.s;
                    const isDone = step > stepItem.s;
                    return (
                      <div key={stepItem.s} className="flex flex-col items-center relative z-10">
                        <button
                          type="button"
                          onClick={() => isDone && setStep(stepItem.s)}
                          className={[
                            'w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition-all border-2',
                            isActive ? 'bg-blue-600 border-blue-600 text-white ring-4 ring-blue-100' :
                            isDone ? 'bg-green-600 border-green-600 text-white' : 'bg-white border-gray-300 text-gray-400',
                          ].join(' ')}
                        >
                          {isDone ? '✓' : stepItem.s}
                        </button>
                        <span className={[
                          'text-xs mt-1.5 font-medium',
                          isActive ? 'text-blue-600 font-bold' : isDone ? 'text-gray-700' : 'text-gray-400',
                        ].join(' ')}>
                          {stepItem.title}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* STEP 1: Select Products */}
              {step === 1 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-100 gap-2">
                    <div>
                      <h3 className="text-sm font-bold text-gray-900">
                        Step 1: Choose Products for Replenishment
                      </h3>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Select multiple commodities to batch together into a single restock shipment.
                      </p>
                    </div>
                    <span className="text-xs font-semibold text-blue-600">
                      {orderItems.length} products selected
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {products.map((p) => {
                      const isSelected = orderItems.some((i) => i.productId === p.id);
                      return (
                        <div
                          key={p.id}
                          onClick={() => handleToggleProduct(p)}
                          className={[
                            'p-3.5 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-3 text-xs',
                            isSelected
                              ? 'border-blue-500 bg-blue-50/50 ring-2 ring-blue-100 shadow-2xs'
                              : 'border-gray-200 hover:border-gray-300 bg-white',
                          ].join(' ')}
                        >
                          <div>
                            <p className="font-semibold text-gray-900">{p.name}</p>
                            <p className="text-[11px] font-mono text-gray-400">SKU: {p.sku}</p>
                            <span className="inline-block mt-1 text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                              {p.category}
                            </span>
                          </div>
                          <div className="text-right flex flex-col items-end">
                            <span className="font-semibold text-gray-700">₹{p.costPrice || p.unitPrice}/{p.unit}</span>
                            <div className={[
                              'w-5 h-5 rounded-md mt-2 flex items-center justify-center border transition-colors',
                              isSelected ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300',
                            ].join(' ')}>
                              {isSelected && <CheckCircle2 size={13} />}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="pt-4 border-t border-gray-100 flex justify-end">
                    <Button
                      size="md"
                      variant="primary"
                      disabled={orderItems.length === 0}
                      onClick={() => setStep(2)}
                      icon={ArrowRight}
                      iconPosition="right"
                    >
                      Continue ({orderItems.length} selected)
                    </Button>
                  </div>
                </div>
              )}

              {/* STEP 2: Requested Quantities & Notes */}
              {step === 2 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs space-y-5">
                  <div className="pb-3 border-b border-gray-100">
                    <h3 className="text-sm font-bold text-gray-900">
                      Step 2: Specify Quantities & Urgency
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Enter the required replenishment volume for each selected commodity.
                    </p>
                  </div>

                  <div className="space-y-3">
                    {orderItems.map((item) => (
                      <div key={item.productId} className="p-3 bg-gray-50 rounded-xl border border-gray-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
                        <div>
                          <p className="font-semibold text-gray-900">{item.productName}</p>
                          <p className="text-[11px] text-gray-400 font-mono">SKU: {item.sku} · Est. Rate: ₹{item.unitPrice}/{item.unit}</p>
                        </div>
                        <div className="flex items-center gap-3 w-full sm:w-auto">
                          <label className="text-gray-500 text-xs">Quantity:</label>
                          <input
                            type="number"
                            min="1"
                            value={item.requestedQuantity}
                            onChange={(e) => handleQuantityChange(item.productId, e.target.value)}
                            className="w-24 p-2 rounded-lg border border-gray-300 text-sm font-bold text-center bg-white"
                          />
                          <span className="font-medium text-gray-700 min-w-10">{item.unit}</span>
                          <span className="font-bold text-gray-900 min-w-24 text-right">
                            ₹{(item.requestedQuantity * item.unitPrice).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                        Priority Level
                      </label>
                      <select
                        value={priority}
                        onChange={(e) => setPriority(e.target.value)}
                        className="w-full text-xs p-2.5 rounded-lg border border-gray-300 bg-white"
                      >
                        <option value="Normal">Normal Replenishment</option>
                        <option value="High">High Urgency (Low Stock Situation)</option>
                        <option value="Critical">Emergency Express (Near Out-of-Stock)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                        Order Notes for Warehouse Manager
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Please expedite Sona Masoori Rice pallet..."
                        value={orderNotes}
                        onChange={(e) => setOrderNotes(e.target.value)}
                        className="w-full text-xs p-2.5 rounded-lg border border-gray-300 bg-white"
                      />
                    </div>
                  </div>

                  <div className="pt-4 border-t border-gray-100 flex justify-between">
                    <Button size="md" variant="secondary" onClick={() => setStep(1)} icon={ArrowLeft}>
                      Back to Products
                    </Button>
                    <Button size="md" variant="primary" onClick={() => setStep(3)} icon={ArrowRight} iconPosition="right">
                      Review & Select Warehouse
                    </Button>
                  </div>
                </div>
              )}

              {/* STEP 3: Review & Destination Warehouse Selection */}
              {step === 3 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs space-y-5">
                  <div className="pb-3 border-b border-gray-100">
                    <h3 className="text-sm font-bold text-gray-900">
                      Step 3: Review Requisition & Select Initial Destination
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Your preferred warehouse is selected by default. You can adjust the initial destination if needed.
                    </p>
                  </div>

                  {/* Destination Warehouse Selection */}
                  <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-200 space-y-3">
                    <label className="block text-xs font-bold text-blue-900 uppercase">
                      Initial Destination Fulfillment Warehouse
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {warehouses.map((wh) => (
                        <div
                          key={wh.id}
                          onClick={() => setSelectedWarehouseId(wh.id)}
                          className={[
                            'p-3.5 rounded-xl border bg-white cursor-pointer transition-all flex items-start justify-between text-xs',
                            selectedWarehouseId === wh.id
                              ? 'border-blue-600 ring-2 ring-blue-200 shadow-2xs'
                              : 'border-gray-200 hover:border-gray-300',
                          ].join(' ')}
                        >
                          <div>
                            <p className="font-bold text-gray-900">{wh.name}</p>
                            <p className="text-[11px] text-gray-500 mt-0.5">{wh.distanceKm} km · {wh.dispatchSpeed}</p>
                            {wh.isPreferred && (
                              <span className="inline-block mt-1 text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-semibold">
                                ★ Your Preferred Warehouse
                              </span>
                            )}
                          </div>
                          <div className={[
                            'w-4 h-4 rounded-full border-2 flex items-center justify-center',
                            selectedWarehouseId === wh.id ? 'border-blue-600 bg-blue-600' : 'border-gray-300',
                          ].join(' ')}>
                            {selectedWarehouseId === wh.id && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Order Summary Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-gray-50 text-gray-500 font-semibold uppercase text-[10px]">
                        <tr>
                          <th className="p-2.5">Product</th>
                          <th className="p-2.5 text-center">SKU</th>
                          <th className="p-2.5 text-center">Requested Quantity</th>
                          <th className="p-2.5 text-right">Est. Cost</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {orderItems.map((item) => (
                          <tr key={item.productId}>
                            <td className="p-2.5 font-semibold text-gray-900">{item.productName}</td>
                            <td className="p-2.5 text-center font-mono text-gray-400">{item.sku}</td>
                            <td className="p-2.5 text-center font-bold text-gray-900">{item.requestedQuantity} {item.unit}</td>
                            <td className="p-2.5 text-right font-medium text-gray-700">₹{(item.requestedQuantity * item.unitPrice).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Totals */}
                  <div className="p-4 bg-gray-50 rounded-xl space-y-1.5 text-xs">
                    <div className="flex justify-between text-gray-600">
                      <span>Total Requisition Line Items:</span>
                      <span className="font-bold text-gray-900">{totalItemsCount} commodities</span>
                    </div>
                    <div className="flex justify-between text-gray-600">
                      <span>Total Physical Units:</span>
                      <span className="font-bold text-gray-900">{totalRequestedUnits} units</span>
                    </div>
                    <div className="flex justify-between text-sm font-bold text-gray-900 pt-2 border-t border-gray-200">
                      <span>Estimated Order Value:</span>
                      <span className="text-blue-700">₹{estimatedOrderCost.toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-gray-100 flex justify-between">
                    <Button size="md" variant="secondary" onClick={() => setStep(2)} icon={ArrowLeft}>
                      Back to Quantities
                    </Button>
                    <Button size="md" variant="primary" onClick={handleSubmitOrder} icon={ShoppingCart}>
                      Submit Restock Requisition
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: ORDER HISTORY */}
      {activeTab === 'history' && (
        <DataTable
          columns={orderColumns}
          data={orders}
          searchPlaceholder="Search order reference or warehouse..."
          searchKeys={['orderNumber', 'destinationWarehouseName', 'status']}
          pageSize={8}
          actions={(row) => (
            <Button
              size="xs"
              variant="secondary"
              onClick={() => navigate('/shop/tracking')}
            >
              Track Order
            </Button>
          )}
        />
      )}
    </div>
  );
}
