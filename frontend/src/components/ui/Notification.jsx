import { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

const VARIANTS = {
  success: {
    icon: CheckCircle,
    bg: 'bg-green-50 border-green-200',
    iconColor: 'text-green-500',
    text: 'text-green-800',
  },
  error: {
    icon: AlertCircle,
    bg: 'bg-red-50 border-red-200',
    iconColor: 'text-red-500',
    text: 'text-red-800',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-orange-50 border-orange-200',
    iconColor: 'text-orange-500',
    text: 'text-orange-800',
  },
  info: {
    icon: Info,
    bg: 'bg-blue-50 border-blue-200',
    iconColor: 'text-blue-500',
    text: 'text-blue-800',
  },
};

export function Toast({ message, variant = 'info', onClose, duration = 4000 }) {
  const config = VARIANTS[variant] || VARIANTS.info;
  const Icon = config.icon;

  useEffect(() => {
    if (duration > 0 && onClose) {
      const t = setTimeout(onClose, duration);
      return () => clearTimeout(t);
    }
  }, [duration, onClose]);

  return (
    <div className={[
      'flex items-start gap-3 p-4 rounded-xl border min-w-72 max-w-sm',
      'shadow-[0_4px_6px_-1px_rgba(0,0,0,0.07),_0_2px_4px_-2px_rgba(0,0,0,0.07)]',
      config.bg,
    ].join(' ')}>
      <Icon size={18} className={['mt-0.5 flex-shrink-0', config.iconColor].join(' ')} />
      <p className={['text-sm flex-1', config.text].join(' ')}>{message}</p>
      <button
        onClick={onClose}
        className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
        aria-label="Dismiss"
      >
        <X size={16} />
      </button>
    </div>
  );
}

export function Alert({ message, variant = 'info', onClose, title, className = '' }) {
  const config = VARIANTS[variant] || VARIANTS.info;
  const Icon = config.icon;
  return (
    <div className={['flex gap-3 p-4 rounded-xl border', config.bg, className].join(' ')}>
      <Icon size={18} className={['mt-0.5 flex-shrink-0', config.iconColor].join(' ')} />
      <div className="flex-1 min-w-0">
        {title && <p className={['text-sm font-medium mb-1', config.text].join(' ')}>{title}</p>}
        <p className={['text-sm', config.text].join(' ')}>{message}</p>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Dismiss"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}

// Default export — Toast container
export default function ToastContainer({ toasts, removeToast }) {
  return (
    <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-3 pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <Toast {...t} onClose={() => removeToast(t.id)} />
        </div>
      ))}
    </div>
  );
}
