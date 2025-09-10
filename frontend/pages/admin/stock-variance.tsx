import { useState, useEffect } from 'react';
import { request } from '../../utils/api';
import AdminLayout from '@/components/Layout/AdminLayout';

interface StockVariance {
  driver_id: number;
  driver_name: string;
  lorry_id: string;
  date: string;
  expected_count: number;
  actual_count: number;
  variance: number;
  missing_uids: string[];
  unexpected_uids: string[];
  status: 'PENDING' | 'RESOLVED' | 'HOLD_GENERATED';
}

interface VarianceSummary {
  total_variances: number;
  pending_variances: number;
  resolved_variances: number;
  drivers_on_hold: number;
  total_variance_amount: number;
}

export default function StockVarianceDashboard() {
  const [variances, setVariances] = useState<StockVariance[]>([]);
  const [summary, setSummary] = useState<VarianceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedDriver, setSelectedDriver] = useState<string>('');
  const [showDetails, setShowDetails] = useState<StockVariance | null>(null);

  useEffect(() => {
    loadVariances();
  }, [selectedDate, selectedDriver]);

  const loadVariances = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (selectedDate) params.append('date', selectedDate);
      if (selectedDriver) params.append('driver_id', selectedDriver);

      const response = await request<{ variances: StockVariance[]; summary: VarianceSummary }>(`/lorry-management/stock-variance?${params.toString()}`);
      setVariances(response.variances || []);
      setSummary(response.summary);
    } catch (err: any) {
      setError(err.message || 'Failed to load variance data');
      // Mock data for demonstration
      setVariances([
        {
          driver_id: 1,
          driver_name: 'John Smith',
          lorry_id: 'CEH5295',
          date: selectedDate,
          expected_count: 15,
          actual_count: 13,
          variance: -2,
          missing_uids: ['SKU001-DRV001-20250909-001', 'SKU002-DRV001-20250909-002'],
          unexpected_uids: [],
          status: 'PENDING'
        },
        {
          driver_id: 2,
          driver_name: 'Jane Doe',
          lorry_id: 'ABC1234',
          date: selectedDate,
          expected_count: 8,
          actual_count: 10,
          variance: 2,
          missing_uids: [],
          unexpected_uids: ['SKU003-ADMIN-20250909-001', 'SKU004-ADMIN-20250909-002'],
          status: 'RESOLVED'
        }
      ]);
      setSummary({
        total_variances: 2,
        pending_variances: 1,
        resolved_variances: 1,
        drivers_on_hold: 1,
        total_variance_amount: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const getVarianceColor = (variance: number) => {
    if (variance === 0) return 'text-green-600 bg-green-100';
    if (variance > 0) return 'text-orange-600 bg-orange-100';
    return 'text-red-600 bg-red-100';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PENDING': return 'bg-yellow-100 text-yellow-800';
      case 'RESOLVED': return 'bg-green-100 text-green-800';
      case 'HOLD_GENERATED': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="container">
          <div className="flex items-center justify-center h-64">
            <div className="text-lg">⏳ Loading variance data...</div>
          </div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="container">
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">📊 Stock Variance Dashboard</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">Monitor driver stock discrepancies and take corrective actions</p>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Real-time variance detection
            </div>
          </div>

          {/* Controls */}
          <div className="card">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <span className="text-xl">🔍</span>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Filter Options</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">Filter variances by date and driver</p>
              </div>
            </div>
            <div className="flex space-x-4">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="p-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <select
                value={selectedDriver}
                onChange={(e) => setSelectedDriver(e.target.value)}
                className="p-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">All Drivers</option>
                <option value="1">John Smith</option>
                <option value="2">Jane Doe</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400 flex items-start space-x-3">
              <span className="text-xl">⚠️</span>
              <div>
                <div className="font-medium">API Error (Using Demo Data)</div>
                <div className="text-sm mt-1">{error}</div>
              </div>
            </div>
          )}

          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="card text-center">
                <div className="text-2xl font-bold text-blue-600">{summary.total_variances}</div>
                <div className="text-sm text-gray-600">Total Variances</div>
              </div>
              <div className="card text-center">
                <div className="text-2xl font-bold text-yellow-600">{summary.pending_variances}</div>
                <div className="text-sm text-gray-600">Pending</div>
              </div>
              <div className="card text-center">
                <div className="text-2xl font-bold text-green-600">{summary.resolved_variances}</div>
                <div className="text-sm text-gray-600">Resolved</div>
              </div>
              <div className="card text-center">
                <div className="text-2xl font-bold text-red-600">{summary.drivers_on_hold}</div>
                <div className="text-sm text-gray-600">Drivers on Hold</div>
              </div>
            </div>
          )}

          {/* Variance List */}
          <div className="card">
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                <span className="text-xl">📋</span>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Stock Variances ({variances.length})</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">Review and manage stock discrepancies</p>
              </div>
            </div>

            {variances.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Driver</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Lorry</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Expected</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Actual</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Variance</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-600">
                    {variances.map((variance, index) => (
                      <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-4 py-3">
                          <div className="font-medium text-gray-900 dark:text-white">{variance.driver_name}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">ID: {variance.driver_id}</div>
                        </td>
                        <td className="px-4 py-3 font-mono text-sm text-gray-900 dark:text-white">{variance.lorry_id}</td>
                        <td className="px-4 py-3 text-gray-900 dark:text-white">{variance.expected_count}</td>
                        <td className="px-4 py-3 text-gray-900 dark:text-white">{variance.actual_count}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${getVarianceColor(variance.variance)}`}>
                            {variance.variance > 0 ? '+' : ''}{variance.variance}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${getStatusColor(variance.status)}`}>
                            {variance.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setShowDetails(variance)}
                            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
                          >
                            View Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <div className="text-4xl mb-2">✅</div>
                <p>No stock variances found</p>
                <p className="text-sm">All driver stock matches expected levels</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}