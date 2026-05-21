import { create } from "zustand";
import { authApi } from "@/lib/api";

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  plan: string;
  subscription_status: string;
  is_verified: boolean;
  two_factor_enabled: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, totpCode?: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("access_token") : null,
  isLoading: false,
  isAuthenticated: false,

  login: async (email: string, password: string, totpCode?: string) => {
    set({ isLoading: true });
    try {
      const { data } = await authApi.login({ email, password, totp_code: totpCode });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      set({ token: data.access_token, isAuthenticated: true });
    } finally {
      set({ isLoading: false });
    }
  },

  register: async (name: string, email: string, password: string) => {
    set({ isLoading: true });
    try {
      await authApi.register({ name, email, password });
    } finally {
      set({ isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ isAuthenticated: false });
      return;
    }
    try {
      const { data } = await authApi.getMe();
      set({ user: data, isAuthenticated: true });
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ user: null, token: null, isAuthenticated: false });
    }
  },
}));
