/**
 * POS Screen - Main point of sale interface
 * Product grid + Cart + Checkout + Barcode Scanner
 *
 * Barcode scanner flow:
 *   Cashier taps "Scan" → camera opens → quét barcode → lookup product →
 *   nếu tìm thấy → addToCart → camera tự đóng
 *   nếu không → Alert "Không tìm thấy sản phẩm"
 *
 * Fallback: Nếu camera permission bị từ chối → hiển thị text input nhập
 * barcode thủ công.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  Modal,
  Platform,
} from 'react-native';
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
} from 'react-native-vision-camera';
import { useCodeScanner } from 'vision-camera-code-scanner';
import { api } from '../services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Product {
  id: string;
  name: string;
  sku: string;
  barcode?: string;
  price: number;
  image_url?: string;
  category_id: string;
}

interface CartItem {
  product: Product;
  quantity: number;
}

// ─── BarcodeScanner component ─────────────────────────────────────────────────

interface BarcodeScannerProps {
  visible: boolean;
  onCodeScanned: (code: string) => void;
  onClose: () => void;
}

/**
 * Camera-based barcode scanner overlay.
 * Renders a fullscreen camera with a crosshair overlay.
 * After a successful scan, calls onCodeScanned once then deactivates itself.
 */
const BarcodeScanner: React.FC<BarcodeScannerProps> = ({
  visible,
  onCodeScanned,
  onClose,
}) => {
  const device = useCameraDevice('back');
  // Prevent multiple rapid scans from firing
  const scannedRef = useRef(false);

  // Reset on each open
  useEffect(() => {
    if (visible) {
      scannedRef.current = false;
    }
  }, [visible]);

  const codeScanner = useCodeScanner({
    codeTypes: [
      'ean-13',
      'ean-8',
      'upc-a',
      'upc-e',
      'code-128',
      'code-39',
      'code-93',
      'qr',
    ],
    onCodeScanned: (codes) => {
      if (scannedRef.current) return;
      const code = codes[0]?.value;
      if (code) {
        scannedRef.current = true;
        onCodeScanned(code);
      }
    },
  });

  if (!device) {
    return (
      <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
        <View style={scannerStyles.container}>
          <Text style={scannerStyles.errorText}>
            Không tìm thấy camera. Vui lòng sử dụng nhập barcode thủ công.
          </Text>
          <TouchableOpacity style={scannerStyles.closeButton} onPress={onClose}>
            <Text style={scannerStyles.closeButtonText}>Đóng</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    );
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      statusBarTranslucent
      onRequestClose={onClose}
    >
      <View style={scannerStyles.container}>
        <Camera
          style={StyleSheet.absoluteFill}
          device={device}
          isActive={visible}
          codeScanner={codeScanner}
        />

        {/* Overlay UI */}
        <View style={scannerStyles.overlay}>
          {/* Dimmed top */}
          <View style={scannerStyles.dimArea} />

          {/* Middle row: dim | viewfinder | dim */}
          <View style={scannerStyles.middleRow}>
            <View style={scannerStyles.dimArea} />
            <View style={scannerStyles.viewfinder}>
              {/* Corner brackets */}
              <View style={[scannerStyles.corner, scannerStyles.topLeft]} />
              <View style={[scannerStyles.corner, scannerStyles.topRight]} />
              <View style={[scannerStyles.corner, scannerStyles.bottomLeft]} />
              <View style={[scannerStyles.corner, scannerStyles.bottomRight]} />
            </View>
            <View style={scannerStyles.dimArea} />
          </View>

          {/* Dimmed bottom */}
          <View style={scannerStyles.dimArea} />
        </View>

        {/* Instruction & close button */}
        <View style={scannerStyles.footer}>
          <Text style={scannerStyles.instructionText}>
            Đưa barcode vào khung để quét
          </Text>
          <TouchableOpacity style={scannerStyles.closeButton} onPress={onClose}>
            <Text style={scannerStyles.closeButtonText}>✕ Đóng</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

// ─── ManualBarcodeInput component ─────────────────────────────────────────────

interface ManualBarcodeInputProps {
  visible: boolean;
  onSubmit: (code: string) => void;
  onClose: () => void;
}

/**
 * Fallback manual barcode input modal (shown when camera permission denied).
 */
const ManualBarcodeInput: React.FC<ManualBarcodeInputProps> = ({
  visible,
  onSubmit,
  onClose,
}) => {
  const [value, setValue] = useState('');

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setValue('');
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={manualStyles.backdrop}>
        <View style={manualStyles.card}>
          <Text style={manualStyles.title}>Nhập barcode thủ công</Text>
          <TextInput
            style={manualStyles.input}
            value={value}
            onChangeText={setValue}
            placeholder="Nhập barcode hoặc SKU..."
            autoFocus
            onSubmitEditing={handleSubmit}
            returnKeyType="search"
          />
          <View style={manualStyles.actions}>
            <TouchableOpacity style={manualStyles.cancelBtn} onPress={onClose}>
              <Text style={manualStyles.cancelText}>Huỷ</Text>
            </TouchableOpacity>
            <TouchableOpacity style={manualStyles.submitBtn} onPress={handleSubmit}>
              <Text style={manualStyles.submitText}>Tìm</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

// ─── POSScreen ────────────────────────────────────────────────────────────────

export const POSScreen: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  // Scanner state
  const [scannerVisible, setScannerVisible] = useState(false);
  const [manualInputVisible, setManualInputVisible] = useState(false);
  const [scannerLoading, setScannerLoading] = useState(false);

  const { hasPermission, requestPermission } = useCameraPermission();

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

  // ── Cart helpers ──────────────────────────────────────────────────────────

  const addToCart = useCallback((product: Product) => {
    setCart((prev) => {
      const existing = prev.find((item) => item.product.id === product.id);
      if (existing) {
        return prev.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { product, quantity: 1 }];
    });
  }, []);

  const updateQuantity = (productId: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((item) =>
          item.product.id === productId
            ? { ...item, quantity: item.quantity + delta }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const getTotal = () =>
    cart.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  const handleCheckout = () => {
    if (cart.length === 0) {
      Alert.alert('Giỏ hàng trống', 'Vui lòng thêm sản phẩm vào giỏ');
      return;
    }

    Alert.alert(
      'Thanh toán',
      `Tổng tiền: ${getTotal().toLocaleString('vi-VN')} ₫`,
      [
        { text: 'Huỷ', style: 'cancel' },
        {
          text: 'Xác nhận',
          onPress: () => {
            // TODO: Create order via API
            Alert.alert('Thành công', 'Đơn hàng đã được tạo!');
            setCart([]);
          },
        },
      ]
    );
  };

  // ── Barcode scanner handlers ──────────────────────────────────────────────

  /**
   * Xử lý khi người dùng nhấn nút Scan.
   * Kiểm tra permission → mở camera scanner hoặc fallback manual input.
   */
  const handleScanPress = async () => {
    if (hasPermission) {
      setScannerVisible(true);
      return;
    }

    const granted = await requestPermission();
    if (granted) {
      setScannerVisible(true);
    } else {
      // Permission denied → show manual input fallback
      Alert.alert(
        'Không có quyền camera',
        'Ứng dụng không có quyền truy cập camera. Bạn có muốn nhập barcode thủ công không?',
        [
          { text: 'Huỷ', style: 'cancel' },
          { text: 'Nhập thủ công', onPress: () => setManualInputVisible(true) },
        ]
      );
    }
  };

  /**
   * Callback khi quét được barcode (từ camera hoặc manual input).
   * Lookup product → addToCart hoặc hiển thị thông báo không tìm thấy.
   */
  const handleCodeScanned = useCallback(
    async (code: string) => {
      // Close scanner / manual input first
      setScannerVisible(false);
      setManualInputVisible(false);
      setScannerLoading(true);

      try {
        const product = await api.getProductByBarcode(code);

        if (product) {
          addToCart(product);
          // Brief confirmation toast — shown via Alert for simplicity
          Alert.alert(
            '✅ Đã thêm vào giỏ',
            `${product.name}\n${product.price.toLocaleString('vi-VN')} ₫`,
            [{ text: 'OK' }],
            { cancelable: true }
          );
        } else {
          // Barcode not matched → try SKU lookup as fallback
          const bysku = await api.getProductBySku(code);
          if (bysku) {
            addToCart(bysku);
            Alert.alert(
              '✅ Đã thêm vào giỏ',
              `${bysku.name}\n${bysku.price.toLocaleString('vi-VN')} ₫`,
              [{ text: 'OK' }],
              { cancelable: true }
            );
          } else {
            Alert.alert(
              'Không tìm thấy sản phẩm',
              `Barcode: ${code}\nKhông có sản phẩm nào khớp trong hệ thống.`,
              [
                { text: 'Nhập thủ công', onPress: () => setManualInputVisible(true) },
                { text: 'Đóng', style: 'cancel' },
              ]
            );
          }
        }
      } catch (error: any) {
        Alert.alert('Lỗi', `Không thể tra cứu sản phẩm: ${error.message}`);
      } finally {
        setScannerLoading(false);
      }
    },
    [addToCart]
  );

  // ── Render ────────────────────────────────────────────────────────────────

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
      {/* Camera Barcode Scanner */}
      <BarcodeScanner
        visible={scannerVisible}
        onCodeScanned={handleCodeScanned}
        onClose={() => setScannerVisible(false)}
      />

      {/* Manual Barcode Input (fallback) */}
      <ManualBarcodeInput
        visible={manualInputVisible}
        onSubmit={handleCodeScanned}
        onClose={() => setManualInputVisible(false)}
      />

      {/* Left: Product Grid */}
      <View style={styles.productsPanel}>
        {/* Search row + Scan button */}
        <View style={styles.searchRow}>
          <TextInput
            style={styles.searchInput}
            placeholder="Tìm kiếm sản phẩm..."
            value={search}
            onChangeText={setSearch}
          />
          <TouchableOpacity
            style={[styles.scanButton, scannerLoading && styles.scanButtonDisabled]}
            onPress={handleScanPress}
            disabled={scannerLoading}
            accessibilityLabel="Quét barcode"
          >
            {scannerLoading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.scanButtonText}>📷 Scan</Text>
            )}
          </TouchableOpacity>
        </View>

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
        <Text style={styles.cartTitle}>Giỏ hàng</Text>

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
            <Text style={styles.totalLabel}>Tổng:</Text>
            <Text style={styles.totalAmount}>
              {getTotal().toLocaleString('vi-VN')} ₫
            </Text>
          </View>

          <TouchableOpacity
            style={[
              styles.checkoutButton,
              cart.length === 0 && styles.checkoutButtonDisabled,
            ]}
            onPress={handleCheckout}
            disabled={cart.length === 0}
          >
            <Text style={styles.checkoutButtonText}>Thanh toán</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

// ─── Styles ───────────────────────────────────────────────────────────────────

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
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    height: 50,
    backgroundColor: '#fff',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  scanButton: {
    height: 50,
    paddingHorizontal: 16,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    minWidth: 90,
  },
  scanButtonDisabled: {
    backgroundColor: '#999',
  },
  scanButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
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

// ─── Scanner styles ───────────────────────────────────────────────────────────

const VIEWFINDER_SIZE = 260;
const CORNER_LENGTH = 32;
const CORNER_THICKNESS = 4;

const scannerStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    flexDirection: 'column',
  },
  dimArea: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  middleRow: {
    flexDirection: 'row',
    height: VIEWFINDER_SIZE,
  },
  viewfinder: {
    width: VIEWFINDER_SIZE,
    height: VIEWFINDER_SIZE,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: CORNER_LENGTH,
    height: CORNER_LENGTH,
    borderColor: '#fff',
  },
  topLeft: {
    top: 0,
    left: 0,
    borderTopWidth: CORNER_THICKNESS,
    borderLeftWidth: CORNER_THICKNESS,
    borderTopLeftRadius: 4,
  },
  topRight: {
    top: 0,
    right: 0,
    borderTopWidth: CORNER_THICKNESS,
    borderRightWidth: CORNER_THICKNESS,
    borderTopRightRadius: 4,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: CORNER_THICKNESS,
    borderLeftWidth: CORNER_THICKNESS,
    borderBottomLeftRadius: 4,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: CORNER_THICKNESS,
    borderRightWidth: CORNER_THICKNESS,
    borderBottomRightRadius: 4,
  },
  footer: {
    position: 'absolute',
    bottom: 48,
    left: 0,
    right: 0,
    alignItems: 'center',
    gap: 16,
  },
  instructionText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    paddingHorizontal: 24,
  },
  closeButton: {
    paddingHorizontal: 32,
    paddingVertical: 12,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.5)',
  },
  closeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  errorText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    padding: 32,
  },
});

// ─── Manual input styles ──────────────────────────────────────────────────────

const manualStyles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '80%',
    maxWidth: 400,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    textAlign: 'center',
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    marginBottom: 16,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelBtn: {
    flex: 1,
    height: 48,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelText: {
    fontSize: 16,
    color: '#666',
  },
  submitBtn: {
    flex: 1,
    height: 48,
    borderRadius: 8,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  submitText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
  },
});
