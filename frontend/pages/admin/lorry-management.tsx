// import { useSession } from 'next-auth/react';
import { useEffect, useState, useMemo } from 'react';
import { request } from '../../utils/api';
import AdminLayout from '@/components/Layout/AdminLayout';

// Types
type Assignment = {
  id: number;
  lorry_id: string;
  driver_id: number;
  date: string;
  notes?: string | null;
  driver_name?: string;
  assignment_date?: string;
  status: string;
  stock_verified: boolean;
};

type Hold = {
  id: number;
  driver_id: number;
  reason: string;
  status: 'ACTIVE' | 'RESOLVED';
  created_at: string;
  driver_name?: string;
};

type Driver = {
  id: number;
  name?: string | null;
  phone?: string | null;
  base_warehouse?: string;
  priority_lorry_id?: string | null;
  created_at?: string;
};

type Lorry = {
  id: number;
  lorry_id: string;
  plate_number?: string | null;
  model?: string | null;
  capacity?: string | null;
  base_warehouse: string;
  is_active: boolean;
  is_available: boolean;
  notes?: string | null;
  current_location?: string | null;
  last_maintenance_date?: string | null;
  created_at: string;
  updated_at: string;
};

type LorryInventory = {
  lorry_id: string;
  current_stock_count: number;
  current_uids: string[];
  has_more: boolean;
};

type StockTransaction = {
  id: number;
  lorry_id: string;
  action: string;
  uid: string;
  admin_user: string;
  notes?: string;
  transaction_date: string;
  created_at: string;
};

type AssignmentStatus = {
  assignment_date: string;
  scheduled_drivers: number;
  assigned_drivers: number;
  unassigned_drivers: number;
  available_lorries: number;
  can_auto_assign: boolean;
  assignments: Array<{
    driver_id: number;
    driver_name: string;
    lorry_id: string;
    status: string;
    assigned_at: string;
  }>;
};

// API helper
async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await request<T>(path, init);
  } catch (e: any) {
    throw new Error(e.message || `Failed to fetch ${path}`);
  }
}

const asArray = <T,>(x: unknown): T[] => (Array.isArray(x) ? (x as T[]) : []);

