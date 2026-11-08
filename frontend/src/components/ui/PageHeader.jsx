export default function PageHeader({ title, subtitle, action, breadcrumbs, className = '' }) {
  return (
    <div className={['mb-6', className].join(' ')}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1.5 text-xs text-gray-500 mb-2" aria-label="Breadcrumb">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-gray-300">/</span>}
              {crumb.href ? (
                <a href={crumb.href} className="hover:text-gray-700 transition-colors">
                  {crumb.label}
                </a>
              ) : (
                <span className={i === breadcrumbs.length - 1 ? 'text-gray-700 font-medium' : ''}>
                  {crumb.label}
                </span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-gray-900 truncate">{title}</h1>
          {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
    </div>
  );
}
