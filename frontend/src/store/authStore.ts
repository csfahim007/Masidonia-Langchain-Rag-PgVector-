import { create } from 'zustand';
import type { User } from '../types';
import { authAPI } from '../services/api';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name?: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  setUser: (user: User) => void;
}

let loadUserPromise: Promise<void> | null = null;

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email: string, password: string) => {
    const response = await authAPI.login({ email, password });
    const { access_token, refresh_token, user } = response.data;

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);

    set({ user, isAuthenticated: true, isLoading: false });
  },

  register: async (email: string, password: string, full_name?: string) => {
    await authAPI.register({ email, password, full_name });
  },

  logout: async () => {
    try {
      await authAPI.logout();
    } catch {
      // Clear local session even if server logout fails
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  loadUser: async () => {
    if (loadUserPromise) {
      return loadUserPromise;
    }

    loadUserPromise = (async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          set({ user: null, isLoading: false, isAuthenticated: false });
          return;
        }

        set({ isLoading: true });

        const response = await authAPI.getMe();
        set({ user: response.data, isAuthenticated: true, isLoading: false });
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    })().finally(() => {
      loadUserPromise = null;
    });

    return loadUserPromise;
  },

  setUser: (user: User) => set({ user }),
}));
