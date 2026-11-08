import { createContext, useContext, useState, useCallback } from 'react';

// Auth context — frontend-only demo, not connected to Supabase yet
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  // Demo login — replace with real auth in next phase
  const login = useCallback(async (email, password, role) => {
    setLoading(true);
    // Simulate async call
    await new Promise((r) => setTimeout(r, 800));
    const demoUser = {
      id: 'demo-user-1',
      email,
      role: role || 'shop',
      name: email.split('@')[0].replace(/\./g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
    };
    setUser(demoUser);
    setLoading(false);
    return { success: true, user: demoUser };
  }, []);

  const logout = useCallback(() => {
    setUser(null);
  }, []);

  const isAuthenticated = Boolean(user);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
