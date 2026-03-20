import axios from 'axios';
import type {
  TunnelStatus,
  TunnelCreate,
  TunnelResponse,
  RequestLogPage,
  RequestLogDetail,
  AuthResponse,
  User,
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_URL || 'https://api.tunnel.dev';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tunnel_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const tunnelApi = {
  createTunnel: async (data: TunnelCreate): Promise<TunnelResponse> => {
    const response = await api.post<TunnelResponse>('/tunnels', data);
    return response.data;
  },

  getTunnelStatus: async (slug: string): Promise<TunnelStatus> => {
    const response = await api.get<TunnelStatus>(`/tunnels/${slug}`);
    return response.data;
  },

  expireTunnel: async (slug: string) => {
    const response = await api.delete(`/tunnels/${slug}`);
    return response.data;
  },

  getRequestLogs: async (
    slug: string,
    params?: { page?: number; limit?: number; method?: string; status_min?: number; path?: string }
  ): Promise<RequestLogPage> => {
    const response = await api.get<RequestLogPage>(`/tunnels/${slug}/requests`, { params });
    return response.data;
  },

  getRequestDetail: async (slug: string, requestId: string): Promise<RequestLogDetail> => {
    const response = await api.get<RequestLogDetail>(`/tunnels/${slug}/requests/${requestId}`);
    return response.data;
  },

  updateSettings: async (slug: string, data: Record<string, unknown>) => {
    const response = await api.patch(`/tunnels/${slug}/settings`, data);
    return response.data;
  },
};

export const authApi = {
  googleCallback: async (code: string, redirect_uri: string): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/google', { code, redirect_uri });
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  getDeviceCode: async () => {
    const response = await api.get('/auth/device');
    return response.data;
  },
};

export default api;
