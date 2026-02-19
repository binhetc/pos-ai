/**
 * Main App Component - Navigation & Auth Flow
 */

import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LoginScreen } from './screens/LoginScreen';
import { POSScreen } from './screens/POSScreen';
import { ProductsScreen } from './screens/ProductsScreen';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [currentScreen, setCurrentScreen] = useState<'pos' | 'products'>('pos');

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      setIsAuthenticated(!!token);
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  // Simple screen switcher (in production, use React Navigation)
  return (
    <View style={styles.container}>
      {currentScreen === 'pos' ? <POSScreen /> : <ProductsScreen />}
      
      {/* Simple tab bar */}
      <View style={styles.tabBar}>
        <View
          style={[styles.tab, currentScreen === 'pos' && styles.activeTab]}
          onTouchEnd={() => setCurrentScreen('pos')}
        >
          <View style={styles.tabContent}>POS</View>
        </View>
        <View
          style={[styles.tab, currentScreen === 'products' && styles.activeTab]}
          onTouchEnd={() => setCurrentScreen('products')}
        >
          <View style={styles.tabContent}>Products</View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderColor: '#e0e0e0',
    height: 60,
  },
  tab: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  activeTab: {
    borderTopWidth: 3,
    borderColor: '#007AFF',
  },
  tabContent: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
});
