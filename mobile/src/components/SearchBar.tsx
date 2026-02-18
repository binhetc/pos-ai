/**
 * SearchBar - Thanh tìm kiếm + quét barcode
 */

import React from 'react';
import { View, TextInput, TouchableOpacity, Text, StyleSheet } from 'react-native';

interface Props {
  value: string;
  onChangeText: (text: string) => void;
  onBarcodeScan?: () => void;
}

export const SearchBar: React.FC<Props> = ({ value, onChangeText, onBarcodeScan }) => {
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>🔍</Text>
      <TextInput
        style={styles.input}
        placeholder="Tìm sản phẩm, SKU, barcode..."
        placeholderTextColor="#9CA3AF"
        value={value}
        onChangeText={onChangeText}
        autoCapitalize="none"
        returnKeyType="search"
      />
      {onBarcodeScan && (
        <TouchableOpacity style={styles.scanBtn} onPress={onBarcodeScan}>
          <Text style={styles.scanIcon}>📷</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    marginHorizontal: 12,
    marginVertical: 8,
    paddingHorizontal: 12,
    height: 44,
  },
  icon: {
    fontSize: 16,
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: '#1F2937',
  },
  scanBtn: {
    padding: 4,
    marginLeft: 8,
  },
  scanIcon: {
    fontSize: 20,
  },
});
