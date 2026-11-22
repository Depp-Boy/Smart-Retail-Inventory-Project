import { Warehouse, Star, MapPin, Phone, Mail, Clock, Check, Eye } from 'lucide-react';
import Badge from '../ui/Badge';
import Button from '../ui/Button';

export default function WarehouseCard({
  warehouse,
  onSelectPreferred,
  onViewDetails,
  onUpdateRank,
}) {
  const isPreferred = warehouse.isPreferred;

  return (
    <div
      className={[
        'bg-white rounded-xl border transition-all p-5 shadow-xs flex flex-col justify-between',
        isPreferred
          ? 'border-blue-500 ring-2 ring-blue-100'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-md',
      ].join(' ')}
    >
      <div>
        {/* Top Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            <div className={[
              'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
              isPreferred ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700',
            ].join(' ')}>
              <Warehouse size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 leading-snug">
                {warehouse.name}
              </h3>
              <p className="text-[11px] font-mono text-gray-400">
                Code: {warehouse.code}
              </p>
            </div>
          </div>
          {isPreferred ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-100 text-blue-700 border border-blue-200 shadow-2xs">
              <Star size={12} className="fill-blue-600 text-blue-600" />
              Preferred
            </span>
          ) : (
            <Badge variant="neutral" className="text-[11px]">
              Alternative #{warehouse.ranking || 2}
            </Badge>
          )}
        </div>

        {/* Location & Distance */}
        <div className="space-y-1.5 mb-4 text-xs text-gray-600">
          <p className="flex items-start gap-1.5">
            <MapPin size={13} className="text-gray-400 mt-0.5 flex-shrink-0" />
            <span className="line-clamp-2">{warehouse.location}</span>
          </p>
          <div className="flex items-center gap-3 pt-1 text-[11px] text-gray-500">
            <span className="font-semibold text-gray-800 bg-gray-100 px-2 py-0.5 rounded">
              📍 {warehouse.distanceKm} km away
            </span>
            <span>⚡ {warehouse.dispatchSpeed}</span>
          </div>
        </div>

        {/* Categories preview */}
        <div className="mb-4">
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
            Categories Stocked
          </p>
          <div className="flex flex-wrap gap-1">
            {warehouse.categoriesHandled?.slice(0, 3).map((cat) => (
              <span key={cat} className="text-[10px] bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                {cat}
              </span>
            ))}
            {warehouse.categoriesHandled?.length > 3 && (
              <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                +{warehouse.categoriesHandled.length - 3} more
              </span>
            )}
          </div>
        </div>

        {/* Capacity & Operating Status */}
        <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100 mb-4 space-y-1 text-xs">
          <div className="flex justify-between text-gray-600 text-[11px]">
            <span>Hub Capacity:</span>
            <span className="font-medium text-gray-800">{warehouse.totalCapacitySqFt.toLocaleString()} sq.ft</span>
          </div>
          <div className="flex justify-between text-gray-600 text-[11px]">
            <span>Status:</span>
            <span className="font-semibold text-green-700 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              {warehouse.status}
            </span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="pt-3 border-t border-gray-100 flex items-center justify-between gap-2">
        <button
          onClick={() => onViewDetails(warehouse)}
          className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 py-1"
        >
          <Eye size={13} /> View Details
        </button>

        {!isPreferred ? (
          <Button
            size="xs"
            variant="secondary"
            onClick={() => onSelectPreferred(warehouse.id)}
            icon={Star}
          >
            Set as Preferred
          </Button>
        ) : (
          <span className="text-xs text-blue-700 font-semibold flex items-center gap-1">
            <Check size={14} className="text-blue-600" /> Active Destination
          </span>
        )}
      </div>
    </div>
  );
}
