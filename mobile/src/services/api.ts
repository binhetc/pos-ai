/**
 * POS AI - API Service
 * Connects to FastAPI backend for products, categories, inventory
 */

import { Product, Category, ProductListResponse, InventoryAdjustRequest } from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Products ──────────────────────────────────────────────
export const productsApi = {
  list: (params?: { page?: number; page_size?: number; category_id?: string; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    if (params?.category_id) qs.set('category_id', params.category_id);
    if (params?.search) qs.set('search', params.search);
    return request<ProductListResponse>(`/products?${qs}`);
  },

  get: (id: string) => request<Product>(`/products/${id}`),

  getByBarcode: (barcode: string) => request<Product>(`/products/barcode/${barcode}`),

  create: (data: Partial<Product>) =>
    request<Product>('/products', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: string, data: Partial<Product>) =>
    request<Product>(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  delete: (id: string) => request<void>(`/products/${id}`, { method: 'DELETE' }),
};

// ── Categories ────────────────────────────────────────────
export const categoriesApi = {
  list: () => request<Category[]>('/categories'),

  create: (data: Partial<Category>) =>
    request<Category>('/categories', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: string, data: Partial<Category>) =>
    request<Category>(`/categories/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  delete: (id: string) => request<void>(`/categories/${id}`, { method: 'DELETE' }),
};

// ── Inventory ─────────────────────────────────────────────
export const inventoryApi = {
  adjust: (productId: string, data: InventoryAdjustRequest) =>
    request(`/inventory/${productId}/adjust`, { method: 'POST', body: JSON.stringify(data) }),

  history: (productId: string, limit = 50) =>
    request(`/inventory/${productId}/history?limit=${limit}`),
};
