import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, TextInput, FlatList, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator, RefreshControl,
} from 'react-native';
import { api } from '../services/api';

interface Customer {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  loyalty_points: number;
  address: string | null;
}

interface CreateCustomerForm {
  name: string;
  phone: string;
  email: string;
  address: string;
}

const EMPTY_FORM: CreateCustomerForm = { name: '', phone: '', email: '', address: '' };

export default function CustomerScreen() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateCustomerForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchCustomers = useCallback(async (searchTerm = '', pageNum = 1) => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(pageNum), size: '20' };
      if (searchTerm.trim()) params.search = searchTerm.trim();

      const response = await api.get('/customers', { params });
      if (pageNum === 1) {
        setCustomers(response.data.items);
      } else {
        setCustomers(prev => [...prev, ...response.data.items]);
      }
      setTotal(response.data.total);
    } catch (error: any) {
      Alert.alert('Lỗi', error?.response?.data?.detail || 'Không thể tải danh sách khách hàng');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      fetchCustomers(search, 1);
    }, 400);
    return () => clearTimeout(timer);
  }, [search]);

  const handleRefresh = () => {
    setRefreshing(true);
    setPage(1);
    fetchCustomers(search, 1);
  };

  const handleLoadMore = () => {
    if (customers.length < total && !loading) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchCustomers(search, nextPage);
    }
  };

  const handleCreate = async () => {
    if (!form.name.trim()) {
      Alert.alert('Lỗi', 'Tên khách hàng không được để trống');
      return;
    }
    try {
      setSaving(true);
      const payload: Record<string, string> = { name: form.name.trim() };
      if (form.phone.trim()) payload.phone = form.phone.trim();
      if (form.email.trim()) payload.email = form.email.trim();
      if (form.address.trim()) payload.address = form.address.trim();

      await api.post('/customers', payload);
      Alert.alert('Thành công', `Đã thêm khách hàng: ${form.name}`);
      setForm(EMPTY_FORM);
      setShowCreate(false);
      fetchCustomers(search, 1);
    } catch (error: any) {
      Alert.alert('Lỗi', error?.response?.data?.detail || 'Không thể thêm khách hàng');
    } finally {
      setSaving(false);
    }
  };

  const handleAddPoints = async (customer: Customer) => {
    Alert.prompt(
      'Thêm điểm tích lũy',
      `Khách: ${customer.name} - Hiện có: ${customer.loyalty_points} điểm\nNhập số điểm muốn thêm:`,
      async (value) => {
        const points = parseInt(value || '0', 10);
        if (isNaN(points) || points <= 0) return;
        try {
          await api.post(`/customers/${customer.id}/loyalty-points`, {
            points_change: points,
            reason: 'Tích điểm từ POS',
          });
          fetchCustomers(search, 1);
        } catch (error: any) {
          Alert.alert('Lỗi', error?.response?.data?.detail || 'Không thể cập nhật điểm');
        }
      },
      'plain-text',
    );
  };

  const renderCustomer = ({ item }: { item: Customer }) => (
    <View style={styles.customerCard}>
      <View style={styles.customerInfo}>
        <Text style={styles.customerName}>{item.name}</Text>
        {item.phone ? <Text style={styles.customerDetail}>📱 {item.phone}</Text> : null}
        {item.email ? <Text style={styles.customerDetail}>✉️ {item.email}</Text> : null}
        <View style={styles.pointsBadge}>
          <Text style={styles.pointsText}>⭐ {item.loyalty_points} điểm</Text>
        </View>
      </View>
      <TouchableOpacity
        style={styles.addPointsBtn}
        onPress={() => handleAddPoints(item)}
      >
        <Text style={styles.addPointsBtnText}>+Điểm</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Khách hàng ({total})</Text>
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => setShowCreate(!showCreate)}
        >
          <Text style={styles.addBtnText}>{showCreate ? '✕ Đóng' : '+ Thêm'}</Text>
        </TouchableOpacity>
      </View>

      {/* Search */}
      <TextInput
        style={styles.searchInput}
        placeholder="🔍 Tìm theo tên, SĐT, email..."
        value={search}
        onChangeText={setSearch}
        clearButtonMode="while-editing"
      />

      {/* Create Form */}
      {showCreate && (
        <View style={styles.createForm}>
          <Text style={styles.formTitle}>Thêm khách hàng mới</Text>
          <TextInput
            style={styles.input}
            placeholder="Tên khách hàng *"
            value={form.name}
            onChangeText={v => setForm(f => ({ ...f, name: v }))}
          />
          <TextInput
            style={styles.input}
            placeholder="Số điện thoại"
            value={form.phone}
            onChangeText={v => setForm(f => ({ ...f, phone: v }))}
            keyboardType="phone-pad"
          />
          <TextInput
            style={styles.input}
            placeholder="Email"
            value={form.email}
            onChangeText={v => setForm(f => ({ ...f, email: v }))}
            keyboardType="email-address"
            autoCapitalize="none"
          />
          <TextInput
            style={styles.input}
            placeholder="Địa chỉ"
            value={form.address}
            onChangeText={v => setForm(f => ({ ...f, address: v }))}
          />
          <TouchableOpacity
            style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
            onPress={handleCreate}
            disabled={saving}
          >
            {saving
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.saveBtnText}>Lưu khách hàng</Text>
            }
          </TouchableOpacity>
        </View>
      )}

      {/* List */}
      <FlatList
        data={customers}
        keyExtractor={item => item.id}
        renderItem={renderCustomer}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />}
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.3}
        ListEmptyComponent={
          !loading ? (
            <Text style={styles.emptyText}>
              {search ? 'Không tìm thấy khách hàng' : 'Chưa có khách hàng nào'}
            </Text>
          ) : null
        }
        ListFooterComponent={
          loading && customers.length > 0 ? <ActivityIndicator style={{ margin: 16 }} /> : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#eee',
  },
  title: { fontSize: 18, fontWeight: 'bold', color: '#1a1a1a' },
  addBtn: { backgroundColor: '#4CAF50', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
  addBtnText: { color: '#fff', fontWeight: '600' },
  searchInput: {
    margin: 12, padding: 12, backgroundColor: '#fff',
    borderRadius: 10, borderWidth: 1, borderColor: '#ddd', fontSize: 15,
  },
  createForm: {
    margin: 12, padding: 16, backgroundColor: '#fff',
    borderRadius: 12, borderWidth: 1, borderColor: '#4CAF50',
  },
  formTitle: { fontSize: 16, fontWeight: '600', marginBottom: 12, color: '#1a1a1a' },
  input: {
    borderWidth: 1, borderColor: '#ddd', borderRadius: 8,
    padding: 10, marginBottom: 10, fontSize: 15,
  },
  saveBtn: {
    backgroundColor: '#4CAF50', padding: 14, borderRadius: 8,
    alignItems: 'center', marginTop: 4,
  },
  saveBtnDisabled: { opacity: 0.7 },
  saveBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  customerCard: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    marginHorizontal: 12, marginVertical: 5, padding: 14,
    borderRadius: 10, elevation: 1, shadowColor: '#000', shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  customerInfo: { flex: 1 },
  customerName: { fontSize: 16, fontWeight: '600', color: '#1a1a1a', marginBottom: 3 },
  customerDetail: { fontSize: 13, color: '#666', marginBottom: 2 },
  pointsBadge: {
    marginTop: 4, backgroundColor: '#FFF9C4', paddingHorizontal: 8,
    paddingVertical: 3, borderRadius: 12, alignSelf: 'flex-start',
  },
  pointsText: { fontSize: 12, color: '#F57F17', fontWeight: '600' },
  addPointsBtn: {
    backgroundColor: '#E8F5E9', padding: 10, borderRadius: 8,
    borderWidth: 1, borderColor: '#4CAF50',
  },
  addPointsBtnText: { color: '#4CAF50', fontWeight: '600', fontSize: 13 },
  emptyText: { textAlign: 'center', color: '#999', marginTop: 40, fontSize: 15 },
});
