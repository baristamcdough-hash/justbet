import { create } from 'zustand';
import api from '../services/api';
import { User, AuthTokens } from '../types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (phone: string, password: string) => Promise<void>;
  register: (phone: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: true,

  login: async (phone, password) => {
    const res = await api.post<AuthTokens>('/api/auth/login', { phone, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    set({ isAuthenticated: true });

    // Fetch user profile
    const userRes = await api.get<User>('/api/auth/me');
    set({ user: userRes.data });
  },

  register: async (phone, password) => {
    const res = await api.post<AuthTokens>('/api/auth/register', { phone, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    set({ isAuthenticated: true });

    const userRes = await api.get<User>('/api/auth/me');
    set({ user: userRes.data });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    try {
      const res = await api.get<User>('/api/auth/me');
      set({ user: res.data, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },

  initialize: async () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const res = await api.get<User>('/api/auth/me');
        set({ user: res.data, isAuthenticated: true, isLoading: false });
      } catch {
        set({ isAuthenticated: false, isLoading: false });
      }
    } else {
      set({ isLoading: false });
    }
  },
}));
