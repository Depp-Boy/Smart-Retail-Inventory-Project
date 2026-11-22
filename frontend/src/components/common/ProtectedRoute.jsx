import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { FullPageLoader } from '../ui/LoadingSpinner';

/**
 * ProtectedRoute — wraps a route with authentication and optional role checks.
 *
 * Usage:
 *   <ProtectedRoute allowedRoles={['shop', 'admin']}>
 *     <ShopDashboard />
 *   </ProtectedRoute>
 *
 * - Unauthenticated users → redirect to /login (preserving intended URL in state)
 * - Wrong role → redirect to their own role dashboard
 * - Loading (restoring session) → shows FullPageLoader
 */
export default function ProtectedRoute({ children, allowedRoles = [] }) {
  const { user, isAuthenticated, initializing } = useAuth();
  const location = useLocation();

  if (initializing) {
    return <FullPageLoader message="Restoring session..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles.length > 0 && !allowedRoles.includes(user?.role)) {
    // Redirect to the user's correct role dashboard
    const dashboards = {
      shop: '/shop/dashboard',
      warehouse: '/warehouse/dashboard',
      worker: '/worker/dashboard',
      admin: '/shop/dashboard',
    };
    const redirect = dashboards[user?.role] || '/login';
    return <Navigate to={redirect} replace />;
  }

  return children;
}
