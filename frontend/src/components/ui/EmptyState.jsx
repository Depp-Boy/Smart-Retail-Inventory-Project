import { Package } from 'lucide-react';

export default function EmptyState({
  icon: Icon = Package,
  title = 'No data found',
  description = 'There is nothing here yet.',
  action,
  className = '',
}) {
  return (
    <div className={['flex flex-col items-center justify-center py-16 text-center', className].join(' ')}>
      <div className="p-4 bg-gray-100 rounded-full mb-4">
        <Icon size={32} className="text-gray-400" />
      </div>
      <h3 className="text-base font-semibold text-gray-700">{title}</h3>
      <p className="text-sm text-gray-500 mt-1 max-w-xs">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'An unexpected error occurred. Please try again.',
  action,
  className = '',
}) {
  return (
    <div className={['flex flex-col items-center justify-center py-16 text-center', className].join(' ')}>
      <div className="p-4 bg-red-50 rounded-full mb-4">
        <svg className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-gray-700">{title}</h3>
      <p className="text-sm text-gray-500 mt-1 max-w-xs">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
