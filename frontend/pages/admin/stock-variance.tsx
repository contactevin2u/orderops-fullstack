import { useState, useEffect } from 'react';
import { api } from '@/utils/api';
import { Admin } from '@/components/Layout/Admin';

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
      
      // Build query parameters
      const params = new URLSearchParams();
      if (selectedDate) params.append('date', selectedDate);
      if (selectedDriver) params.append('driver_id', selectedDriver);
      
      // Note: This endpoint would need to be created
      const response = await api<{ 
        variances: StockVariance[], 
        summary: VarianceSummary 
      }>(`/lorry-management/variance-report?${params.toString()}`);
      
      setVariances(response.variances || []);
      setSummary(response.summary || {
        total_variances: 0,
        pending_variances: 0,
        resolved_variances: 0,
        drivers_on_hold: 0,
        total_variance_amount: 0
      });
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load variance data');
      // Set mock data for demonstration
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
          expected_count: 20,
          actual_count: 22,
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
      <Admin>
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">⏳ Loading variance data...</div>
        </div>
      </Admin>
    );
  }
  
  return (
    <Admin>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">📊 Stock Variance Dashboard</h1>
          <div className="flex space-x-4">
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={loadVariances}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
        
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <div className="font-medium">⚠️ API Error (Using Demo Data)</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        )}
        
        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-lg border p-4">
              <div className="text-2xl font-bold text-blue-600">{summary.total_variances}</div>
              <div className="text-sm text-gray-600">Total Variances</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-2xl font-bold text-yellow-600">{summary.pending_variances}</div>
              <div className="text-sm text-gray-600">Pending Review</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-2xl font-bold text-green-600">{summary.resolved_variances}</div>
              <div className="text-sm text-gray-600">Resolved</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-2xl font-bold text-red-600">{summary.drivers_on_hold}</div>
              <div className="text-sm text-gray-600">Drivers on Hold</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-2xl font-bold text-purple-600">
                {Math.abs(summary.total_variance_amount)}
              </div>
              <div className="text-sm text-gray-600">Net Variance</div>
            </div>
          </div>
        )}
        
        {/* Filters */}
        <div className="bg-white rounded-lg border p-4">
          <div className="flex space-x-4 items-center">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Driver</label>
              <select
                value={selectedDriver}
                onChange={(e) => setSelectedDriver(e.target.value)}
                className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Drivers</option>
                {Array.from(new Set(variances.map(v => v.driver_name))).map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
        
        {/* Variances Table */}
        <div className="bg-white rounded-lg border">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Stock Variances ({variances.length})</h2>
          </div>
          
          {variances.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Driver</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Lorry</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Date</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Expected</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Actual</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Variance</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {variances.map((variance, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div>
                          <div className="font-medium">{variance.driver_name}</div>
                          <div className="text-xs text-gray-500">ID: {variance.driver_id}</div>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono">{variance.lorry_id}</td>
                      <td className="px-4 py-3 text-sm">
                        {new Date(variance.date).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-center">{variance.expected_count}</td>
                      <td className="px-4 py-3 text-center">{variance.actual_count}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 text-sm font-medium rounded ${getVarianceColor(variance.variance)}`}>
                          {variance.variance > 0 ? `+${variance.variance}` : variance.variance}
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
                          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
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
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">✅</div>
              <p>No stock variances found</p>
              <p className="text-sm">All driver stock counts match expected amounts</p>
            </div>
          )}
        </div>
        
        {/* Variance Details Modal */}
        {showDetails && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b flex justify-between items-center">
                <h3 className="text-xl font-bold">
                  📊 Variance Details: {showDetails.driver_name}
                </h3>
                <button
                  onClick={() => setShowDetails(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ×
                </button>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Summary */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-semibold mb-3">Basic Information</h4>
                    <div className="space-y-2 text-sm">
                      <div><strong>Driver:</strong> {showDetails.driver_name}</div>
                      <div><strong>Lorry:</strong> {showDetails.lorry_id}</div>
                      <div><strong>Date:</strong> {new Date(showDetails.date).toLocaleDateString()}</div>
                      <div><strong>Status:</strong> 
                        <span className={`ml-2 inline-flex px-2 py-1 text-xs font-medium rounded ${getStatusColor(showDetails.status)}`}>
                          {showDetails.status.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-semibold mb-3">Stock Count Summary</h4>
                    <div className="space-y-2 text-sm">
                      <div><strong>Expected:</strong> {showDetails.expected_count} items</div>
                      <div><strong>Actual:</strong> {showDetails.actual_count} items</div>
                      <div>
                        <strong>Variance:</strong> 
                        <span className={`ml-2 font-semibold ${showDetails.variance === 0 ? 'text-green-600' : showDetails.variance > 0 ? 'text-orange-600' : 'text-red-600'}`}>
                          {showDetails.variance > 0 ? `+${showDetails.variance}` : showDetails.variance} items
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">
                        {showDetails.variance === 0 ? '✅ Perfect match' : 
                         showDetails.variance > 0 ? '📈 Excess stock found' : '📉 Items missing'}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Missing UIDs */}
                {showDetails.missing_uids.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-3 text-red-600">❌ Missing UIDs ({showDetails.missing_uids.length})</h4>
                    <div className="bg-red-50 rounded-lg p-4">
                      <div className="space-y-1 text-sm font-mono">
                        {showDetails.missing_uids.map((uid, index) => (
                          <div key={index} className="text-red-700">{uid}</div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Unexpected UIDs */}
                {showDetails.unexpected_uids.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-3 text-orange-600">➕ Unexpected UIDs ({showDetails.unexpected_uids.length})</h4>
                    <div className="bg-orange-50 rounded-lg p-4">
                      <div className="space-y-1 text-sm font-mono">
                        {showDetails.unexpected_uids.map((uid, index) => (
                          <div key={index} className="text-orange-700">{uid}</div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                
                {/* No Issues */}
                {showDetails.missing_uids.length === 0 && showDetails.unexpected_uids.length === 0 && (
                  <div className="bg-green-50 rounded-lg p-4 text-center">
                    <div className="text-2xl mb-2">✅</div>
                    <div className="text-green-800 font-medium">Perfect Stock Match</div>
                    <div className="text-sm text-green-600 mt-1">All expected UIDs were found, no unexpected UIDs present</div>
                  </div>
                )}
                
                {/* Action Recommendations */}
                <div className="bg-blue-50 rounded-lg p-4">
                  <h4 className="font-semibold mb-2 text-blue-800">💡 Recommended Actions</h4>
                  <div className="text-sm text-blue-700">
                    {showDetails.variance === 0 ? (
                      <p>✅ No action required - stock count is accurate</p>
                    ) : showDetails.variance > 0 ? (
                      <div className="space-y-1">
                        <p>• Investigate source of unexpected items</p>
                        <p>• Verify if items belong to another lorry</p>
                        <p>• Update inventory records if legitimate additions</p>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <p>• Search for missing items in driver's possession</p>
                        <p>• Check if items were delivered but not recorded</p>
                        <p>• Consider driver hold if items cannot be accounted for</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Admin>
  );
}