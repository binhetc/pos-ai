/**
 * ProductGrid - Grid hiển thị sản phẩm cho màn hình POS
 * Tap để thêm vào giỏ hàng, hiển thị giá + tồn kho
 */

import React from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  Image,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { Product } from '../types';

const SCREEN_WIDTH = Dimensions.get('window').width;
const NUM_COLUMNS = 3;
const CARD_MARGIN = 6;
const CARD_WIDTH = (SCREEN_WIDTH * 0.65 - CARD_MARGIN * (NUM_COLUMNS + 1)) / NUM_COLUMNS;

interface Props {
  products: Product[];
  onProductPress: (product: Product) => void;
  onEndReached?: () => void;
  loading?: boolean;
}

const formatVND = (n: number) =>
  n.toLocaleString('vi-VN', { style: 'currency', currency: 'VND' });

export const ProductGrid: React.FC<Props> = ({ products, onProductPress, onEndReached, loading }) => {
  const renderItem = ({ item }: { item: Product }) => {
    const lowStock = item.in_stock <= item.min_stock && item.in_stock > 0;
    const outOfStock = item.in_stock === 0;

    return (
      <TouchableOpacity
        style={[styles.card, outOfStock && styles.cardDisabled]}
        onPress={() => !outOfStock && onProductPress(item)}
        disabled={outOfStock}
        activeOpacity={0.7}
      >
        {/* Product Image */}
        <View style={styles.imageContainer}>
          {item.image_url ? (
            <Image source={{ uri: item.image_url }} style={styles.image} />
          ) : (
            <View style={styles.imagePlaceholder}>
              <Text style={styles.placeholderEmoji}>📦</Text>
            </View>
          )}
          {/* Stock badge */}
          {lowStock && (
            <View style={styles.badgeWarning}>
              <Text style={styles.badgeText}>⚠️ {item.in_stock}</Text>
            </View>
          )}
          {outOfStock && (
            <View style={styles.badgeOut}>
              <Text style={styles.badgeText}>Hết hàng</Text>
            </View>
          )}
        </View>

        {/* Info */}
        <Text style={styles.name} numberOfLines={2}>{item.name}</Text>
        <Text style={styles.price}>{formatVND(item.price)}</Text>
        <Text style={styles.sku}>{item.sku}</Text>
      </TouchableOpacity>
    );
  };

  return (
    <FlatList
      data={products}
      renderItem={renderItem}
      keyExtractor={(item) => item.id}
      numColumns={NUM_COLUMNS}
      contentContainerStyle={styles.grid}
      onEndReached={onEndReached}
      onEndReachedThreshold={0.3}
      showsVerticalScrollIndicator={false}
    />
  );
};

const styles = StyleSheet.create({
  grid: {
    padding: CARD_MARGIN,
  },
  card: {
    width: CARD_WIDTH,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    margin: CARD_MARGIN,
    padding: 8,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
  },
  cardDisabled: {
    opacity: 0.5,
  },
  imageContainer: {
    width: '100%',
    aspectRatio: 1,
    borderRadius: 8,
    overflow: 'hidden',
    marginBottom: 6,
    position: 'relative',
  },
  image: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  imagePlaceholder: {
    width: '100%',
    height: '100%',
    backgroundColor: '#F3F4F6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderEmoji: {
    fontSize: 32,
  },
  badgeWarning: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: '#FCD34D',
    borderRadius: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  badgeOut: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  name: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 2,
  },
  price: {
    fontSize: 14,
    fontWeight: '700',
    color: '#2563EB',
  },
  sku: {
    fontSize: 10,
    color: '#9CA3AF',
    marginTop: 2,
  },
});
