import { useState } from 'react';
import { Menu, Bell, ChevronDown, User, Settings, LogOut, Package2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useIsMobile } from '../../hooks/useMediaQuery';

export default function TopBar({
  title,
  userName,
  userEmail,
  role,
  onLogout,
  notificationCount = 0,
  notificationPath = '#',
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const isMobile = useIsMobile();

  const handleMenuToggle = () => {
    if (typeof window !== 'undefined' && typeof window.__sidebarToggle === 'function') {
      window.__sidebarToggle();
    }
  };

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 md:px-6 sticky top-0 z-20 flex-shrink-0">
      {/* Left */}
      <div className="flex items-center gap-3 min-w-0">
        {isMobile && (
          <button
            onClick={handleMenuToggle}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors flex-shrink-0"
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
        )}
        {isMobile && (
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-blue-600 rounded-md flex items-center justify-center flex-shrink-0">
              <Package2 size={13} className="text-white" />
            </div>
            <span className="text-sm font-bold text-gray-900">StockSense</span>
          </div>
        )}
        {!isMobile && title && (
          <h2 className="text-sm font-semibold text-gray-600 truncate">{title}</h2>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {/* Notifications */}
        <Link
          to={notificationPath}
          className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
          aria-label={`Notifications${notificationCount > 0 ? ` (${notificationCount})` : ''}`}
        >
          <Bell size={20} />
          {notificationCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
              {notificationCount > 9 ? '9+' : notificationCount}
            </span>
          )}
        </Link>

        {/* Profile dropdown */}
        <div className="relative ml-1">
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex items-center gap-2 px-1.5 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            aria-expanded={profileOpen}
            aria-haspopup="true"
          >
            <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-white leading-none">
                {userName?.[0]?.toUpperCase() || 'U'}
              </span>
            </div>
            {!isMobile && (
              <>
                <div className="text-left hidden sm:block max-w-32">
                  <p className="text-sm font-medium text-gray-900 leading-none truncate">{userName}</p>
                  {role && (
                    <p className="text-xs text-gray-400 leading-none mt-0.5 truncate">{role}</p>
                  )}
                </div>
                <ChevronDown size={14} className="text-gray-400 flex-shrink-0" />
              </>
            )}
          </button>

          {profileOpen && (
            <>
              {/* Close backdrop */}
              <div className="fixed inset-0 z-40" onClick={() => setProfileOpen(false)} />
              <div className="absolute right-0 top-full mt-2 w-52 bg-white border border-gray-200 rounded-xl shadow-lg z-50">
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="text-sm font-semibold text-gray-900 truncate">{userName}</p>
                  <p className="text-xs text-gray-500 truncate mt-0.5">{userEmail}</p>
                </div>
                <div className="py-1">
                  <Link
                    to="profile"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <User size={15} className="text-gray-400" />
                    Profile
                  </Link>
                  <Link
                    to="settings"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Settings size={15} className="text-gray-400" />
                    Settings
                  </Link>
                </div>
                <div className="py-1 border-t border-gray-100">
                  <button
                    onClick={() => { setProfileOpen(false); onLogout?.(); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <LogOut size={15} />
                    Sign out
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
