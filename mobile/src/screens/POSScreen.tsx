/**
 * POSScreen - Màn hình bán hàng chính
 * Layout: [Product Grid (65%)] | [Cart Panel (35%)]
 * Trên: SearchBar + CategoryBar
 * Giữa: Product Grid (tap để thêm giỏ)
 * Phải: Cart Panel (qty, total, checkout)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, Alert, ActivityIndicator } from 'react-native';

import { Product, Category } from '../types';
import { productsApi, categoriesApi } from '../services/api';
import { useCart } from '../hooks/useCart';

import { SearchBar } from '../components/SearchBar';
import { CategoryBar } from '../components/CategoryBar';
import { ProductGrid } from '../components/ProductGrid';
import { CartPanel } from '../components/CartPanel';

export const POSScreen: React.FC = () => {
  // State
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  // Cart
  const { items, total, addItem, removeItem, updateQuantity, clear } = useCart();

  // Load categories
  useEffect(() => {
    categoriesApi.list().then(setCategories).catch(console.error);
  }, []);

  // Load products - removed `loading` from deps to prevent infinite loop
  const loadProducts = useCallback(
    async (pageNum = 1, append = false) => {
      setLoading(true);
      try {
        const res = await productsApi.list({
          page: pageNum,
          page_size: 30,
          category_id: selectedCategory || undefined,
          search: searchText || undefined,
        });

        if (append) {
          setProducts((prev) => [...prev, ...res.items]);
        } else {
          setProducts(res.items);
        }
        setHasMore(res.items.length === 30);
        setPage(pageNum);
      } catch (err) {
        console.error('Failed to load products:', err);
      } finally {
        setLoading(false);
      }
    },
    [selectedCategory, searchText],
  );

  // Reload when filters change
  useEffect(() => {
    loadProducts(1, false);
  }, [loadProducts]);

  // Pagination - use ref to prevent race condition with loading state
  const loadingRef = React.useRef(false);
  React.useEffect(() => { loadingRef.current = loading; }, [loading]);

  const loadMore = () => {
    if (hasMore && !loadingRef.current) {
      loadProducts(page + 1, true);
    }
  };

  // Add to cart
  const handleProductPress = (product: Product) => {
    addItem(product);
  };

  // Barcode scan (placeholder - sẽ tích hợp camera sau)
  const handleBarcodeScan = async () => {
    // TODO: Tích hợp react-native-camera / expo-barcode-scanner
    Alert.alert('Quét barcode', 'Tính năng quét barcode sẽ tích hợp camera AI');
  };

  // Checkout
  const handleCheckout = () => {
    Alert.alert(
      'Xác nhận thanh toán',
      `Tổng: ${total.toLocaleString('vi-VN')}₫\nSố sản phẩm: ${items.length}`,
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Thanh toán',
          onPress: () => {
            // TODO: Tạo order, giảm tồn kho, in hóa đơn
            Alert.alert('Thành công!', 'Đơn hàng đã được tạo');
            clear();
          },
        },
      ],
    );
  };

  return (
    <View style={styles.container}>
      {/* Left side - Products (65%) */}
      <View style={styles.productSide}>
        <SearchBar
          value={searchText}
          onChangeText={setSearchText}
          onBarcodeScan={handleBarcodeScan}
        />

        <CategoryBar
          categories={categories}
          selectedId={selectedCategory}
          onSelect={setSelectedCategory}
        />

        {loading && products.length === 0 ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#2563EB" />
          </View>
        ) : (
          <ProductGrid
            products={products}
            onProductPress={handleProductPress}
            onEndReached={loadMore}
            loading={loading}
          />
        )}
      </View>

      {/* Right side - Cart (35%) */}
      <View style={styles.cartSide}>
        <CartPanel
          items={items}
          total={total}
          onUpdateQty={updateQuantity}
          onRemove={removeItem}
          onClear={clear}
          onCheckout={handleCheckout}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#F9FAFB',
  },
  productSide: {
    flex: 0.65,
  },
  cartSide: {
    flex: 0.35,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
