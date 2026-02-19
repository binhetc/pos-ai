/**
 * POS Screen - Main point of sale interface
 * Product grid + Cart + Checkout
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { api } from '../services/api';

interface Product {
  id: string;
  name: string;
  sku: string;
  price: number;
  image_url?: string;
  category_id: string;
}

interface CartItem {
  product: Product;
  quantity: number;
}

export const POSScreen: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const response = await api.getProducts({ size: 100 });
      setProducts(response.items);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const addToCart = (product: Product) => {
    const existingItem = cart.find((item) => item.product.id === product.id);
    if (existingItem) {
      setCart(
        cart.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      );
    } else {
      setCart([...cart, { product, quantity: 1 }]);
    }
  };

  const updateQuantity = (productId: string, delta: number) => {
    setCart(
      cart
        .map((item) =>
          item.product.id === productId
            ? { ...item, quantity: item.quantity + delta }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const getTotal = () => {
    return cart.reduce(
      (sum, item) => sum + item.product.price * item.quantity,
      0
    );
  };

  const handleCheckout = () => {
    if (cart.length === 0) {
      Alert.alert('Empty Cart', 'Please add items to cart');
      return;
    }

    Alert.alert(
      'Checkout',
      `Total: ${getTotal().toLocaleString('vi-VN')} ₫`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Confirm',
          onPress: () => {
            // TODO: Create order via API
            Alert.alert('Success', 'Order completed!');
            setCart([]);
          },
        },
      ]
    );
  };

  const filteredProducts = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.sku.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Left: Product Grid */}
      <View style={styles.productsPanel}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search products..."
          value={search}
          onChangeText={setSearch}
        />

        <FlatList
          data={filteredProducts}
          keyExtractor={(item) => item.id}
          numColumns={3}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.productCard}
              onPress={() => addToCart(item)}
            >
              <Text style={styles.productName} numberOfLines={2}>
                {item.name}
              </Text>
              <Text style={styles.productPrice}>
                {item.price.toLocaleString('vi-VN')} ₫
              </Text>
            </TouchableOpacity>
          )}
          contentContainerStyle={styles.productGrid}
        />
      </View>

      {/* Right: Cart */}
      <View style={styles.cartPanel}>
        <Text style={styles.cartTitle}>Cart</Text>

        <FlatList
          data={cart}
          keyExtractor={(item) => item.product.id}
          renderItem={({ item }) => (
            <View style={styles.cartItem}>
              <View style={styles.cartItemInfo}>
                <Text style={styles.cartItemName}>{item.product.name}</Text>
                <Text style={styles.cartItemPrice}>
                  {item.product.price.toLocaleString('vi-VN')} ₫
                </Text>
              </View>

              <View style={styles.quantityControls}>
                <TouchableOpacity
                  style={styles.quantityButton}
                  onPress={() => updateQuantity(item.product.id, -1)}
                >
                  <Text style={styles.quantityButtonText}>-</Text>
                </TouchableOpacity>

                <Text style={styles.quantity}>{item.quantity}</Text>

                <TouchableOpacity
                  style={styles.quantityButton}
                  onPress={() => updateQuantity(item.product.id, 1)}
                >
                  <Text style={styles.quantityButtonText}>+</Text>
                </TouchableOpacity>
              </View>

              <Text style={styles.cartItemTotal}>
                {(item.product.price * item.quantity).toLocaleString('vi-VN')} ₫
              </Text>
            </View>
          )}
          style={styles.cartList}
        />

        <View style={styles.cartFooter}>
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Total:</Text>
            <Text style={styles.totalAmount}>
              {getTotal().toLocaleString('vi-VN')} ₫
            </Text>
          </View>

          <TouchableOpacity
            style={[styles.checkoutButton, cart.length === 0 && styles.checkoutButtonDisabled]}
            onPress={handleCheckout}
            disabled={cart.length === 0}
          >
            <Text style={styles.checkoutButtonText}>Checkout</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  productsPanel: {
    flex: 2,
    padding: 16,
  },
  searchInput: {
    height: 50,
    backgroundColor: '#fff',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  productGrid: {
    paddingBottom: 16,
  },
  productCard: {
    flex: 1,
    margin: 8,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
    minHeight: 100,
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  productName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  productPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  cartPanel: {
    flex: 1,
    backgroundColor: '#fff',
    borderLeftWidth: 1,
    borderColor: '#e0e0e0',
    padding: 16,
  },
  cartTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  cartList: {
    flex: 1,
  },
  cartItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderColor: '#f0f0f0',
  },
  cartItemInfo: {
    flex: 1,
  },
  cartItemName: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  cartItemPrice: {
    fontSize: 12,
    color: '#666',
  },
  quantityControls: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 12,
  },
  quantityButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  quantityButtonText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  quantity: {
    fontSize: 16,
    fontWeight: '600',
    marginHorizontal: 12,
    minWidth: 30,
    textAlign: 'center',
  },
  cartItemTotal: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#007AFF',
    minWidth: 80,
    textAlign: 'right',
  },
  cartFooter: {
    borderTopWidth: 2,
    borderColor: '#e0e0e0',
    paddingTop: 16,
    marginTop: 16,
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  totalLabel: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  totalAmount: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  checkoutButton: {
    height: 56,
    backgroundColor: '#34C759',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkoutButtonDisabled: {
    backgroundColor: '#ccc',
  },
  checkoutButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
