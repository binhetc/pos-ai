import { useState, useEffect, useCallback } from 'react';
import { cartStore } from '../store/cartStore';
import { Product, CartItem } from '../types';

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [total, setTotal] = useState(0);
  const [itemCount, setItemCount] = useState(0);

  useEffect(() => {
    const update = () => {
      setItems(cartStore.getItems());
      setTotal(cartStore.getTotal());
      setItemCount(cartStore.getItemCount());
    };
    update();
    return cartStore.subscribe(update);
  }, []);

  const addItem = useCallback((product: Product, qty?: number) => cartStore.addItem(product, qty), []);
  const removeItem = useCallback((id: string) => cartStore.removeItem(id), []);
  const updateQuantity = useCallback((id: string, qty: number) => cartStore.updateQuantity(id, qty), []);
  const clear = useCallback(() => cartStore.clear(), []);

  return { items, total, itemCount, addItem, removeItem, updateQuantity, clear };
}
