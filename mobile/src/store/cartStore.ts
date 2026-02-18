/**
 * Cart Store - Simple state management for POS cart
 * Uses observer pattern for React Native compatibility
 */

import { Product, CartItem } from '../types';

type Listener = () => void;

class CartStore {
  private items: Map<string, CartItem> = new Map();
  private listeners: Set<Listener> = new Set();

  subscribe(listener: Listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    this.listeners.forEach((l) => l());
  }

  addItem(product: Product, qty = 1) {
    const existing = this.items.get(product.id);
    if (existing) {
      existing.quantity += qty;
    } else {
      this.items.set(product.id, { product, quantity: qty });
    }
    this.notify();
  }

  removeItem(productId: string) {
    this.items.delete(productId);
    this.notify();
  }

  updateQuantity(productId: string, qty: number) {
    if (qty <= 0) {
      this.removeItem(productId);
      return;
    }
    const item = this.items.get(productId);
    if (item) {
      item.quantity = qty;
      this.notify();
    }
  }

  clear() {
    this.items.clear();
    this.notify();
  }

  getItems(): CartItem[] {
    return Array.from(this.items.values());
  }

  getTotal(): number {
    return this.getItems().reduce((sum, item) => sum + item.product.price * item.quantity, 0);
  }

  getItemCount(): number {
    return this.getItems().reduce((sum, item) => sum + item.quantity, 0);
  }
}

export const cartStore = new CartStore();
