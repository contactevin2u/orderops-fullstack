import { useState, useEffect } from 'react';
import { api } from '@/utils/api';
import { Admin } from '@/components/Layout/Admin';

interface UIDSearchResult {
  uid: string;
  sku_code: string;
  sku_name: string;
  status: string;
  current_location: string;
  created_at: string;
}

interface UIDDetails {
  uid: string;
  sku: {
    id: number;
    code: string;
    name: string;
    type: string | null;
  };
  item: {
    id: number;
    status: string;
    item_type: string;
    oem_serial_number: string | null;
    created_at: string;
  };
  current_location: string;
  current_lorry: string | null;
  current_driver: {
    id: number;
    name: string;
    employee_id: string;
  } | null;
  stock_history: Array<{
    id: number;
    action: string;
    lorry_id: string;
    order_id: number | null;
    driver_id: number | null;
    admin_user: string;
    notes: string | null;
    transaction_date: string;
    created_at: string;
  }>;
  delivery_history: Array<{
    id: number;
    order_id: number;
    order_number: string;
    action: string;
    driver_name: string | null;
    notes: string | null;
    scanned_at: string;
  }>;
  total_transactions: number;
}

export default function UIDManagement() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<UIDSearchResult[]>([]);
  const [selectedUID, setSelectedUID] = useState<UIDDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleSearch = async () => {
    if (searchQuery.trim().length < 2) {
      setError('Search query must be at least 2 characters');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await api<{ results: UIDSearchResult[] }>(`/inventory/uid/search?query=${encodeURIComponent(searchQuery)}`);
      setSearchResults(response.results);
    } catch (err: any) {
      setError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };
  
  const handleViewDetails = async (uid: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api<UIDDetails>(`/inventory/uid/${encodeURIComponent(uid)}/details`);
      setSelectedUID(response);
    } catch (err: any) {
      setError(err.message || 'Failed to load UID details');
    } finally {
      setLoading(false);
    }
  };
  
  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'warehouse': return 'bg-gray-100 text-gray-800';
      case 'with_driver': return 'bg-blue-100 text-blue-800';
      case 'delivered': return 'bg-green-100 text-green-800';
      case 'returned': return 'bg-yellow-100 text-yellow-800';
      case 'in_repair': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  const getActionBadgeColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'load': return 'bg-green-100 text-green-800';
      case 'unload': return 'bg-red-100 text-red-800';
      case 'delivery': return 'bg-blue-100 text-blue-800';
      case 'collection': return 'bg-purple-100 text-purple-800';
      case 'deliver': return 'bg-green-100 text-green-800';
      case 'collect': return 'bg-purple-100 text-purple-800';
      case 'repair': return 'bg-orange-100 text-orange-800';
      case 'swap': return 'bg-indigo-100 text-indigo-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  return (
    <Admin>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">UID Management & Tracking</h1>
        </div>
        
        {/* Search Section */}
        <div className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-semibold mb-4">🔍 Search UIDs</h2>
          <div className="flex space-x-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Enter UID or partial UID to search..."
              className="flex-1 p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSearch}
              disabled={loading || searchQuery.trim().length < 2}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50"
            >
              {loading ? '⏳ Searching...' : '🔍 Search'}
            </button>
          </div>
          
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}
        </div>
        
        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="bg-white rounded-lg border">
            <div className="p-4 border-b">
              <h3 className="text-lg font-semibold">📋 Search Results ({searchResults.length})</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">UID</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">SKU</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Current Location</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Created</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {searchResults.map((result) => (
                    <tr key={result.uid} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-sm">{result.uid}</td>
                      <td className="px-4 py-3">
                        <div>
                          <div className="font-medium text-sm">{result.sku_code}</div>
                          <div className="text-xs text-gray-500">{result.sku_name}</div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${getStatusBadgeColor(result.status)}`}>
                          {result.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{result.current_location}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(result.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleViewDetails(result.uid)}
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
          </div>
        )}
        
        {/* UID Details Modal */}
        {selectedUID && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b flex justify-between items-center">
                <h3 className="text-xl font-bold">📦 UID Details: {selectedUID.uid}</h3>
                <button
                  onClick={() => setSelectedUID(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ×
                </button>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Basic Information */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-semibold mb-3">Basic Information</h4>
                    <div className="space-y-2 text-sm">
                      <div><strong>UID:</strong> {selectedUID.uid}</div>
                      <div><strong>Status:</strong> 
                        <span className={`ml-2 inline-flex px-2 py-1 text-xs font-medium rounded ${getStatusBadgeColor(selectedUID.item.status)}`}>
                          {selectedUID.item.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>
                      <div><strong>Type:</strong> {selectedUID.item.item_type}</div>
                      <div><strong>Current Location:</strong> {selectedUID.current_location}</div>
                      {selectedUID.current_lorry && (
                        <div><strong>Current Lorry:</strong> {selectedUID.current_lorry}</div>
                      )}
                      {selectedUID.item.oem_serial_number && (
                        <div><strong>OEM Serial:</strong> {selectedUID.item.oem_serial_number}</div>
                      )}
                      <div><strong>Created:</strong> {new Date(selectedUID.item.created_at).toLocaleString()}</div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-semibold mb-3">SKU Information</h4>
                    <div className="space-y-2 text-sm">
                      <div><strong>SKU Code:</strong> {selectedUID.sku.code}</div>
                      <div><strong>SKU Name:</strong> {selectedUID.sku.name}</div>
                      {selectedUID.sku.type && (
                        <div><strong>SKU Type:</strong> {selectedUID.sku.type}</div>
                      )}
                    </div>
                    
                    {selectedUID.current_driver && (
                      <div className="mt-4 pt-4 border-t">
                        <h5 className="font-medium mb-2">Current Driver</h5>
                        <div className="space-y-1 text-sm">
                          <div><strong>Name:</strong> {selectedUID.current_driver.name}</div>
                          <div><strong>Employee ID:</strong> {selectedUID.current_driver.employee_id}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Stock Transaction History */}
                <div>
                  <h4 className="font-semibold mb-3">📋 Stock Movement History ({selectedUID.stock_history.length})</h4>
                  {selectedUID.stock_history.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left">Date</th>
                            <th className="px-3 py-2 text-left">Action</th>
                            <th className="px-3 py-2 text-left">Lorry</th>
                            <th className="px-3 py-2 text-left">Admin User</th>
                            <th className="px-3 py-2 text-left">Notes</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {selectedUID.stock_history.map((transaction) => (
                            <tr key={transaction.id} className="hover:bg-gray-50">
                              <td className="px-3 py-2">
                                {new Date(transaction.transaction_date).toLocaleString()}
                              </td>
                              <td className="px-3 py-2">
                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${getActionBadgeColor(transaction.action)}`}>
                                  {transaction.action}
                                </span>
                              </td>
                              <td className="px-3 py-2 font-mono">{transaction.lorry_id}</td>
                              <td className="px-3 py-2">{transaction.admin_user}</td>
                              <td className="px-3 py-2">{transaction.notes || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No stock movements recorded</p>
                  )}
                </div>
                
                {/* Delivery History */}
                <div>
                  <h4 className="font-semibold mb-3">🚚 Delivery History ({selectedUID.delivery_history.length})</h4>
                  {selectedUID.delivery_history.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left">Date</th>
                            <th className="px-3 py-2 text-left">Order</th>
                            <th className="px-3 py-2 text-left">Action</th>
                            <th className="px-3 py-2 text-left">Driver</th>
                            <th className="px-3 py-2 text-left">Notes</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {selectedUID.delivery_history.map((delivery) => (
                            <tr key={delivery.id} className="hover:bg-gray-50">
                              <td className="px-3 py-2">
                                {new Date(delivery.scanned_at).toLocaleString()}
                              </td>
                              <td className="px-3 py-2">
                                <div>
                                  <div className="font-medium">#{delivery.order_number}</div>
                                  <div className="text-xs text-gray-500">ID: {delivery.order_id}</div>
                                </div>
                              </td>
                              <td className="px-3 py-2">
                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${getActionBadgeColor(delivery.action)}`}>
                                  {delivery.action}
                                </span>
                              </td>
                              <td className="px-3 py-2">{delivery.driver_name || '-'}</td>
                              <td className="px-3 py-2">{delivery.notes || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No delivery actions recorded</p>
                  )}
                </div>
                
                {/* Summary Stats */}
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-blue-600">{selectedUID.total_transactions}</div>
                      <div className="text-sm text-gray-600">Total Transactions</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-600">{selectedUID.stock_history.length}</div>
                      <div className="text-sm text-gray-600">Stock Movements</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-purple-600">{selectedUID.delivery_history.length}</div>
                      <div className="text-sm text-gray-600">Delivery Actions</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {searchResults.length === 0 && searchQuery.length >= 2 && !loading && (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">🔍</div>
            <p>No UIDs found matching &quot;{searchQuery}&quot;</p>
            <p className="text-sm">Try a different search term or partial UID</p>
          </div>
        )}
      </div>
    </Admin>
  );
}