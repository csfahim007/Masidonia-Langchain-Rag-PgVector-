import axios from 'axios';
import type { ChatStreamEvent } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

const publicApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

const AUTH_NO_REFRESH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh'];
const AUTH_PAGES = ['/login', '/register'];

const isAuthNoRefreshRequest = (url?: string) =>
  AUTH_NO_REFRESH_PATHS.some((path) => url?.includes(path));

let refreshPromise: Promise<string> | null = null;

const refreshAccessToken = async (): Promise<string> => {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) throw new Error('No refresh token');
      const response = await publicApi.post('/auth/refresh', { refresh_token: refreshToken });
      const { access_token, refresh_token: newRefreshToken } = response.data;
      localStorage.setItem('access_token', access_token);
      if (newRefreshToken) {
        localStorage.setItem('refresh_token', newRefreshToken);
      }
      return access_token;
    })().finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
};

const clearAuthAndRedirect = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  if (!AUTH_PAGES.includes(window.location.pathname)) {
    window.location.href = '/login';
  }
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry || isAuthNoRefreshRequest(originalRequest.url)) {
      return Promise.reject(error);
    }
    originalRequest._retry = true;
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) { clearAuthAndRedirect(); return Promise.reject(error); }
    try {
      const accessToken = await refreshAccessToken();
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return api(originalRequest);
    } catch {
      clearAuthAndRedirect();
      return Promise.reject(error);
    }
  }
);

export default api;

export const authAPI = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    publicApi.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    publicApi.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  updateProfile: (data: { full_name?: string }) => api.patch('/auth/me', data),
};

export const documentsAPI = {
  list: (folderId?: string) =>
    api.get('/documents', { params: folderId ? { folder_id: folderId } : {} }),
  get: (id: string) => api.get(`/documents/${id}`),
  upload: (file: File, folderId?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/upload', formData, {
      params: folderId ? { folder_id: folderId } : {},
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
  },
  bulkUpload: (files: File[], folderId?: string, onProgress?: (done: number, total: number) => void) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return api.post('/documents/bulk-upload', formData, {
      params: folderId ? { folder_id: folderId } : {},
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(event.loaded, event.total);
        }
      },
    });
  },
  delete: (id: string) => api.delete(`/documents/${id}`),
  preview: (id: string) => api.get(`/documents/${id}/preview`),
  update: (id: string, data: { title?: string; tags?: string[] }) =>
    api.patch(`/documents/${id}`, data),
};

export const foldersAPI = {
  list: (parentId?: string) =>
    api.get('/folders', { params: parentId ? { parent_id: parentId } : {} }),
  create: (name: string, parentId?: string) =>
    api.post('/folders', { name, parent_id: parentId || null }),
  rename: (id: string, name: string) => api.patch(`/folders/${id}`, { name }),
  delete: (id: string) => api.delete(`/folders/${id}`),
  moveDocument: (documentId: string, folderId?: string | null) =>
    api.patch(`/folders/documents/${documentId}/move`, { folder_id: folderId ?? null }),
};

const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export const chatAPI = {
  send: (data: { question: string; document_id?: string; conversation_id?: string }) =>
    api.post('/chat', data),
  stream: async (
    data: { question: string; document_id?: string; conversation_id?: string },
    onEvent: (event: ChatStreamEvent) => void,
  ) => {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (response.status === 401) {
      clearAuthAndRedirect();
      throw new Error('Unauthorized');
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Stream failed' }));
      throw new Error(err.detail || 'Stream failed');
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response stream');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;
        try {
          onEvent(JSON.parse(line.slice(6)) as ChatStreamEvent);
        } catch {
          /* ignore malformed chunks */
        }
      }
    }
  },
  conversations: () => api.get('/chat/conversations'),
  messages: (conversationId: string) =>
    api.get(`/chat/conversations/${conversationId}/messages`),
  deleteConversation: (conversationId: string) =>
    api.delete(`/chat/conversations/${conversationId}`),
};

export const searchAPI = {
  query: (q: string, mode = 'hybrid', documentId?: string) =>
    api.get('/search', { params: { q, mode, document_id: documentId } }),
  autocomplete: (q: string) => api.get('/search/autocomplete', { params: { q } }),
  history: () => api.get('/search/history'),
  clearHistory: () => api.delete('/search/history'),
};

export const analyticsAPI = {
  overview: () => api.get('/analytics/overview'),
  trends: (days = 7) => api.get('/analytics/trends', { params: { days } }),
  topics: () => api.get('/analytics/topics'),
  platform: () => api.get('/analytics/platform'),
};

export const getErrorMessage = (error: unknown, fallback: string): string => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
};
