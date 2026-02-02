// src/store/auth.store.ts
import { create } from "zustand";
import { clearTokens, saveTokens } from "@/utils/storage";

interface AuthState {
  user: any;
  isAuthenticated: boolean;
  login: (data: any) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,

  login: (data) => {
    saveTokens(data);
    set({ user: data.user, isAuthenticated: true });
  },

  logout: () => {
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },
}));
