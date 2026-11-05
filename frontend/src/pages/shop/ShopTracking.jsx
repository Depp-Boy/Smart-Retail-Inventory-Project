import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Truck, Package, Warehouse, Calendar, Clock, AlertTriangle,
  ArrowRight, Search, CheckCircle2, ChevronRight
} from 'lucide-react';
import { shopService } from '../../services/shopService';
import PageHeader from '../../components/ui/PageHeader';
import OrderTimeline from '../../components/common/OrderTimeline';
import AllocationBreakdown from '../../components/common/AllocationBreakdown';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { useToast } from '../../context/ToastContext';

export default function ShopTracking() {
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const targetOrderId = searchParams.get('orderId');

  const [orders, setOrders] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [selectedOrderId, setSelectedOrderId] = useState('');
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [ords, whs] = await Promise.all([
        shopService.getOrders(),
        shopService.getWarehouses(),
      ]);
      setOrders(ords);
      setWarehouses(whs);

      // Select first order or target from URL
      if (ords.length > 0) {
        const found = ords.find((o) => o.id === targetOrderId || o.orderNumber === targetOrderId);
        setSelectedOrderId(found ? found.id : ords[0].id);
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to load tracking data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [targetOrderId]);

  const handleReroute = async (orderId, targetWhId, targetWhName) => {
    try {
      await shopService.rerouteToAlternativeWarehouse(orderId, targetWhId, targetWhName);
      toast.success(`Deficit balance routed to ${targetWhName} for secondary allocation.`);
      loadData();
    } catch (err) {
      toast.error('Failed to reroute order.');
    }
  };

  const selectedOrder = orders.find((o) => o.id === selectedOrderId);

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
        title="Replenishment Order Tracking"
        subtitle="Real-time multi-stage fulfillment visibility, multi-warehouse allocations, and alternative routing."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Order Tracking' }]}
      />

      {/* Main Grid: Orders list on Left (1 col), Order Details & Timeline on Right (2 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Orders selector list */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
              Active & Past Orders ({orders.length})
            </h3>
            <span className="text-[11px] text-gray-400">Click to inspect</span>
          </div>

          <div className="space-y-2.5 max-h-[720px] overflow-y-auto pr-1">
            {orders.map((ord) => {
              const isSelected = ord.id === selectedOrderId;
              return (
                <div
                  key={ord.id}
                  onClick={() => setSelectedOrderId(ord.id)}
                  className={[
                    'p-3.5 rounded-xl border transition-all cursor-pointer text-xs bg-white',
                    isSelected
                      ? 'border-blue-500 ring-2 ring-blue-100 shadow-sm'
                      : 'border-gray-200 hover:border-gray-300',
                  ].join(' ')}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono font-bold text-gray-900 text-sm">
                      {ord.orderNumber}
                    </span>
                    <Badge
                      variant={
                        ord.status === 'Delivered' ? 'success' :
                        ord.status === 'Dispatched' ? 'info' :
                        ord.status === 'Partially Allocated' ? 'warning' :
                        ord.status === 'Rejected' ? 'danger' : 'neutral'
                      }
                      dot
                    >
                      {ord.status}
                    </Badge>
                  </div>

                  <p className="text-gray-600 line-clamp-1 mb-2">
                    {ord.items?.map((i) => i.productName).join(', ')}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-gray-400 pt-2 border-t border-gray-100">
                    <span>📍 {ord.destinationWarehouseName}</span>
                    <span>{ord.orderDate}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Selected Order Details, Multi-Warehouse Split & Visual Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {selectedOrder ? (
            <div className="space-y-6">
              {/* Order Header Card */}
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-100 gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-gray-900 text-base">
                        Order #{selectedOrder.orderNumber}
                      </span>
                      <Badge
                        variant={
                          selectedOrder.status === 'Delivered' ? 'success' :
                          selectedOrder.status === 'Dispatched' ? 'info' :
                          selectedOrder.status === 'Partially Allocated' ? 'warning' :
                          selectedOrder.status === 'Rejected' ? 'danger' : 'neutral'
                        }
                        dot
                      >
                        {selectedOrder.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-400 font-mono mt-0.5">
                      System Reference: {selectedOrder.id} · Placed: {selectedOrder.orderDate}
                    </p>
                  </div>

                  {selectedOrder.trackingNumber && (
                    <div className="p-2 bg-indigo-50 border border-indigo-100 rounded-lg text-xs text-indigo-900 flex items-center gap-2">
                      <Truck size={16} className="text-indigo-600" />
                      <div>
                        <span className="text-[10px] text-indigo-500 uppercase font-semibold block">Waybill Tracking</span>
                        <span className="font-mono font-bold">{selectedOrder.trackingNumber}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Logistics Key Points */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-400 text-[10px] uppercase font-semibold block">Primary Destination</span>
                    <span className="font-semibold text-gray-900">{selectedOrder.destinationWarehouseName}</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-400 text-[10px] uppercase font-semibold block">Requested Items</span>
                    <span className="font-semibold text-gray-900">{selectedOrder.items?.length} commodities</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-400 text-[10px] uppercase font-semibold block">Allocation Ratio</span>
                    <span className="font-semibold text-blue-700">
                      {selectedOrder.totalAllocatedUnits || 0} / {selectedOrder.totalRequestedUnits} units
                    </span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-400 text-[10px] uppercase font-semibold block">Requisition Value</span>
                    <span className="font-semibold text-gray-900">₹{selectedOrder.totalAmount?.toLocaleString()}</span>
                  </div>
                </div>

                {selectedOrder.notes && (
                  <p className="text-xs text-gray-500 italic bg-gray-50 p-2.5 rounded-lg border border-gray-100">
                    Order Note: "{selectedOrder.notes}"
                  </p>
                )}
              </div>

              {/* Multi-Warehouse Allocation Breakdown Component */}
              <AllocationBreakdown
                order={selectedOrder}
                warehousesList={warehouses}
                onRerouteAlternative={handleReroute}
              />

              {/* Visual Status Progression & Timeline Event Logs */}
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
                <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Clock size={16} className="text-blue-600" />
                  Visual Order Fulfillment Timeline
                </h3>
                <OrderTimeline
                  currentStatus={selectedOrder.status}
                  timeline={selectedOrder.timeline || []}
                />
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400 text-xs">
              Select an order from the list to view its tracking details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
