import { Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Package, ShoppingCart, BarChart2, Warehouse,
  ClipboardList, Truck, TrendingUp, Bell, User, Settings,
} from 'lucide-react';
import Sidebar from '../components/navigation/Sidebar';
import TopBar from '../components/navigation/TopBar';
import { useAuth } from '../context/AuthContext';
import { useIsMobile } from '../hooks/useMediaQuery';

const shopNavItems = [
  {
    label: 'Main',
    items: [
      { label: 'Dashboard',     path: '/shop/dashboard',     icon: LayoutDashboard },
      { label: 'Inventory',     path: '/shop/inventory',     icon: Package },
      { label: 'Products',      path: '/shop/products',      icon: ShoppingCart },
      { label: 'Sales',         path: '/shop/sales',         icon: BarChart2 },
    ],
  },
  {
    label: 'Replenishment',
    items: [
      { label: 'Warehouses',    path: '/shop/warehouses',    icon: Warehouse },
      { label: 'Orders',        path: '/shop/orders',        icon: ClipboardList },
      { label: 'Tracking',      path: '/shop/tracking',      icon: Truck },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { label: 'Forecast',      path: '/shop/forecast',      icon: TrendingUp },
    ],
  },
  {
    label: 'Account',
    items: [
      { label: 'Notifications', path: '/shop/notifications', icon: Bell },
      { label: 'Profile',       path: '/shop/profile',       icon: User },
      { label: 'Settings',      path: '/shop/settings',      icon: Settings },
    ],
  },
];

export default function ShopLayout() {
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
        navItems={shopNavItems}
        role="shop"
        userName={user?.name || 'Shop Owner'}
        userEmail={user?.email || ''}
        onLogout={handleLogout}
      />
      <div
        className="flex flex-col flex-1 overflow-hidden min-w-0 transition-all duration-200"
        style={!isMobile ? { marginLeft: 256 } : {}}
      >
        <TopBar
          title="Shop Dashboard"
          userName={user?.name || 'Shop Owner'}
          userEmail={user?.email || ''}
          role="Shop Owner"
          onLogout={handleLogout}
          notificationPath="/shop/notifications"
          notificationCount={3}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
