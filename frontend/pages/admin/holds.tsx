import { useState, useEffect } from 'react';
import { request } from '../../utils/api';
import AdminLayout from '@/components/Layout/AdminLayout';

interface DriverHold {
  id: number;
  driver_id: number;
  driver_name: string;
  reason: string;
  description: string;
  status: 'ACTIVE' | 'RESOLVED';
  created_by: number;
  created_at: string;
  resolved_by?: number;
  resolved_at?: string;
  resolution_notes?: string;
}

interface Driver {
  id: number;
  name: string;
  employee_id: string;
  is_active: boolean;
}

export default function HoldManagement() {
  const [holds, setHolds] = useState<DriverHold[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<'ALL' | 'ACTIVE' | 'RESOLVED'>('ACTIVE');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showResolveModal, setShowResolveModal] = useState<DriverHold | null>(null);
  
  // Create hold form state
  const [createForm, setCreateForm] = useState({
    driver_id: '',
    reason: '',
    description: ''
  });
  
  const [resolveNotes, setResolveNotes] = useState('');
  
  useEffect(() => {
    loadHolds();
    loadDrivers();
  }, [selectedStatus]);
  
  const loadHolds = async () => {
    try {
      const statusFilter = selectedStatus === 'ALL' ? '' : `?status=${selectedStatus}`;
      const response = await request<DriverHold[]>(`/lorry-management/holds${statusFilter}`);
      setHolds(response || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load holds');
      console.error('Holds load error:', err);
    }
  };
  
  const loadDrivers = async () => {
    try {
      const response = await request<Driver[]>('/drivers');
      setDrivers((response || []).filter(d => d.is_active));
    } catch (err: any) {
      console.error('Failed to load drivers:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const handleCreateHold = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!createForm.driver_id || !createForm.reason) {
      setError('Driver and reason are required');
      return;
    }
    
    try {
      await request('/lorry-management/holds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          driver_id: parseInt(createForm.driver_id),
          reason: createForm.reason,
          description: createForm.description
        })
      });
      
      setShowCreateModal(false);
      setCreateForm({ driver_id: '', reason: '', description: '' });
      await loadHolds();
    } catch (err: any) {
      setError(err.message || 'Failed to create hold');
    }
  };
  
  const handleResolveHold = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!showResolveModal || !resolveNotes.trim()) {
      setError('Resolution notes are required');
      return;
    }
    
    try {
      await request(`/lorry-management/holds/${showResolveModal.id}/resolve`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolution_notes: resolveNotes
        })
      });
      
      setShowResolveModal(null);
      setResolveNotes('');
      await loadHolds();
    } catch (err: any) {
      setError(err.message || 'Failed to resolve hold');
    }
  };
  
  const getReasonBadgeColor = (reason: string) => {
    switch (reason.toLowerCase()) {
      case 'stock_variance': return 'bg-yellow-100 text-yellow-800';
      case 'disciplinary': return 'bg-red-100 text-red-800';
      case 'system_issue': return 'bg-blue-100 text-blue-800';
      case 'training': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  const formatReason = (reason: string) => {
    return reason.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  };
  
  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">⏳ Loading holds...</div>
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
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">🚫 Driver Hold Management</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">Manage driver holds for stock variance, disciplinary, and training purposes</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white px-6 py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-200 flex items-center space-x-2"
            >
              <span>➕</span>
              <span>Create Hold</span>
            </button>
          </div>
        
          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400 flex items-start space-x-3">
              <span className="text-xl">⚠️</span>
              <div>
                <div className="font-medium">Error</div>
                <div>{error}</div>
              </div>
            </div>
          )}
          
          {/* Status Filter */}
          <div className="card">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <span className="text-xl">🔍</span>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Filter Holds</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">View holds by status</p>
              </div>
            </div>
            <div className="flex space-x-4">
              {(['ALL', 'ACTIVE', 'RESOLVED'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setSelectedStatus(status)}
                  className={`px-4 py-2 rounded-xl font-medium transition-all duration-200 ${
                    selectedStatus === status
                      ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {status} {status === 'ACTIVE' && holds.filter(h => h.status === 'ACTIVE').length > 0 && 
                    `(${holds.filter(h => h.status === 'ACTIVE').length})`}
                </button>
              ))}
            </div>
          </div>
        
        {/* Holds List */}
        <div className="bg-white rounded-lg border">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">
              {selectedStatus === 'ALL' ? 'All Holds' : `${selectedStatus.toLowerCase().replace(/^\w/, c => c.toUpperCase())} Holds`} ({holds.length})
            </h2>
          </div>
          
          {holds.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Driver</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Reason</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Description</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Created</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {holds.map((hold) => (
                    <tr key={hold.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div>
                          <div className="font-medium">{hold.driver_name}</div>
                          <div className="text-xs text-gray-500">ID: {hold.driver_id}</div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${getReasonBadgeColor(hold.reason)}`}>
                          {formatReason(hold.reason)}
                        </span>
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        <div className="truncate" title={hold.description}>
                          {hold.description || '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                          hold.status === 'ACTIVE' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                        }`}>
                          {hold.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        <div>{new Date(hold.created_at).toLocaleDateString()}</div>
                        <div className="text-xs">{new Date(hold.created_at).toLocaleTimeString()}</div>
                      </td>
                      <td className="px-4 py-3">
                        {hold.status === 'ACTIVE' ? (
                          <button
                            onClick={() => setShowResolveModal(hold)}
                            className="text-green-600 hover:text-green-800 text-sm font-medium"
                          >
                            ✅ Resolve
                          </button>
                        ) : (
                          <div className="text-sm text-gray-500">
                            <div>Resolved: {hold.resolved_at && new Date(hold.resolved_at).toLocaleDateString()}</div>
                            {hold.resolution_notes && (
                              <div className="text-xs mt-1" title={hold.resolution_notes}>
                                📝 {hold.resolution_notes.length > 30 ? 
                                  `${hold.resolution_notes.substring(0, 30)}...` : 
                                  hold.resolution_notes}
                              </div>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">
                {selectedStatus === 'ACTIVE' ? '✅' : selectedStatus === 'RESOLVED' ? '🏁' : '📋'}
              </div>
              <p>No {selectedStatus.toLowerCase()} holds found</p>
              {selectedStatus === 'ACTIVE' && (
                <p className="text-sm">All drivers are currently available for work</p>
              )}
            </div>
          )}
        </div>
        
        {/* Create Hold Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full">
              <div className="p-6 border-b">
                <h3 className="text-xl font-bold">🚫 Create Driver Hold</h3>
              </div>
              
              <form onSubmit={handleCreateHold} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Driver *
                  </label>
                  <select
                    value={createForm.driver_id}
                    onChange={(e) => setCreateForm({...createForm, driver_id: e.target.value})}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-red-500"
                    required
                  >
                    <option value="">Select a driver...</option>
                    {drivers.map((driver) => (
                      <option key={driver.id} value={driver.id}>
                        {driver.name} ({driver.employee_id})
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reason *
                  </label>
                  <select
                    value={createForm.reason}
                    onChange={(e) => setCreateForm({...createForm, reason: e.target.value})}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-red-500"
                    required
                  >
                    <option value="">Select a reason...</option>
                    <option value="stock_variance">Stock Variance</option>
                    <option value="disciplinary">Disciplinary Action</option>
                    <option value="system_issue">System Issue</option>
                    <option value="training">Training Required</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    value={createForm.description}
                    onChange={(e) => setCreateForm({...createForm, description: e.target.value})}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-red-500"
                    rows={3}
                    placeholder="Additional details about the hold..."
                  />
                </div>
                
                <div className="flex space-x-4 pt-4">
                  <button
                    type="submit"
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg font-medium"
                  >
                    🚫 Create Hold
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateModal(false);
                      setCreateForm({ driver_id: '', reason: '', description: '' });
                    }}
                    className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-3 rounded-lg font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
        
        {/* Resolve Hold Modal */}
        {showResolveModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full">
              <div className="p-6 border-b">
                <h3 className="text-xl font-bold">✅ Resolve Hold</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Driver: <strong>{showResolveModal.driver_name}</strong>
                </p>
                <p className="text-sm text-gray-600">
                  Reason: <strong>{formatReason(showResolveModal.reason)}</strong>
                </p>
              </div>
              
              <form onSubmit={handleResolveHold} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Resolution Notes *
                  </label>
                  <textarea
                    value={resolveNotes}
                    onChange={(e) => setResolveNotes(e.target.value)}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500"
                    rows={4}
                    placeholder="Describe how the hold was resolved and any corrective actions taken..."
                    required
                  />
                </div>
                
                <div className="flex space-x-4 pt-4">
                  <button
                    type="submit"
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-medium"
                  >
                    ✅ Resolve Hold
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowResolveModal(null);
                      setResolveNotes('');
                    }}
                    className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-3 rounded-lg font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
        </div>
      </div>
    </AdminLayout>
  );
}