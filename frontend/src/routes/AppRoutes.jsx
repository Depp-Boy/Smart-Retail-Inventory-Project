import { Routes, Route, Navigate } from 'react-router-dom';

// Layouts
import PublicLayout from '../layouts/PublicLayout';
import ShopLayout from '../layouts/ShopLayout';
import WarehouseLayout from '../layouts/WarehouseLayout';
import WorkerLayout from '../layouts/WorkerLayout';

// Public pages
import LandingPage from '../pages/public/LandingPage';

// Auth pages
import LoginPage from '../pages/auth/LoginPage';
import RegisterPage from '../pages/auth/RegisterPage';
import ForgotPasswordPage from '../pages/auth/ForgotPasswordPage';
import ResetPasswordPage from '../pages/auth/ResetPasswordPage';

// Shop pages
import ShopDashboard from '../pages/shop/ShopDashboard';
import ShopInventory from '../pages/shop/ShopInventory';
import ShopProducts from '../pages/shop/ShopProducts';
import ShopSales from '../pages/shop/ShopSales';
import ShopWarehouses from '../pages/shop/ShopWarehouses';
import ShopOrders from '../pages/shop/ShopOrders';
import ShopTracking from '../pages/shop/ShopTracking';
import ShopForecast from '../pages/shop/ShopForecast';
import ShopNotifications from '../pages/shop/ShopNotifications';
import ShopProfile from '../pages/shop/ShopProfile';
import ShopSettings from '../pages/shop/ShopSettings';

// Warehouse pages
import WarehouseDashboard from '../pages/warehouse/WarehouseDashboard';
import WarehouseInventory from '../pages/warehouse/WarehouseInventory';
import WarehouseProducts from '../pages/warehouse/WarehouseProducts';
import WarehouseRequests from '../pages/warehouse/WarehouseRequests';
import WarehouseOrders from '../pages/warehouse/WarehouseOrders';
import WarehouseAllocations from '../pages/warehouse/WarehouseAllocations';
import WarehouseDispatch from '../pages/warehouse/WarehouseDispatch';
import WarehouseWorkers from '../pages/warehouse/WarehouseWorkers';
import WarehouseAnalytics from '../pages/warehouse/WarehouseAnalytics';
import WarehouseNotifications from '../pages/warehouse/WarehouseNotifications';
import WarehouseSettings from '../pages/warehouse/WarehouseSettings';

// Worker pages
import WorkerDashboard from '../pages/worker/WorkerDashboard';
import WorkerTasks from '../pages/worker/WorkerTasks';
import WorkerInventory from '../pages/worker/WorkerInventory';
import WorkerProcessing from '../pages/worker/WorkerProcessing';
import WorkerDispatch from '../pages/worker/WorkerDispatch';
import WorkerNotifications from '../pages/worker/WorkerNotifications';
import WorkerProfile from '../pages/worker/WorkerProfile';

// ─── Not Found ────────────────────────────────────────────────────────────────
function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4 text-center">
      <div className="text-6xl font-extrabold text-gray-200 mb-4">404</div>
      <h1 className="text-xl font-bold text-gray-900 mb-2">Page not found</h1>
      <p className="text-sm text-gray-500 mb-6">
        The page you are looking for does not exist or has been moved.
      </p>
      <a href="/" className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm font-medium px-5 py-2.5 rounded-lg hover:bg-blue-700 transition-colors">
        ← Back to Home
      </a>
    </div>
  );
}

// ─── App Routes ───────────────────────────────────────────────────────────────
export default function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route element={<PublicLayout />}>
        <Route path="/"                index element={<LandingPage />} />
        <Route path="/login"                 element={<LoginPage />} />
        <Route path="/register"              element={<RegisterPage />} />
        <Route path="/forgot-password"       element={<ForgotPasswordPage />} />
        <Route path="/reset-password"        element={<ResetPasswordPage />} />
      </Route>

      {/* Shop Owner */}
      <Route path="/shop" element={<ShopLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard"     element={<ShopDashboard />} />
        <Route path="inventory"     element={<ShopInventory />} />
        <Route path="products"      element={<ShopProducts />} />
        <Route path="sales"         element={<ShopSales />} />
        <Route path="warehouses"    element={<ShopWarehouses />} />
        <Route path="orders"        element={<ShopOrders />} />
        <Route path="tracking"      element={<ShopTracking />} />
        <Route path="forecast"      element={<ShopForecast />} />
        <Route path="notifications" element={<ShopNotifications />} />
        <Route path="profile"       element={<ShopProfile />} />
        <Route path="settings"      element={<ShopSettings />} />
      </Route>

      {/* Warehouse Manager */}
      <Route path="/warehouse" element={<WarehouseLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard"     element={<WarehouseDashboard />} />
        <Route path="inventory"     element={<WarehouseInventory />} />
        <Route path="products"      element={<WarehouseProducts />} />
        <Route path="requests"      element={<WarehouseRequests />} />
        <Route path="orders"        element={<WarehouseOrders />} />
        <Route path="allocations"   element={<WarehouseAllocations />} />
        <Route path="dispatch"      element={<WarehouseDispatch />} />
        <Route path="workers"       element={<WarehouseWorkers />} />
        <Route path="analytics"     element={<WarehouseAnalytics />} />
        <Route path="notifications" element={<WarehouseNotifications />} />
        <Route path="settings"      element={<WarehouseSettings />} />
      </Route>

      {/* Warehouse Worker */}
      <Route path="/worker" element={<WorkerLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard"     element={<WorkerDashboard />} />
        <Route path="tasks"         element={<WorkerTasks />} />
        <Route path="inventory"     element={<WorkerInventory />} />
        <Route path="processing"    element={<WorkerProcessing />} />
        <Route path="dispatch"      element={<WorkerDispatch />} />
        <Route path="notifications" element={<WorkerNotifications />} />
        <Route path="profile"       element={<WorkerProfile />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
