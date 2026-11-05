import {
  CheckCircle, Clock, AlertTriangle, Truck, Package, XCircle, ArrowRight
} from 'lucide-react';

const STATUS_ICONS = {
  Pending: { icon: Clock, color: 'text-amber-500', bg: 'bg-amber-100', border: 'border-amber-300' },
  Accepted: { icon: CheckCircle, color: 'text-blue-500', bg: 'bg-blue-100', border: 'border-blue-300' },
  'Partially Allocated': { icon: AlertTriangle, color: 'text-orange-500', bg: 'bg-orange-100', border: 'border-orange-300' },
  Processing: { icon: Package, color: 'text-purple-500', bg: 'bg-purple-100', border: 'border-purple-300' },
  Dispatched: { icon: Truck, color: 'text-indigo-500', bg: 'bg-indigo-100', border: 'border-indigo-300' },
  Delivered: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', border: 'border-green-300' },
  Rejected: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', border: 'border-red-300' },
  Cancelled: { icon: XCircle, color: 'text-gray-500', bg: 'bg-gray-100', border: 'border-gray-300' },
  Expired: { icon: Clock, color: 'text-gray-400', bg: 'bg-gray-100', border: 'border-gray-200' },
};

const STANDARD_STEPS = ['Pending', 'Accepted', 'Processing', 'Dispatched', 'Delivered'];

export default function OrderTimeline({ currentStatus = 'Pending', timeline = [], className = '' }) {
  const isRejected = currentStatus === 'Rejected';
  const isCancelled = currentStatus === 'Cancelled';
  const isPartial = currentStatus === 'Partially Allocated';

  const currentStepIndex = STANDARD_STEPS.indexOf(currentStatus);

  return (
    <div className={['space-y-6', className].join(' ')}>
      {/* Horizontal Step Progression Bar (Standard Flow) */}
      {!isRejected && !isCancelled && (
        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
            Fulfillment Stage
          </p>
          <div className="flex items-center justify-between relative">
            <div className="absolute top-4 left-6 right-6 h-0.5 bg-gray-200 -z-0" />
            {STANDARD_STEPS.map((step, idx) => {
              const Icon = STATUS_ICONS[step]?.icon || Clock;
              const isPast = currentStepIndex > idx || (isPartial && idx <= 1);
              const isCurrent = currentStatus === step || (isPartial && step === 'Accepted');

              return (
                <div key={step} className="flex flex-col items-center relative z-10">
                  <div
                    className={[
                      'w-8 h-8 rounded-full flex items-center justify-center transition-all border-2',
                      isCurrent
                        ? 'bg-blue-600 border-blue-600 text-white shadow-md ring-4 ring-blue-100'
                        : isPast
                        ? 'bg-green-600 border-green-600 text-white'
                        : 'bg-white border-gray-300 text-gray-400',
                    ].join(' ')}
                  >
                    <Icon size={14} />
                  </div>
                  <span
                    className={[
                      'text-[11px] sm:text-xs mt-2 font-medium text-center',
                      isCurrent ? 'text-blue-600 font-bold' : isPast ? 'text-gray-800' : 'text-gray-400',
                    ].join(' ')}
                  >
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Exception banner for Rejected or Cancelled */}
      {(isRejected || isCancelled) && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
          <XCircle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-red-900">
              Order {currentStatus}
            </h4>
            <p className="text-xs text-red-700 mt-0.5">
              This order did not progress through normal fulfillment. See logged timeline events below for details and alternative actions.
            </p>
          </div>
        </div>
      )}

      {/* Detailed Chronological Event Logs */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Status Activity Log
        </h4>
        <div className="space-y-4 relative pl-6 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200">
          {timeline.map((entry, idx) => {
            const config = STATUS_ICONS[entry.status] || STATUS_ICONS.Pending;
            const Icon = config.icon;

            return (
              <div key={idx} className="relative">
                <div
                  className={[
                    'absolute -left-6 top-0.5 w-5 h-5 rounded-full flex items-center justify-center border bg-white',
                    config.border,
                  ].join(' ')}
                >
                  <Icon size={11} className={config.color} />
                </div>
                <div className="bg-white p-3 rounded-lg border border-gray-100 shadow-2xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                    <span className={['text-xs font-semibold px-2 py-0.5 rounded-full inline-block w-fit', config.bg, config.color].join(' ')}>
                      {entry.status}
                    </span>
                    <span className="text-[11px] text-gray-400 font-mono">
                      {entry.date}
                    </span>
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed mt-1">
                    {entry.note}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
