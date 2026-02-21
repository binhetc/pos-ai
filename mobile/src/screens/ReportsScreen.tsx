import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert,
} from 'react-native';
import { api } from '../services/api';

type ReportTab = 'daily' | 'top_products' | 'payment';

interface DailySalesItem {
  date: string;
  total_orders: number;
  total_revenue: number;
  avg_order_value: number;
}

interface DailySalesReport {
  items: DailySalesItem[];
  total_revenue: number;
  total_orders: number;
  period_start: string;
  period_end: string;
}

interface TopProduct {
  product_name: string;
  sku: string;
  total_quantity: number;
  total_revenue: number;
}

interface PaymentMethodStat {
  payment_method: string;
  total_orders: number;
  total_revenue: number;
  percentage: number;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND',
    maximumFractionDigits: 0,
  }).format(amount);
}

function getDateRange(days: number): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - days + 1);
  const fmt = (d: Date) => d.toISOString().split('T')[0];
  return { start: fmt(start), end: fmt(end) };
}

export default function ReportsScreen() {
  const [activeTab, setActiveTab] = useState<ReportTab>('daily');
  const [period, setPeriod] = useState<7 | 30>(7); // days
  const [loading, setLoading] = useState(false);

  const [dailyReport, setDailyReport] = useState<DailySalesReport | null>(null);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [paymentStats, setPaymentStats] = useState<PaymentMethodStat[]>([]);

  const fetchReport = async () => {
    const { start, end } = getDateRange(period);
    setLoading(true);
    try {
      if (activeTab === 'daily') {
        const res = await api.get('/reports/daily-sales', {
          params: { start_date: start, end_date: end },
        });
        setDailyReport(res.data);
      } else if (activeTab === 'top_products') {
        const res = await api.get('/reports/top-products', {
          params: { start_date: start, end_date: end, limit: 10 },
        });
        setTopProducts(res.data.items);
      } else if (activeTab === 'payment') {
        const res = await api.get('/reports/payment-methods', {
          params: { start_date: start, end_date: end },
        });
        setPaymentStats(res.data.items);
      }
    } catch (error: any) {
      Alert.alert('Lỗi', error?.response?.data?.detail || 'Không thể tải báo cáo');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchReport(); }, [activeTab, period]);

  const PAYMENT_LABELS: Record<string, string> = {
    cash: '💵 Tiền mặt',
    card: '💳 Thẻ',
    transfer: '🏦 Chuyển khoản',
    momo: '📱 MoMo',
    vnpay: '📱 VNPay',
  };

  return (
    <View style={styles.container}>
      {/* Tab Bar */}
      <View style={styles.tabBar}>
        {(['daily', 'top_products', 'payment'] as ReportTab[]).map(tab => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
              {tab === 'daily' ? 'Doanh thu' : tab === 'top_products' ? 'Top SP' : 'TT Toán'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Period Selector */}
      <View style={styles.periodBar}>
        <Text style={styles.periodLabel}>Thời gian:</Text>
        {([7, 30] as const).map(d => (
          <TouchableOpacity
            key={d}
            style={[styles.periodBtn, period === d && styles.periodBtnActive]}
            onPress={() => setPeriod(d)}
          >
            <Text style={[styles.periodBtnText, period === d && styles.periodBtnTextActive]}>
              {d === 7 ? '7 ngày' : '30 ngày'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#2196F3" style={{ marginTop: 60 }} />
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16 }}>

          {/* Daily Sales */}
          {activeTab === 'daily' && dailyReport && (
            <View>
              {/* Summary Cards */}
              <View style={styles.summaryRow}>
                <View style={[styles.summaryCard, { backgroundColor: '#E3F2FD' }]}>
                  <Text style={styles.summaryLabel}>Tổng doanh thu</Text>
                  <Text style={[styles.summaryValue, { color: '#1976D2' }]}>
                    {formatCurrency(dailyReport.total_revenue)}
                  </Text>
                </View>
                <View style={[styles.summaryCard, { backgroundColor: '#E8F5E9' }]}>
                  <Text style={styles.summaryLabel}>Tổng đơn hàng</Text>
                  <Text style={[styles.summaryValue, { color: '#388E3C' }]}>
                    {dailyReport.total_orders}
                  </Text>
                </View>
              </View>

              {/* Daily Breakdown */}
              <Text style={styles.sectionTitle}>Chi tiết theo ngày</Text>
              {dailyReport.items.length === 0 ? (
                <Text style={styles.emptyText}>Không có dữ liệu trong kỳ này</Text>
              ) : (
                dailyReport.items.map(item => (
                  <View key={item.date} style={styles.dailyRow}>
                    <View>
                      <Text style={styles.dailyDate}>
                        {new Date(item.date).toLocaleDateString('vi-VN', {
                          weekday: 'short', day: '2-digit', month: '2-digit',
                        })}
                      </Text>
                      <Text style={styles.dailyOrders}>{item.total_orders} đơn</Text>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={styles.dailyRevenue}>{formatCurrency(item.total_revenue)}</Text>
                      <Text style={styles.dailyAvg}>TB: {formatCurrency(item.avg_order_value)}</Text>
                    </View>
                  </View>
                ))
              )}
            </View>
          )}

          {/* Top Products */}
          {activeTab === 'top_products' && (
            <View>
              <Text style={styles.sectionTitle}>Top sản phẩm bán chạy</Text>
              {topProducts.length === 0 ? (
                <Text style={styles.emptyText}>Không có dữ liệu</Text>
              ) : (
                topProducts.map((product, index) => (
                  <View key={product.sku} style={styles.productRow}>
                    <View style={styles.productRank}>
                      <Text style={styles.productRankText}>{index + 1}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.productName}>{product.product_name}</Text>
                      <Text style={styles.productSku}>SKU: {product.sku}</Text>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={styles.productQty}>{product.total_quantity} cái</Text>
                      <Text style={styles.productRevenue}>{formatCurrency(product.total_revenue)}</Text>
                    </View>
                  </View>
                ))
              )}
            </View>
          )}

          {/* Payment Methods */}
          {activeTab === 'payment' && (
            <View>
              <Text style={styles.sectionTitle}>Phương thức thanh toán</Text>
              {paymentStats.length === 0 ? (
                <Text style={styles.emptyText}>Không có dữ liệu</Text>
              ) : (
                paymentStats.map(stat => (
                  <View key={stat.payment_method} style={styles.paymentRow}>
                    <Text style={styles.paymentMethod}>
                      {PAYMENT_LABELS[stat.payment_method] || stat.payment_method}
                    </Text>
                    <View style={styles.paymentStats}>
                      <Text style={styles.paymentOrders}>{stat.total_orders} đơn</Text>
                      <Text style={styles.paymentRevenue}>{formatCurrency(stat.total_revenue)}</Text>
                      <View style={styles.progressBar}>
                        <View style={[styles.progressFill, { width: `${stat.percentage}%` }]} />
                      </View>
                      <Text style={styles.paymentPercent}>{Number(stat.percentage).toFixed(1)}%</Text>
                    </View>
                  </View>
                ))
              )}
            </View>
          )}

        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  tabBar: { flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#eee' },
  tab: { flex: 1, paddingVertical: 14, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#2196F3' },
  tabText: { fontSize: 13, color: '#999', fontWeight: '500' },
  tabTextActive: { color: '#2196F3', fontWeight: '700' },
  periodBar: { flexDirection: 'row', alignItems: 'center', padding: 12, backgroundColor: '#fff', marginBottom: 2 },
  periodLabel: { fontSize: 13, color: '#666', marginRight: 10 },
  periodBtn: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 16, borderWidth: 1, borderColor: '#ddd', marginRight: 8 },
  periodBtnActive: { backgroundColor: '#2196F3', borderColor: '#2196F3' },
  periodBtnText: { fontSize: 13, color: '#666' },
  periodBtnTextActive: { color: '#fff', fontWeight: '600' },
  summaryRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  summaryCard: { flex: 1, padding: 16, borderRadius: 12, alignItems: 'center' },
  summaryLabel: { fontSize: 12, color: '#666', marginBottom: 6 },
  summaryValue: { fontSize: 18, fontWeight: 'bold' },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#1a1a1a', marginBottom: 10 },
  emptyText: { textAlign: 'center', color: '#999', marginTop: 40 },
  dailyRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    backgroundColor: '#fff', padding: 14, borderRadius: 10, marginBottom: 8,
  },
  dailyDate: { fontSize: 14, fontWeight: '600', color: '#1a1a1a' },
  dailyOrders: { fontSize: 12, color: '#666', marginTop: 2 },
  dailyRevenue: { fontSize: 15, fontWeight: '700', color: '#2196F3' },
  dailyAvg: { fontSize: 11, color: '#999', marginTop: 2 },
  productRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#fff', padding: 14, borderRadius: 10, marginBottom: 8,
  },
  productRank: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: '#2196F3',
    alignItems: 'center', justifyContent: 'center', marginRight: 12,
  },
  productRankText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  productName: { fontSize: 14, fontWeight: '600', color: '#1a1a1a' },
  productSku: { fontSize: 11, color: '#999', marginTop: 2 },
  productQty: { fontSize: 13, fontWeight: '600', color: '#4CAF50' },
  productRevenue: { fontSize: 13, color: '#2196F3', marginTop: 2 },
  paymentRow: {
    backgroundColor: '#fff', padding: 14, borderRadius: 10, marginBottom: 8,
  },
  paymentMethod: { fontSize: 15, fontWeight: '600', color: '#1a1a1a', marginBottom: 8 },
  paymentStats: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  paymentOrders: { fontSize: 12, color: '#666', width: 50 },
  paymentRevenue: { fontSize: 13, fontWeight: '600', color: '#2196F3', flex: 1 },
  progressBar: { width: 80, height: 6, backgroundColor: '#eee', borderRadius: 3 },
  progressFill: { height: 6, backgroundColor: '#2196F3', borderRadius: 3 },
  paymentPercent: { fontSize: 12, color: '#666', width: 40, textAlign: 'right' },
});
