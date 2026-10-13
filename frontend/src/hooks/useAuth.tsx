import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole, Brand } from '../types';
import { authService } from '../services/authService';
import { brandService } from '../services/brandService';
import { checkBackendHealth } from '../services/apiClient';

interface AuthContextType {
  user: User | null;
  role: UserRole;
  isAuthenticated: boolean;
  isLoading: boolean;
  isBackendConnected: boolean;
  activeBrand: Brand | null;
  setActiveBrand: (brand: Brand | null) => void;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  switchRole: (role: UserRole) => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [activeBrand, setActiveBrand] = useState<Brand | null>(null);

  const initAuth = async () => {
    setIsLoading(true);
    try {
      const backendOk = await checkBackendHealth();
      setIsBackendConnected(backendOk);

      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);

      const brands = await brandService.listBrands();
      if (brands && brands.length > 0) {
        setActiveBrand(brands[0]);
      }
    } catch {
      // fallback handled in service
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    initAuth();
  }, []);

  const login = async (email: string, pass: string) => {
    const res = await authService.login(email, pass);
    setUser(res.user);
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  const switchRole = async (newRole: UserRole) => {
    const updated = await authService.switchRole(newRole);
    setUser(updated);
  };

  const refreshAuth = async () => {
    const currentUser = await authService.getCurrentUser();
    setUser(currentUser);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || 'investigator',
        isAuthenticated: !!user,
        isLoading,
        isBackendConnected,
        activeBrand,
        setActiveBrand,
        login,
        logout,
        switchRole,
        refreshAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
