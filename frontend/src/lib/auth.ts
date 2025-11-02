// Authentication utilities and user database

export interface User {
  id: string;
  username: string;
  email: string;
  role: "front" | "compliance" | "legal" | "super";
  displayName: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  user?: User;
  token?: string;
  error?: string;
}

// Mock user database (hardcoded credentials for client-side auth)
const USERS: Array<User & { password: string }> = [
  {
    id: "1",
    username: "front",
    email: "front@example.com",
    password: "front123",
    role: "front",
    displayName: "Front Office User",
  },
  {
    id: "2",
    username: "compliance",
    email: "compliance@example.com",
    password: "compliance123",
    role: "compliance",
    displayName: "Compliance Officer",
  },
  {
    id: "3",
    username: "legal",
    email: "legal@example.com",
    password: "legal123",
    role: "legal",
    displayName: "Legal Counsel",
  },
  {
    id: "4",
    username: "super",
    email: "super@example.com",
    password: "super123",
    role: "super",
    displayName: "Super Administrator",
  },
];

// Validate credentials and return user if valid
export const validateCredentials = (
  credentials: LoginCredentials
): LoginResponse => {
  const user = USERS.find(
    (u) =>
      u.email === credentials.email && u.password === credentials.password
  );

  if (user) {
    // Remove password from response
    const { password, ...userWithoutPassword } = user;
    const token = generateToken(userWithoutPassword);

    return {
      success: true,
      user: userWithoutPassword,
      token,
    };
  }

  return {
    success: false,
    error: "Invalid email or password",
  };
};

// Generate a simple token (client-side only, not secure for production)
const generateToken = (user: User): string => {
  return btoa(JSON.stringify({ userId: user.id, timestamp: Date.now() }));
};

// localStorage keys
const AUTH_STORAGE_KEY = "slenth_auth";

// Save auth state to localStorage
export const saveAuthState = (authState: AuthState): void => {
  try {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authState));
  } catch (error) {
    console.error("Failed to save auth state:", error);
  }
};

// Load auth state from localStorage
export const loadAuthState = (): AuthState | null => {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error("Failed to load auth state:", error);
  }
  return null;
};

// Clear auth state from localStorage
export const clearAuthState = (): void => {
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch (error) {
    console.error("Failed to clear auth state:", error);
  }
};

// Permission checking functions
export const canManageAlert = (
  alertRole: string,
  userRole: string
): boolean => {
  // Super user can manage all alerts
  if (userRole === "super") {
    return true;
  }

  // Users can only manage alerts for their own role
  return alertRole === userRole;
};

export const canManageInternalRules = (userRole: string): boolean => {
  // Only compliance and super users can manage internal rules
  return userRole === "compliance" || userRole === "super";
};
