import { useState, useEffect } from 'react';
import { Warehouse, Star, MapPin, Phone, Mail, Clock, Info, ShieldCheck, CheckCircle } from 'lucide-react';
import { shopService } from '../../services/shopService';
import PageHeader from '../../components/ui/PageHeader';
import WarehouseCard from '../../components/common/WarehouseCard';
import Modal from '../../components/ui/Modal';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { useToast } from '../../context/ToastContext';

export default function ShopWarehouses() {
  const { toast } = useToast();
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedWarehouse, setSelectedWarehouse] = useState(null);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);

  const loadWarehouses = async () => {
    try {
      setLoading(true);
      const data = await shopService.getWarehouses();
      setWarehouses(data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load warehouses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWarehouses();
  }, []);

  const handleSelectPreferred = async (warehouseId) => {
    try {
      const updated = await shopService.setPreferredWarehouse(warehouseId);
      setWarehouses(updated);
      const wh = updated.find((w) => w.id === warehouseId);
      toast.success(`"${wh?.name}" is now designated as your preferred fulfillment warehouse.`);
    } catch (err) {
      toast.error('Failed to update preferred warehouse.');
    }
  };

  const handleViewDetails = (wh) => {
    setSelectedWarehouse(wh);
    setDetailsModalOpen(true);
  };

  const preferredWarehouse = warehouses.find((w) => w.isPreferred);
  const alternativeWarehouses = warehouses.filter((w) => !w.isPreferred);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Warehouse Network & Fulfillment Routing"
        subtitle="Discover regional fulfillment centers, inspect commodity coverage, and designate your preferred primary warehouse."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Warehouses' }]}
      />

      {/* Info notice about explicit selection */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-900">
        <Info size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong>Autonomous Shop Routing:</strong> In StockSense, the shop owner directly controls supplier relationships.
          The system <em>does not automatically route orders to the physically nearest warehouse</em>. Your chosen preferred warehouse is the primary destination for all restock requests, with automated split allocation fallback to alternatives only when inventory deficits occur.
        </div>
      </div>

      {loading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <div className="space-y-8">
          {/* Section 1: Active Preferred Warehouse */}
          {preferredWarehouse && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Star size={18} className="fill-blue-600 text-blue-600" />
                <h2 className="text-base font-bold text-gray-900">
                  Current Preferred Warehouse
                </h2>
                <Badge variant="info" className="ml-2">Primary Destination</Badge>
              </div>

              <div className="max-w-2xl">
                <WarehouseCard
                  warehouse={preferredWarehouse}
                  onSelectPreferred={handleSelectPreferred}
                  onViewDetails={handleViewDetails}
                />
              </div>
            </div>
          )}

          {/* Section 2: Alternative Warehouses */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-base font-bold text-gray-900">
                  Alternative & Regional Warehouses ({alternativeWarehouses.length})
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Available fallback hubs utilized during high demand or partial stockout allocations.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {alternativeWarehouses.map((wh) => (
                <WarehouseCard
                  key={wh.id}
                  warehouse={wh}
                  onSelectPreferred={handleSelectPreferred}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Warehouse Details Modal */}
      {selectedWarehouse && (
        <Modal
          isOpen={detailsModalOpen}
          onClose={() => setDetailsModalOpen(false)}
          title={`Hub Profile: ${selectedWarehouse.name}`}
          size="lg"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider">Facility Code</span>
                <p className="font-mono font-bold text-gray-900 text-sm">{selectedWarehouse.code}</p>
              </div>
              <div className="flex items-center gap-2">
                {selectedWarehouse.isPreferred ? (
                  <Badge variant="info">★ Active Preferred Hub</Badge>
                ) : (
                  <Badge variant="neutral">Alternative Hub</Badge>
                )}
                <Badge variant="success" dot>{selectedWarehouse.status}</Badge>
              </div>
            </div>

            <p className="text-gray-600 leading-relaxed">
              {selectedWarehouse.description}
            </p>

            {/* Logistics Attributes Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[10px] uppercase font-semibold">Proximity</span>
                <span className="text-sm font-bold text-gray-900">{selectedWarehouse.distanceKm} km</span>
              </div>
              <div className="p-3 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[10px] uppercase font-semibold">Dispatch Window</span>
                <span className="text-sm font-bold text-blue-700">{selectedWarehouse.dispatchSpeed}</span>
              </div>
              <div className="p-3 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[10px] uppercase font-semibold">Storage Area</span>
                <span className="text-sm font-bold text-gray-900">{selectedWarehouse.totalCapacitySqFt.toLocaleString()} sq.ft</span>
              </div>
              <div className="p-3 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[10px] uppercase font-semibold">Facility Manager</span>
                <span className="text-xs font-semibold text-gray-800">{selectedWarehouse.manager}</span>
              </div>
              <div className="p-3 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[10px] uppercase font-semibold">Phone Contact</span>
                <span className="text-xs font-mono text-gray-800">{selectedWarehouse.phone}</span>
              </div>
              <div className="p-3 bg-white border border-gray-100 rounded-lg">
                <span className="text-gray-400 block text-[10px] uppercase font-semibold">Operating Hours</span>
                <span className="text-xs text-gray-800">{selectedWarehouse.operatingHours}</span>
              </div>
            </div>

            {/* Categories handled */}
            <div>
              <p className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Certified Handled Categories
              </p>
              <div className="flex flex-wrap gap-1.5">
                {selectedWarehouse.categoriesHandled?.map((cat) => (
                  <span key={cat} className="text-xs bg-blue-50 text-blue-700 border border-blue-100 px-2.5 py-1 rounded-md">
                    ✓ {cat}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
              <span className="text-[11px] text-gray-400">
                Location: {selectedWarehouse.location}
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => setDetailsModalOpen(false)}>
                  Close
                </Button>
                {!selectedWarehouse.isPreferred && (
                  <Button
                    size="sm"
                    variant="primary"
                    icon={Star}
                    onClick={() => {
                      handleSelectPreferred(selectedWarehouse.id);
                      setDetailsModalOpen(false);
                    }}
                  >
                    Select as Preferred
                  </Button>
                )}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
