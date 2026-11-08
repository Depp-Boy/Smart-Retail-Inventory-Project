import { Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Package, ShoppingBag, ClipboardList,
  Truck, Users, BarChart2, Bell, Settings, Layers,
} from 'lucide-react';
import Sidebar from '../components/navigation/Sidebar';
import TopBar from '../components/navigation/TopBar';
import { useAuth } from '../context/AuthContext';
import { useIsMobile } from '../hooks/useMediaQuery';

const warehouseNavItems = [
  {
    label: 'Main',
    items: [
      { label: 'Dashboard',     path: '/warehouse/dashboard',    icon: LayoutDashboard },
      { label: 'Inventory',     path: '/warehouse/inventory',    icon: Package },
      { label: 'Products',      path: '/warehouse/products',     icon: ShoppingBag },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Requests',      path: '/warehouse/requests',     icon: ClipboardList },
      { label: 'Orders',        path: '/warehouse/orders',       icon: Layers },
      { label: 'Allocations',   path: '/warehouse/allocations',  icon: Layers },
      { label: 'Dispatch',      path: '/warehouse/dispatch',     icon: Truck },
    ],
  },
  {
    label: 'Team',
    items: [
      { label: 'Workers',       path: '/warehouse/workers',      icon: Users },
    ],
  },
  {
    label: 'Reporting',
    items: [
      { label: 'Analytics',     path: '/warehouse/analytics',    icon: BarChart2 },
      { label: 'Notifications', path: '/warehouse/notifications', icon: Bell },
      { label: 'Settings',      path: '/warehouse/settings',     icon: Settings },
    ],
  },
];

export default function WarehouseLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar
        navItems={warehouseNavItems}
        role="warehouse"
        userName={user?.name || 'Warehouse Manager'}
        userEmail={user?.email || ''}
        onLogout={handleLogout}
      />
      <div
        className="flex flex-col flex-1 overflow-hidden min-w-0 transition-all duration-200"
        style={!isMobile ? { marginLeft: 256 } : {}}
      >
        <TopBar
          title="Warehouse Manager"
          userName={user?.name || 'Warehouse Manager'}
          userEmail={user?.email || ''}
          role="Warehouse Manager"
          onLogout={handleLogout}
          notificationPath="/warehouse/notifications"
          notificationCount={5}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
