import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, AuthState } from '@/types/auth';
import { authService } from '@/services/authService';
import { storeToken } from '@/utils/auth';

interface AuthStore extends AuthState {
  login: (credentials: { username: string; password: string }) => Promise<void>;
  register: (data: { username: string; email: string; password: string }) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (credentials) => {
        set({ isLoading: true });
        try {
          const response = await authService.login(credentials);
          const token = response.access_token;

          // Store token in both Zustand and direct localStorage
          storeToken(token);

          set({
            user: response.user,
            token: token,
            isAuthenticated: true,
          });
        } catch (error) {
          throw error;
        } finally {
          set({ isLoading: false });
        }
      },

      register: async (data) => {
        set({ isLoading: true });
        try {
          const response = await authService.register(data);
          const token = response.access_token;

          // Store token in both Zustand and direct localStorage
          storeToken(token);

          set({
            user: response.user,
            token: token,
            isAuthenticated: true,
          });
        } catch (error) {
          throw error;
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        authService.logout().catch(() => {
          // Ignore logout errors
        });
        get().clearAuth();
      },

      refreshToken: async () => {
        try {
          const response = await authService.refreshToken();
          set({
            token: response.access_token,
          });
        } catch (error) {
          get().clearAuth();
          throw error;
        }
      },

      setUser: (user) => {
        set({ user, isAuthenticated: !!user });
      },

      setToken: (token) => {
        set({ token, isAuthenticated: !!token });
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      clearAuth: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);