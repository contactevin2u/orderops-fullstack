// import { useSession } from 'next-auth/react';
import { useEffect, useState, useMemo } from 'react';
import { request } from '../../utils/api';
// import AdminLayout from '@/components/Layout/AdminLayout';

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
  const [activeTab, setActiveTab] = useState<'dashboard' | 'assignments' | 'scanner' | 'transactions'>('dashboard');

  // Data states
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [holds, setHolds] = useState<Hold[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [lorryInventories, setLorryInventories] = useState<LorryInventory[]>([]);
  const [stockTransactions, setStockTransactions] = useState<StockTransaction[]>([]);

  // Scanner states
  const [selectedLorry, setSelectedLorry] = useState<string>('');
  const [scanMode, setScanMode] = useState<'load' | 'unload'>('load');
  const [scanInput, setScanInput] = useState('');
  const [scannedUIDs, setScannedUIDs] = useState<string[]>([]);
  const [scanNotes, setScanNotes] = useState('');
  const [scanLoading, setScanLoading] = useState(false);

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
        const [A, H, D, I, T] = await Promise.allSettled([
          api<Assignment[]>('/lorry-management/assignments'),
          api<Hold[]>('/lorry-management/holds'),
          api<Driver[]>('/drivers'),
          api<{ lorries: LorryInventory[] }>('/lorry-management/stock/summary'),
          api<StockTransaction[]>('/lorry-management/stock/transactions?limit=50'),
        ]);

        if (!cancelled) {
          setAssignments(A.status === 'fulfilled' ? asArray<Assignment>(A.value) : []);
          setHolds(H.status === 'fulfilled' ? asArray<Hold>(H.value) : []);
          setDrivers(D.status === 'fulfilled' ? asArray<Driver>(D.value) : []);
          setLorryInventories(I.status === 'fulfilled' ? (I.value as any)?.lorries || [] : []);
          setStockTransactions(T.status === 'fulfilled' ? asArray<StockTransaction>(T.value) : []);

          if ([A, H, D, I, T].some(r => r.status === 'rejected')) {
            const reasons = [A, H, D, I, T]
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
                { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
                { id: 'scanner', label: '📱 Stock Scanner', icon: '📱' },
                { id: 'assignments', label: '📋 Assignments', icon: '📋' },
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
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{lorryInventories.length}</div>
                  <div className="text-blue-800 font-medium">Active Lorries</div>
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

// (LorryManagementPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
export default LorryManagementPage;