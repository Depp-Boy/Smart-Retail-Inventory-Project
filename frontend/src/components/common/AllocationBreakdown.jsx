import { Warehouse, AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react';
import Button from '../ui/Button';

export default function AllocationBreakdown({
  order,
  onRerouteAlternative,
  warehousesList = [],
  readOnly = false,
}) {
  if (!order) return null;

  const totalRequested = order.totalRequestedUnits || order.items?.reduce((s, i) => s + (i.requestedQuantity || 0), 0) || 0;
  const totalAllocated = order.totalAllocatedUnits || order.allocations?.reduce((s, a) => s + a.items.reduce((sum, it) => sum + it.quantity, 0), 0) || 0;
  const deficit = Math.max(0, totalRequested - totalAllocated);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-100 gap-2">
        <div>
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
            <Warehouse size={16} className="text-blue-600" />
            Multi-Warehouse Allocation Details
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Breakdown of source fulfillment nodes fulfilling Order #{order.orderNumber || order.id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Fulfilled:</span>
          <span className={[
            'text-xs font-bold px-2 py-0.5 rounded-full',
            deficit === 0 ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700',
          ].join(' ')}>
            {totalAllocated} / {totalRequested} units ({Math.round((totalAllocated / (totalRequested || 1)) * 100)}%)
          </span>
        </div>
      </div>

      {/* Product-level breakdown example matching spec */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider">
          SKU Allocation Summary
        </h4>
        <div className="space-y-2">
          {order.items?.map((item) => {
            const requested = item.requestedQuantity;
            const allocated = item.allocatedQuantity !== undefined ? item.allocatedQuantity : requested;
            const itemDeficit = Math.max(0, requested - allocated);

            return (
              <div key={item.productId || item.sku} className="p-3 bg-gray-50 rounded-lg border border-gray-100 text-xs">
                <div className="flex items-center justify-between font-semibold text-gray-800">
                  <span>{item.productName} ({item.sku})</span>
                  <span className="text-gray-600">
                    Required: <span className="text-gray-900">{requested} {item.unit}</span>
                  </span>
                </div>

                {/* Warehouse splits */}
                <div className="mt-2 space-y-1.5 pl-3 border-l-2 border-blue-400">
                  {order.allocations?.map((alloc) => {
                    const match = alloc.items?.find((ai) => ai.productName === item.productName);
                    if (!match) return null;
                    return (
                      <div key={alloc.warehouseId} className="flex items-center justify-between text-gray-600">
                        <span className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                          {alloc.warehouseName} {alloc.isPreferred && <span className="text-[10px] bg-blue-100 text-blue-700 px-1 rounded">Preferred</span>}:
                        </span>
                        <span className="font-medium text-gray-800">{match.quantity} {match.unit} allocated</span>
                      </div>
                    );
                  })}

                  {itemDeficit > 0 && (
                    <div className="flex items-center justify-between text-orange-700 font-medium">
                      <span className="flex items-center gap-1.5">
                        <AlertCircle size={12} className="text-orange-500" />
                        Unallocated Deficit:
                      </span>
                      <span>{itemDeficit} {item.unit} pending</span>
                    </div>
                  )}
                </div>

                <div className="mt-2 pt-2 border-t border-gray-200 flex justify-between font-semibold text-gray-900">
                  <span>Total Allocated:</span>
                  <span>{allocated} {item.unit}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active Warehouses Participating */}
      {order.allocations && order.allocations.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
            Participating Hubs ({order.allocations.length})
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {order.allocations.map((alloc) => (
              <div key={alloc.warehouseId} className="p-3 bg-white border border-gray-200 rounded-lg shadow-2xs">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-bold text-gray-900">{alloc.warehouseName}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5">Target: {alloc.dispatchTarget}</p>
                  </div>
                  <span className="text-[10px] font-semibold bg-green-50 text-green-700 border border-green-200 px-1.5 py-0.5 rounded">
                    {alloc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alternative Warehouse Reroute Interface if Deficit Exists */}
      {deficit > 0 && !readOnly && onRerouteAlternative && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-3">
          <div className="flex items-start gap-2.5">
            <AlertCircle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-bold text-amber-900">
                Alternative Warehouse Fulfillment Required
              </p>
              <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                Preferred warehouse cannot fully satisfy this request ({deficit} units unallocated). Select an alternative regional warehouse to fulfill the remaining balance.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 pt-1">
            <select
              id="alternative-wh-select"
              className="text-xs px-3 py-2 bg-white rounded-lg border border-amber-300 text-gray-800 flex-1 focus:ring-2 focus:ring-blue-500"
              defaultValue=""
            >
              <option value="" disabled>Select Alternative Warehouse...</option>
              {warehousesList
                .filter((w) => w.id !== order.destinationWarehouseId)
                .map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.distanceKm} km · {w.dispatchSpeed})
                  </option>
                ))}
            </select>
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                const el = document.getElementById('alternative-wh-select');
                if (el && el.value) {
                  const targetWh = warehousesList.find((w) => w.id === el.value);
                  onRerouteAlternative(order.id, targetWh.id, targetWh.name);
                }
              }}
            >
              Reroute Balance <ArrowRight size={13} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
