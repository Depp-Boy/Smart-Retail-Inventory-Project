import { Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, CheckSquare, Package, Cpu, Truck, Bell, User } from 'lucide-react';
import Sidebar from '../components/navigation/Sidebar';
import TopBar from '../components/navigation/TopBar';
import { useAuth } from '../context/AuthContext';
import { useIsMobile } from '../hooks/useMediaQuery';

const workerNavItems = [
  {
    label: 'Main',
    items: [
      { label: 'Dashboard',     path: '/worker/dashboard',     icon: LayoutDashboard },
      { label: 'My Tasks',      path: '/worker/tasks',         icon: CheckSquare },
      { label: 'Inventory',     path: '/worker/inventory',     icon: Package },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Processing',    path: '/worker/processing',    icon: Cpu },
      { label: 'Dispatch',      path: '/worker/dispatch',      icon: Truck },
    ],
  },
  {
    label: 'Account',
    items: [
      { label: 'Notifications', path: '/worker/notifications', icon: Bell },
      { label: 'Profile',       path: '/worker/profile',       icon: User },
    ],
  },
];

export default function WorkerLayout() {
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
        navItems={workerNavItems}
        role="worker"
        userName={user?.name || 'Worker'}
        userEmail={user?.email || ''}
        onLogout={handleLogout}
      />
      <div
        className="flex flex-col flex-1 overflow-hidden min-w-0 transition-all duration-200"
        style={!isMobile ? { marginLeft: 256 } : {}}
      >
        <TopBar
          title="Worker Portal"
          userName={user?.name || 'Worker'}
          userEmail={user?.email || ''}
          role="Warehouse Worker"
          onLogout={handleLogout}
          notificationPath="/worker/notifications"
          notificationCount={2}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
