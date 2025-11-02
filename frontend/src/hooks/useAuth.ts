import { useAuthContext } from "@/contexts/AuthContext";

// Custom hook to simplify accessing authentication context
export const useAuth = () => {
  return useAuthContext();
};
