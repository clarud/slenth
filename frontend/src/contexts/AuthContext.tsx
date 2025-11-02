import React, { createContext, useState, useEffect, ReactNode } from "react";
import {
  User,
  AuthState,
  LoginCredentials,
  LoginResponse,
  validateCredentials,
  saveAuthState,
  loadAuthState,
  clearAuthState,
  canManageAlert as checkCanManageAlert,
  canManageInternalRules as checkCanManageInternalRules,
} from "@/lib/auth";

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<LoginResponse>;
  logout: () => void;
  canManageAlert: (alertRole: string) => boolean;
  canManageInternalRules: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null,
  });

  // Load auth state from localStorage on mount
  useEffect(() => {
    const storedAuth = loadAuthState();
    if (storedAuth && storedAuth.isAuthenticated) {
      setAuthState(storedAuth);
    }
  }, []);

  // Login function
  const login = async (
    credentials: LoginCredentials
  ): Promise<LoginResponse> => {
    return new Promise((resolve) => {
      // Simulate async API call
      setTimeout(() => {
        const response = validateCredentials(credentials);

        if (response.success && response.user && response.token) {
          const newAuthState: AuthState = {
            isAuthenticated: true,
            user: response.user,
            token: response.token,
          };

          setAuthState(newAuthState);
          saveAuthState(newAuthState);
        }

        resolve(response);
      }, 500); // Simulate network delay
    });
  };

  // Logout function
  const logout = () => {
    setAuthState({
      isAuthenticated: false,
      user: null,
      token: null,
    });
    clearAuthState();
  };

  // Permission checking functions
  const canManageAlert = (alertRole: string): boolean => {
    if (!authState.user) return false;
    return checkCanManageAlert(alertRole, authState.user.role);
  };

  const canManageInternalRules = (): boolean => {
    if (!authState.user) return false;
    return checkCanManageInternalRules(authState.user.role);
  };

  const contextValue: AuthContextType = {
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    login,
    logout,
    canManageAlert,
    canManageInternalRules,
  };

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
};

export const useAuthContext = () => {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return context;
};
