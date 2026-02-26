/**
 * API Service - HTTP client for POS AI backend
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api/v1';

interface RequestOptions {
  method?: string;
  body?: any;
  headers?: Record<string, string>;
  requireAuth?: boolean;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getAuthToken(): Promise<string | null> {
    return await AsyncStorage.getItem('auth_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const {
      method = 'GET',
      body,
      headers = {},
      requireAuth = true,
    } = options;

    const url = `${this.baseUrl}${endpoint}`;
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    };

    if (requireAuth) {
      const token = await this.getAuthToken();
      if (token) {
        requestHeaders['Authorization'] = `Bearer ${token}`;
      }
    }

    const config: RequestInit = {
      method,
      headers: requestHeaders,
    };

    if (body) {
      config.body = JSON.stringify(body);
    }

    const response = await fetch(url, config);

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: 'An error occurred',
      }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.request<{
      access_token: string;
      user_id: string;
      store_id: string;
      role: string;
    }>('/auth/login', {
      method: 'POST',
      body: { email, password },
      requireAuth: false,
    });

    // Save token
    await AsyncStorage.setItem('auth_token', response.access_token);
    await AsyncStorage.setItem('user_id', response.user_id);
    await AsyncStorage.setItem('store_id', response.store_id);
    await AsyncStorage.setItem('role', response.role);

    return response;
  }

  async logout() {
    await AsyncStorage.multiRemove([
      'auth_token',
      'user_id',
      'store_id',
      'role',
    ]);
  }

  // Product endpoints
  async getProducts(params?: {
    page?: number;
    size?: number;
    search?: string;
    category_id?: string;
    barcode?: string;
    sku?: string;
  }) {
    const filtered = Object.fromEntries(
      Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null)
    );
    const query = new URLSearchParams(
      filtered as Record<string, string>
    ).toString();
    return this.request<{
      items: any[];
      total: number;
      page: number;
      size: number;
    }>(`/products${query ? `?${query}` : ''}`);
  }

  /**
   * Lookup a product by exact barcode string (for barcode scanner use-case).
   * Returns the first matching product or null if not found.
   */
  async getProductByBarcode(barcode: string): Promise<any | null> {
    const result = await this.request<{
      items: any[];
      total: number;
    }>(`/products?barcode=${encodeURIComponent(barcode)}&size=1`);
    return result.items.length > 0 ? result.items[0] : null;
  }

  /**
   * Lookup a product by exact SKU string.
   * Returns the first matching product or null if not found.
   */
  async getProductBySku(sku: string): Promise<any | null> {
    const result = await this.request<{
      items: any[];
      total: number;
    }>(`/products?sku=${encodeURIComponent(sku)}&size=1`);
    return result.items.length > 0 ? result.items[0] : null;
  }

  async getProduct(id: string) {
    return this.request<any>(`/products/${id}`);
  }

  async createProduct(data: any) {
    return this.request<any>('/products', {
      method: 'POST',
      body: data,
    });
  }

  async updateProduct(id: string, data: any) {
    return this.request<any>(`/products/${id}`, {
      method: 'PATCH',
      body: data,
    });
  }

  async deleteProduct(id: string) {
    return this.request<void>(`/products/${id}`, {
      method: 'DELETE',
    });
  }

  // Category endpoints
  async getCategories() {
    return this.request<{
      items: any[];
      total: number;
    }>('/categories');
  }

  async createCategory(data: { name: string; description?: string }) {
    return this.request<any>('/categories', {
      method: 'POST',
      body: data,
    });
  }
}

export const api = new ApiService(API_BASE_URL);
