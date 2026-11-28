import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { getToken, setToken, clearToken } from '../services/api';

const AuthContext = createContext(null);

export function mapBackendRoleToFrontend(backendRole) {
  switch (backendRole?.toUpperCase()) {
    case 'SHOP_OWNER':
      return 'shop';
    case 'WAREHOUSE_MANAGER':
      return 'warehouse';
    case 'WAREHOUSE_WORKER':
      return 'worker';
    case 'ADMIN':
      return 'admin';
    default:
      return backendRole?.toLowerCase() || 'shop';
  }
}

export function mapFrontendRoleToBackend(frontendRole) {
  switch (frontendRole?.toLowerCase()) {
    case 'shop':
      return 'SHOP_OWNER';
    case 'warehouse':
      return 'WAREHOUSE_MANAGER';
    case 'worker':
      return 'WAREHOUSE_WORKER';
    case 'admin':
      return 'ADMIN';
    default:
      return frontendRole?.toUpperCase() || 'SHOP_OWNER';
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('stocksense_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);

  // Restore authenticated session on mount using stored token
  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      const token = getToken();
      if (!token) {
        if (isMounted) setInitializing(false);
        return;
      }

      try {
        const profile = await api.auth.getMe();
        if (isMounted && profile) {
          const authUser = {
            id: profile.user_id,
            userId: profile.user_id,
            name: profile.name,
            email: profile.email,
            phone: profile.phone,
            locationId: profile.location_id,
            backendRole: profile.role,
            role: mapBackendRoleToFrontend(profile.role),
          };
          setUser(authUser);
          localStorage.setItem('stocksense_user', JSON.stringify(authUser));
        }
      } catch (err) {
        console.warn('Session restoration failed:', err);
        clearToken();
        localStorage.removeItem('stocksense_user');
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setInitializing(false);
      }
    }

    restoreSession();
    return () => { isMounted = false; };
  }, []);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const tokenResp = await api.auth.login(email.trim(), password);

      if (tokenResp?.access_token) {
        setToken(tokenResp.access_token);
      }

      const profile = await api.auth.getMe();
      const authUser = {
        id: profile.user_id,
        userId: profile.user_id,
        name: profile.name,
        email: profile.email,
        phone: profile.phone,
        locationId: profile.location_id,
        backendRole: profile.role,
        role: mapBackendRoleToFrontend(profile.role),
      };

      setUser(authUser);
      localStorage.setItem('stocksense_user', JSON.stringify(authUser));
      setLoading(false);
      return { success: true, user: authUser };
    } catch (err) {
      setLoading(false);
      return {
        success: false,
        error: err.detail || err.message || 'Invalid email or password.',
      };
    }
  }, []);

  const register = useCallback(async (formData) => {
    setLoading(true);
    try {
      // Public registration is strictly restricted to SHOP_OWNER
      const payload = {
        name: formData.fullName.trim(),
        email: formData.email.toLowerCase().trim(),
        password: formData.password,
        role: 'SHOP_OWNER',
        phone: formData.phone?.trim() || null,
        location_name: formData.shopName?.trim() || null,
        location_type: 'SHOP',
        location_address: formData.shopAddress?.trim() || null,
      };

      const result = await api.auth.register(payload);
      setLoading(false);
      return { success: true, user: result };
    } catch (err) {
      setLoading(false);
      return {
        success: false,
        error: err.detail || err.message || 'Registration failed.',
      };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch {
      // Ignore network errors during logout
    } finally {
      clearToken();
      localStorage.removeItem('stocksense_user');
      setUser(null);
    }
  }, []);

  const changePassword = useCallback(async (currentPassword, newPassword) => {
    return api.auth.changePassword(currentPassword, newPassword);
  }, []);

  const isAuthenticated = Boolean(user && getToken());

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        initializing,
        isAuthenticated,
        login,
        register,
        logout,
        changePassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
