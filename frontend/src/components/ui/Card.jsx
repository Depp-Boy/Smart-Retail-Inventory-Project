export function Card({ children, className = '', padding = 'default', onClick }) {
  const paddings = {
    none:    '',
    sm:      'p-4',
    default: 'p-5',
    lg:      'p-6',
  };

  return (
    <div
      className={[
        'bg-white rounded-xl border border-gray-200',
        'shadow-[0_1px_3px_0_rgba(0,0,0,0.07),_0_1px_2px_-1px_rgba(0,0,0,0.07)]',
        paddings[padding] || paddings.default,
        onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : '',
        className,
      ].filter(Boolean).join(' ')}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action, className = '' }) {
  return (
    <div className={['flex items-start justify-between mb-4', className].join(' ')}>
      <div>
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div className="ml-4 flex-shrink-0">{action}</div>}
    </div>
  );
}

export function StatCard({ title, value, icon: Icon, trend, trendLabel, color = 'blue', className = '' }) {
  const colors = {
    blue:   { bg: 'bg-blue-50',   icon: 'text-blue-500' },
    green:  { bg: 'bg-green-50',  icon: 'text-green-500' },
    orange: { bg: 'bg-orange-50', icon: 'text-orange-500' },
    red:    { bg: 'bg-red-50',    icon: 'text-red-500' },
    purple: { bg: 'bg-purple-50', icon: 'text-purple-500' },
  };
  const c = colors[color] || colors.blue;

  return (
    <div className={[
      'bg-white rounded-xl border border-gray-200 p-5',
      'shadow-[0_1px_3px_0_rgba(0,0,0,0.07),_0_1px_2px_-1px_rgba(0,0,0,0.07)]',
      className,
    ].join(' ')}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
          <p className="mt-1.5 text-2xl font-bold text-gray-900">{value}</p>
          {trendLabel && (
            <p className={['text-xs mt-1 font-medium', trend >= 0 ? 'text-green-600' : 'text-red-600'].join(' ')}>
              {trend >= 0 ? '▲' : '▼'} {Math.abs(trend)}% {trendLabel}
            </p>
          )}
        </div>
        {Icon && (
          <div className={['p-3 rounded-xl', c.bg].join(' ')}>
            <Icon size={22} className={c.icon} />
          </div>
        )}
      </div>
    </div>
  );
}
