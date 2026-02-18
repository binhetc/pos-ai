// Product & Category types matching backend schemas

export interface Product {
  id: string;
  name: string;
  description: string | null;
  sku: string;
  barcode: string | null;
  price: number;
  cost_price: number | null;
  unit: string;
  image_url: string | null;
  in_stock: number;
  min_stock: number;
  is_active: boolean;
  category_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: string;
  name: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export interface InventoryAdjustRequest {
  quantity_change: number;
  reason: 'purchase' | 'sale' | 'adjustment' | 'damage' | 'return';
  note?: string;
}
