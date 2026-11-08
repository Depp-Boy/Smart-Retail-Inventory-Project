import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight, X, Package2 } from 'lucide-react';
import { useIsMobile } from '../../hooks/useMediaQuery';

export default function Sidebar({ navItems = [], role = 'shop', userName = 'User', userEmail = '', onLogout }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const isMobile = useIsMobile();

  const roleLabels = {
    shop:      'Shop Owner',
    warehouse: 'Warehouse Manager',
    worker:    'Warehouse Worker',
  };
  const roleLabel = roleLabels[role] || 'User';

  // Expose mobile toggle to TopBar via window
  useEffect(() => {
    window.__sidebarToggle = () => setMobileOpen((o) => !o);
    return () => { delete window.__sidebarToggle; };
  }, []);

  // Close drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const NavContent = () => (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#1e2a3b' }}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
        <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Package2 size={17} className="text-white" />
        </div>
        {(!collapsed || isMobile) && (
          <div className="overflow-hidden">
            <p className="text-sm font-bold text-white leading-tight">StockSense</p>
            <p className="text-xs leading-tight" style={{ color: '#93c5fd' }}>{roleLabel}</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {navItems.map((section, si) => (
          <div key={si} className="mb-5">
            {section.label && (!collapsed || isMobile) && (
              <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest"
                style={{ color: 'rgba(255,255,255,0.35)' }}>
                {section.label}
              </p>
            )}
            {section.items.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  title={collapsed && !isMobile ? item.label : undefined}
                  className={[
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg mb-0.5 text-sm transition-colors',
                    active
                      ? 'bg-blue-600 text-white font-medium'
                      : 'hover:bg-white/10',
                  ].join(' ')}
                  style={active ? {} : { color: 'rgba(255,255,255,0.65)' }}
                >
                  {Icon && <Icon size={17} className="flex-shrink-0" />}
                  {(!collapsed || isMobile) && (
                    <span className="truncate">{item.label}</span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* User Footer */}
      <div className="p-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
        <div className={['flex items-center gap-3', collapsed && !isMobile ? 'justify-center' : ''].join(' ')}>
          <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(59,130,246,0.3)' }}>
            <span className="text-xs font-bold" style={{ color: '#93c5fd' }}>
              {userName?.[0]?.toUpperCase() || 'U'}
            </span>
          </div>
          {(!collapsed || isMobile) && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{userName}</p>
              <p className="text-xs truncate" style={{ color: 'rgba(255,255,255,0.45)' }}>{userEmail}</p>
            </div>
          )}
        </div>
        {(!collapsed || isMobile) && onLogout && (
          <button
            onClick={onLogout}
            className="mt-2 w-full text-left px-3 py-2 text-xs rounded-lg transition-colors hover:bg-white/10"
            style={{ color: 'rgba(255,255,255,0.45)' }}
          >
            Sign out
          </button>
        )}
      </div>
    </div>
  );

  if (isMobile) {
    return (
      <>
        {mobileOpen && (
          <div className="fixed inset-0 z-40 flex">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setMobileOpen(false)}
            />
            {/* Drawer */}
            <div className="relative z-50 w-64 h-full flex-shrink-0">
              <button
                onClick={() => setMobileOpen(false)}
                className="absolute top-3 right-3 z-10 w-7 h-7 flex items-center justify-center rounded-full text-white"
                style={{ background: 'rgba(255,255,255,0.2)' }}
                aria-label="Close menu"
              >
                <X size={14} />
              </button>
              <NavContent />
            </div>
          </div>
        )}
      </>
    );
  }

  return (
    <aside
      className="fixed top-0 left-0 h-full z-30 flex-shrink-0 transition-all duration-200"
      style={{ width: collapsed ? 72 : 256 }}
    >
      <NavContent />
      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute top-20 -right-3 w-6 h-6 rounded-full flex items-center justify-center text-white border border-white/20 hover:border-white/40 transition-colors"
        style={{ backgroundColor: '#1e2a3b' }}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>
    </aside>
  );
}