function LorryManagementPage() {
  // const { status } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'lorries' | 'assignments' | 'scanner' | 'transactions'>('dashboard');

  // Data states
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [holds, setHolds] = useState<Hold[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [lorries, setLorries] = useState<Lorry[]>([]);
  const [lorryInventories, setLorryInventories] = useState<LorryInventory[]>([]);
  const [stockTransactions, setStockTransactions] = useState<StockTransaction[]>([]);
  const [assignmentStatus, setAssignmentStatus] = useState<AssignmentStatus | null>(null);

  // Scanner states
  const [selectedLorry, setSelectedLorry] = useState<string>('');
  const [scanMode, setScanMode] = useState<'load' | 'unload'>('load');
  const [scanInput, setScanInput] = useState('');
  const [scannedUIDs, setScannedUIDs] = useState<string[]>([]);
  const [scanNotes, setScanNotes] = useState('');
  const [scanLoading, setScanLoading] = useState(false);

  // Lorry management states
  const [showCreateLorry, setShowCreateLorry] = useState(false);
  const [createLorryForm, setCreateLorryForm] = useState({
    lorry_id: '',
    plate_number: '',
    model: '',
    capacity: '',
    base_warehouse: 'BATU_CAVES',
    notes: ''
  });
  const [createLorryLoading, setCreateLorryLoading] = useState(false);

  // Auto-assignment states
  const [assignmentDate, setAssignmentDate] = useState(new Date().toISOString().split('T')[0]);
  const [autoAssignLoading, setAutoAssignLoading] = useState(false);

  const driverById = useMemo(() => {
    const m = new Map<number, Driver>();
    for (const dr of drivers) m.set(dr.id as number, dr);
    return m;
  }, [drivers]);

  // Load initial data
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [A, H, D, L, I, T, S] = await Promise.allSettled([
          api<Assignment[]>('/lorry-management/assignments'),
          api<Hold[]>('/lorry-management/holds'),
          api<{ drivers: Driver[] }>('/lorry-management/drivers'),
          api<{ lorries: Lorry[] }>('/lorry-management/lorries'),
          api<{ lorries: LorryInventory[] }>('/lorry-management/stock/summary'),
          api<StockTransaction[]>('/lorry-management/stock/transactions?limit=50'),
          api<AssignmentStatus>('/lorry-management/assignment-status'),
        ]);

        if (!cancelled) {
          setAssignments(A.status === 'fulfilled' ? asArray<Assignment>(A.value) : []);
          setHolds(H.status === 'fulfilled' ? asArray<Hold>(H.value) : []);
          setDrivers(D.status === 'fulfilled' ? ((D.value as any)?.drivers || []) as Driver[] : []);
          setLorries(L.status === 'fulfilled' ? ((L.value as any)?.lorries || []) as Lorry[] : []);
          setLorryInventories(I.status === 'fulfilled' ? (I.value as any)?.lorries || [] : []);
          setStockTransactions(T.status === 'fulfilled' ? asArray<StockTransaction>(T.value) : []);
          setAssignmentStatus(S.status === 'fulfilled' ? S.value as AssignmentStatus : null);

          if ([A, H, D, L, I, T, S].some(r => r.status === 'rejected')) {
            const reasons = [A, H, D, L, I, T, S]
              .map(r => (r.status === 'rejected' ? (r.reason?.message || String(r.reason)) : null))
              .filter(Boolean)
              .join(' | ');
            setError(`Some data failed to load: ${reasons}`);
          }
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleScanSubmit = async () => {
    if (!selectedLorry || scannedUIDs.length === 0) {
      setError('Please select a lorry and scan at least one UID');
      return;
    }

    setScanLoading(true);
    try {
      const endpoint = `/lorry-management/stock/${selectedLorry}/${scanMode}`;
      await api(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          uids: scannedUIDs,
          notes: scanNotes || undefined,
        }),
      });

      // Clear scanner
      setScannedUIDs([]);
      setScanInput('');
      setScanNotes('');
      
      // Refresh inventory data
      const inventoryResult = await api<{ lorries: LorryInventory[] }>('/lorry-management/stock/summary');
      setLorryInventories((inventoryResult as any)?.lorries || []);
      
      // Refresh transactions
      const transactionsResult = await api<StockTransaction[]>('/lorry-management/stock/transactions?limit=50');
      setStockTransactions(asArray<StockTransaction>(transactionsResult));

      alert(`Successfully ${scanMode}ed ${scannedUIDs.length} UIDs ${scanMode === 'load' ? 'into' : 'from'} ${selectedLorry}`);
    } catch (e: any) {
      setError(e.message || `Failed to ${scanMode} stock`);
    } finally {
      setScanLoading(false);
    }
  };

  const handleScanInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = scanInput.trim();
    if (trimmed && !scannedUIDs.includes(trimmed)) {
      setScannedUIDs([...scannedUIDs, trimmed]);
      setScanInput('');
    }
  };

  const removeScannedUID = (uid: string) => {
    setScannedUIDs(scannedUIDs.filter(u => u !== uid));
  };

  // Lorry creation handler
  const handleCreateLorry = async () => {
    if (!createLorryForm.lorry_id.trim()) {
      setError('Lorry ID is required');
      return;
    }

    setCreateLorryLoading(true);
    try {
      await api('/lorry-management/lorries', {
        method: 'POST',
        body: JSON.stringify({
          lorry_id: createLorryForm.lorry_id.trim(),
          plate_number: createLorryForm.plate_number.trim() || undefined,
          model: createLorryForm.model.trim() || undefined,
          capacity: createLorryForm.capacity.trim() || undefined,
          base_warehouse: createLorryForm.base_warehouse,
          notes: createLorryForm.notes.trim() || undefined,
        }),
      });

      // Reset form
      setCreateLorryForm({
        lorry_id: '',
        plate_number: '',
        model: '',
        capacity: '',
        base_warehouse: 'BATU_CAVES',
        notes: ''
      });
      setShowCreateLorry(false);

      // Refresh lorries data
      const lorriesResult = await api<{ lorries: Lorry[] }>('/lorry-management/lorries');
      setLorries((lorriesResult as any)?.lorries || []);

      alert(`Successfully created lorry ${createLorryForm.lorry_id}`);
    } catch (e: any) {
      setError(e.message || 'Failed to create lorry');
    } finally {
      setCreateLorryLoading(false);
    }
  };

  // Auto-assignment handler
  const handleAutoAssign = async () => {
    setAutoAssignLoading(true);
    try {
      const result = await api('/lorry-management/auto-assign', {
        method: 'POST',
        body: JSON.stringify({
          assignment_date: assignmentDate,
        }),
      });

      // Refresh assignments and status
      const [assignmentsResult, statusResult] = await Promise.allSettled([
        api<Assignment[]>('/lorry-management/assignments'),
        api<AssignmentStatus>(`/lorry-management/assignment-status?date=${assignmentDate}`),
      ]);

      if (assignmentsResult.status === 'fulfilled') {
        setAssignments(asArray<Assignment>(assignmentsResult.value));
      }
      if (statusResult.status === 'fulfilled') {
        setAssignmentStatus(statusResult.value as AssignmentStatus);
      }

      alert(`Auto-assignment completed for ${assignmentDate}. Check the assignments tab for details.`);
    } catch (e: any) {
      setError(e.message || 'Failed to auto-assign lorries');
    } finally {
      setAutoAssignLoading(false);
    }
  };

  // Update priority lorry handler
  const handleUpdatePriorityLorry = async (driverId: number, priorityLorryId: string | null) => {
    try {
      await api(`/lorry-management/drivers/${driverId}/priority-lorry`, {
        method: 'PATCH',
        body: JSON.stringify({
          priority_lorry_id: priorityLorryId,
        }),
      });

      // Update local state
      setDrivers(prevDrivers => 
        prevDrivers.map(driver => 
          driver.id === driverId 
            ? { ...driver, priority_lorry_id: priorityLorryId }
            : driver
        )
      );

      alert(`Updated priority lorry for driver`);
    } catch (e: any) {
      setError(e.message || 'Failed to update priority lorry');
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">🚛 Lorry Management</h1>
        <div className="text-sm text-gray-500">
          {new Date().toLocaleDateString()} • Real-time Admin Dashboard
        </div>
      </div>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 text-red-700 p-4">
          <div className="flex items-center">
            <span className="text-red-500 mr-2">⚠️</span>
            {error}
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-gray-500">Loading lorry management data…</div>
        </div>
      ) : (
        <>
          {/* Navigation Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8">
              {[
                { id: 'dashboard', label: '📊 Dashboard & Auto-Assign', icon: '📊' },
                { id: 'lorries', label: '🚛 Lorry Management', icon: '🚛' },
                { id: 'assignments', label: '📋 Assignments', icon: '📋' },
                { id: 'scanner', label: '📱 Stock Scanner', icon: '📱' },
                { id: 'transactions', label: '📜 History', icon: '📜' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Automated Assignment Section */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center text-blue-800">
                  🤖 Automated Lorry Assignment
                </h2>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Assignment Date
                    </label>
                    <input
                      type="date"
                      value={assignmentDate}
                      onChange={(e) => setAssignmentDate(e.target.value)}
                      className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      disabled={autoAssignLoading}
                    />
                    
                    <button
                      onClick={handleAutoAssign}
                      disabled={autoAssignLoading || !assignmentDate}
                      className="mt-3 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                      {autoAssignLoading ? (
                        '⏳ Processing Auto-Assignment...'
                      ) : (
                        '🎯 Auto-Assign Lorries for Date'
                      )}
                    </button>
                  </div>
                  
                  {assignmentStatus && (
                    <div className="bg-white rounded-lg border p-4">
                      <h3 className="font-medium text-gray-900 mb-3">Assignment Status for {assignmentStatus.assignment_date}</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Scheduled Drivers:</span>
                          <span className="font-medium">{assignmentStatus.scheduled_drivers}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Assigned Drivers:</span>
                          <span className="font-medium text-green-600">{assignmentStatus.assigned_drivers}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Unassigned Drivers:</span>
                          <span className="font-medium text-red-600">{assignmentStatus.unassigned_drivers}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Available Lorries:</span>
                          <span className="font-medium text-blue-600">{assignmentStatus.available_lorries}</span>
                        </div>
                        {assignmentStatus.can_auto_assign && (
                          <div className="mt-2 p-2 bg-green-50 text-green-800 text-xs rounded">
                            ✅ Auto-assignment available for this date
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{lorries.length}</div>
                  <div className="text-blue-800 font-medium">Total Lorries</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{lorryInventories.length}</div>
                  <div className="text-purple-800 font-medium">Active Lorries</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {lorryInventories.reduce((sum, l) => sum + l.current_stock_count, 0)}
                  </div>
                  <div className="text-green-800 font-medium">Total Stock Items</div>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">
                    {holds.filter(h => h.status === 'ACTIVE').length}
                  </div>
                  <div className="text-red-800 font-medium">Active Holds</div>
                </div>
              </div>

              {/* Real-time Lorry Inventory */}
              <div className="bg-white rounded-lg border">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold flex items-center">
                    📦 Real-time Lorry Inventory
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Lorry ID</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Stock Count</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Sample UIDs</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {lorryInventories.map(lorry => (
                        <tr key={lorry.lorry_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <div className="font-mono font-medium">{lorry.lorry_id}</div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center">
                              <span className="text-lg font-semibold">{lorry.current_stock_count}</span>
                              {lorry.current_stock_count === 0 && (
                                <span className="ml-2 text-gray-500 text-sm">(Empty)</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-sm font-mono text-gray-600">
                              {lorry.current_uids.length > 0 ? (
                                <>
                                  {lorry.current_uids.slice(0, 3).join(', ')}
                                  {lorry.has_more && ' ...'}
                                </>
                              ) : (
                                <span className="text-gray-400">No items</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {lorry.current_stock_count > 0 ? (
                              <span className="inline-flex px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                                Loaded
                              </span>
                            ) : (
                              <span className="inline-flex px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                                Empty
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                      {lorryInventories.length === 0 && (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                            No lorry inventory data available
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Lorries Tab */}
          {activeTab === 'lorries' && (
            <div className="space-y-6">
              {/* Create Lorry Section */}
              <div className="bg-white rounded-lg border">
                <div className="p-4 border-b flex justify-between items-center">
                  <h2 className="text-lg font-semibold flex items-center">
                    🚛 Lorry Fleet Management
                  </h2>
                  <button
                    onClick={() => setShowCreateLorry(!showCreateLorry)}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium"
                  >
                    ➕ Create New Lorry
                  </button>
                </div>

                {showCreateLorry && (
                  <div className="p-4 border-b bg-gray-50">
                    <h3 className="font-medium mb-4">Create New Lorry</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Lorry ID * (e.g., LRY001)
                        </label>
                        <input
                          type="text"
                          value={createLorryForm.lorry_id}
                          onChange={(e) => setCreateLorryForm({...createLorryForm, lorry_id: e.target.value})}
                          placeholder="LRY001"
                          className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          disabled={createLorryLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Plate Number
                        </label>
                        <input
                          type="text"
                          value={createLorryForm.plate_number}
                          onChange={(e) => setCreateLorryForm({...createLorryForm, plate_number: e.target.value})}
                          placeholder="ABC1234"
                          className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          disabled={createLorryLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Model
                        </label>
                        <input
                          type="text"
                          value={createLorryForm.model}
                          onChange={(e) => setCreateLorryForm({...createLorryForm, model: e.target.value})}
                          placeholder="Ford Transit"
                          className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          disabled={createLorryLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Capacity
                        </label>
                        <input
                          type="text"
                          value={createLorryForm.capacity}
                          onChange={(e) => setCreateLorryForm({...createLorryForm, capacity: e.target.value})}
                          placeholder="1 ton"
                          className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          disabled={createLorryLoading}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Base Warehouse
                        </label>
                        <select
                          value={createLorryForm.base_warehouse}
                          onChange={(e) => setCreateLorryForm({...createLorryForm, base_warehouse: e.target.value})}
                          className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          disabled={createLorryLoading}
                        >
                          <option value="BATU_CAVES">Batu Caves</option>
                          <option value="KOTA_KINABALU">Kota Kinabalu</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Notes
                        </label>
                        <input
                          type="text"
                          value={createLorryForm.notes}
                          onChange={(e) => setCreateLorryForm({...createLorryForm, notes: e.target.value})}
                          placeholder="Optional notes..."
                          className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          disabled={createLorryLoading}
                        />
                      </div>
                    </div>
                    <div className="mt-4 flex space-x-3">
                      <button
                        onClick={handleCreateLorry}
                        disabled={!createLorryForm.lorry_id.trim() || createLorryLoading}
                        className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
                      >
                        {createLorryLoading ? '⏳ Creating...' : '✅ Create Lorry'}
                      </button>
                      <button
                        onClick={() => setShowCreateLorry(false)}
                        className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-medium"
                        disabled={createLorryLoading}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Lorries List */}
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Lorry ID</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Plate Number</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Model</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Capacity</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Warehouse</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Status</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {lorries.map(lorry => (
                        <tr key={lorry.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <span className="font-mono font-medium">{lorry.lorry_id}</span>
                          </td>
                          <td className="px-4 py-3">
                            {lorry.plate_number || '-'}
                          </td>
                          <td className="px-4 py-3">
                            {lorry.model || '-'}
                          </td>
                          <td className="px-4 py-3">
                            {lorry.capacity || '-'}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm">{lorry.base_warehouse.replace('_', ' ')}</span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex space-x-2">
                              <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                                lorry.is_active 
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-gray-100 text-gray-800'
                              }`}>
                                {lorry.is_active ? 'Active' : 'Inactive'}
                              </span>
                              <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                                lorry.is_available 
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {lorry.is_available ? 'Available' : 'Busy'}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500">
                            {lorry.notes || '-'}
                          </td>
                        </tr>
                      ))}
                      {lorries.length === 0 && (
                        <tr>
                          <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                            No lorries found. Create your first lorry above.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Driver Priority Lorries */}
              <div className="bg-white rounded-lg border">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold flex items-center">
                    👥 Driver Priority Lorry Settings
                  </h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Set preferred lorries for drivers. Auto-assignment will prioritize these preferences.
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Driver</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Phone</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Base Warehouse</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Priority Lorry</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {drivers.map(driver => (
                        <tr key={driver.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <div>
                              <div className="font-medium">
                                {driver.name || `Driver ${driver.id}`}
                              </div>
                              <div className="text-sm text-gray-500">ID: {driver.id}</div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {driver.phone || '-'}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {driver.base_warehouse?.replace('_', ' ') || '-'}
                          </td>
                          <td className="px-4 py-3">
                            <select
                              value={driver.priority_lorry_id || ''}
                              onChange={(e) => handleUpdatePriorityLorry(driver.id, e.target.value || null)}
                              className="p-2 border rounded focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="">No preference</option>
                              {lorries
                                .filter(l => l.is_active)
                                .map(lorry => (
                                <option key={lorry.lorry_id} value={lorry.lorry_id}>
                                  {lorry.lorry_id} {lorry.plate_number && `(${lorry.plate_number})`}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="px-4 py-3">
                            {driver.priority_lorry_id && (
                              <button
                                onClick={() => handleUpdatePriorityLorry(driver.id, null)}
                                className="text-red-600 hover:text-red-800 text-sm"
                              >
                                Clear
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                      {drivers.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                            No active drivers found
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Stock Scanner Tab */}
          {activeTab === 'scanner' && (
            <div className="space-y-6">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center">
                  <span className="text-yellow-600 text-lg mr-2">🔐</span>
                  <div>
                    <h3 className="font-medium text-yellow-800">Admin-Only Stock Management</h3>
                    <p className="text-sm text-yellow-700">Only admins can load/unload lorry inventory to prevent driver manipulation.</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Scanner Controls */}
                <div className="bg-white rounded-lg border p-6">
                  <h2 className="text-lg font-semibold mb-4 flex items-center">
                    📱 UID Scanner Interface
                  </h2>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Select Lorry
                      </label>
                      <select
                        value={selectedLorry}
                        onChange={(e) => setSelectedLorry(e.target.value)}
                        className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Choose a lorry...</option>
                        {assignments.map(a => (
                          <option key={a.lorry_id} value={a.lorry_id}>
                            {a.lorry_id} - {driverById.get(a.driver_id)?.name || `Driver ${a.driver_id}`}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Scan Mode
                      </label>
                      <div className="flex space-x-4">
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="scanMode"
                            value="load"
                            checked={scanMode === 'load'}
                            onChange={(e) => setScanMode(e.target.value as 'load')}
                            className="mr-2"
                          />
                          <span className="text-green-700">📦 LOAD Stock</span>
                        </label>
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="scanMode"
                            value="unload"
                            checked={scanMode === 'unload'}
                            onChange={(e) => setScanMode(e.target.value as 'unload')}
                            className="mr-2"
                          />
                          <span className="text-red-700">📤 UNLOAD Stock</span>
                        </label>
                      </div>
                    </div>

                    <form onSubmit={handleScanInputSubmit} className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Scan UID
                        </label>
                        <div className="flex space-x-2">
                          <input
                            type="text"
                            value={scanInput}
                            onChange={(e) => setScanInput(e.target.value)}
                            placeholder="Scan or enter UID..."
                            className="flex-1 p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                            disabled={scanLoading}
                          />
                          <button
                            type="submit"
                            disabled={!scanInput.trim() || scanLoading}
                            className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                          >
                            Add
                          </button>
                        </div>
                      </div>
                    </form>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Notes (Optional)
                      </label>
                      <textarea
                        value={scanNotes}
                        onChange={(e) => setScanNotes(e.target.value)}
                        placeholder="Add any notes about this stock operation..."
                        rows={3}
                        className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        disabled={scanLoading}
                      />
                    </div>

                    <button
                      onClick={handleScanSubmit}
                      disabled={!selectedLorry || scannedUIDs.length === 0 || scanLoading}
                      className={`w-full p-4 rounded-lg font-medium ${
                        scanMode === 'load'
                          ? 'bg-green-600 hover:bg-green-700'
                          : 'bg-red-600 hover:bg-red-700'
                      } text-white disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {scanLoading ? 'Processing...' : (
                        <>
                          {scanMode === 'load' ? '📦 LOAD' : '📤 UNLOAD'} {scannedUIDs.length} UIDs {scanMode === 'load' ? 'INTO' : 'FROM'} {selectedLorry || 'LORRY'}
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Scanned UIDs */}
                <div className="bg-white rounded-lg border p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center">
                    📋 Scanned UIDs ({scannedUIDs.length})
                  </h3>
                  
                  {scannedUIDs.length > 0 ? (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {scannedUIDs.map((uid, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <span className="font-mono text-sm">{uid}</span>
                          <button
                            onClick={() => removeScannedUID(uid)}
                            className="text-red-500 hover:text-red-700 p-1"
                            title="Remove"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <div className="text-4xl mb-2">📱</div>
                      <p>No UIDs scanned yet</p>
                      <p className="text-sm">Start scanning UIDs to add them here</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Assignments Tab */}
          {activeTab === 'assignments' && (
            <div className="space-y-6">
              <div className="bg-white rounded-lg border">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold flex items-center">
                    📋 Lorry Assignments
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Driver</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Lorry</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Date</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Status</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Stock Verified</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {assignments.map(assignment => (
                        <tr key={assignment.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <div>
                              <div className="font-medium">
                                {driverById.get(assignment.driver_id)?.name || `Driver ${assignment.driver_id}`}
                              </div>
                              <div className="text-sm text-gray-500">
                                ID: {assignment.driver_id}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="font-mono font-medium">{assignment.lorry_id}</span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {assignment.assignment_date || assignment.date}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                              assignment.status === 'ACTIVE' 
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {assignment.status}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {assignment.stock_verified ? (
                              <span className="text-green-600">✅ Verified</span>
                            ) : (
                              <span className="text-yellow-600">⏳ Pending</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500">
                            {assignment.notes || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Driver Holds */}
              {holds.length > 0 && (
                <div className="bg-white rounded-lg border">
                  <div className="p-4 border-b">
                    <h2 className="text-lg font-semibold flex items-center">
                      🚨 Driver Holds
                    </h2>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Driver</th>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Reason</th>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Status</th>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Created</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {holds.map(hold => (
                          <tr key={hold.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <div className="font-medium">
                                {driverById.get(hold.driver_id)?.name || `Driver ${hold.driver_id}`}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm">{hold.reason}</td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                                hold.status === 'ACTIVE' 
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-green-100 text-green-800'
                              }`}>
                                {hold.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {new Date(hold.created_at).toLocaleDateString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Transactions Tab */}
          {activeTab === 'transactions' && (
            <div className="space-y-6">
              <div className="bg-white rounded-lg border">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold flex items-center">
                    📜 Stock Transaction History & Audit Trail
                  </h2>
                  <p className="text-sm text-gray-600 mt-1">
                    All stock movements are logged for accountability and audit purposes
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Date</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Lorry</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Action</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">UID</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Admin User</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {stockTransactions.map(transaction => (
                        <tr key={transaction.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm">
                            {new Date(transaction.transaction_date).toLocaleString()}
                          </td>
                          <td className="px-4 py-3">
                            <span className="font-mono font-medium">{transaction.lorry_id}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                              transaction.action === 'LOAD' || transaction.action === 'COLLECTION'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {transaction.action}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="font-mono text-sm">{transaction.uid}</span>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {transaction.admin_user}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {transaction.notes || '-'}
                          </td>
                        </tr>
                      ))}
                      {stockTransactions.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                            No stock transactions recorded yet
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

(LorryManagementPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
export default LorryManagementPage;