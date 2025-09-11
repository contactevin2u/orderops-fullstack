import React from 'react';
import { getOrderUIDs, getInventoryConfig, scanUID, resolveSKU, getUIDLedgerHistory, recordUIDScan } from '@/lib/api';
import Card from '@/components/Card';

interface UIDTrackerProps {
  orderId: number;
  orderStatus?: string;
}

interface UIDEntry {
  id: number;
  uid: string;
  action: 'ISSUE' | 'RETURN';
  sku_id?: number;
  sku_name?: string;
  scanned_at: string;
  driver_name?: string;
  notes?: string;
}

interface LedgerEntry {
  id: number;
  uid: string;
  action: string;
  scanned_at: string;
  scanner: {
    type: 'admin' | 'driver' | 'manual';
    id?: number;
    name: string;
  };
  source: string;
  order_id?: number;
  order_reference?: string;
  customer_name?: string;
  lorry_id?: string;
  location_notes?: string;
  notes?: string;
  recorded_at: string;
}

interface InventoryConfig {
  uid_inventory_enabled: boolean;
  uid_scan_required_after_pod: boolean;
  inventory_mode: string;
}

export default function UIDTracker({ orderId, orderStatus }: UIDTrackerProps) {
  const [config, setConfig] = React.useState<InventoryConfig | null>(null);
  const [uids, setUIDs] = React.useState<UIDEntry[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string>('');
  const [showAddForm, setShowAddForm] = React.useState(false);
  const [activeView, setActiveView] = React.useState<'summary' | 'detailed'>('summary');
  
  // Form state
  const [newUID, setNewUID] = React.useState('');
  const [newAction, setNewAction] = React.useState<string>('ISSUE');
  const [newNotes, setNewNotes] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);
  
  // Ledger state
  const [selectedUID, setSelectedUID] = React.useState<string | null>(null);
  const [ledgerHistory, setLedgerHistory] = React.useState<LedgerEntry[]>([]);
  const [loadingLedger, setLoadingLedger] = React.useState(false);

  const loadConfig = React.useCallback(async () => {
    try {
      const configData = await getInventoryConfig();
      setConfig(configData);
    } catch (e: any) {
      console.error('Failed to load inventory config:', e);
      // If config loading fails, assume enabled (fallback to safe defaults)
      setConfig({
        uid_inventory_enabled: true,
        uid_scan_required_after_pod: true,
        inventory_mode: 'required'
      });
    }
  }, []);

  const loadUIDs = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await getOrderUIDs(orderId);
      setUIDs(data.uids || []);
      setError('');
    } catch (e: any) {
      setError(e.message || 'Failed to load UID data');
      setUIDs([]);
    } finally {
      setLoading(false);
    }
  }, [orderId, config]);

  React.useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  React.useEffect(() => {
    if (config) {
      loadUIDs();
    }
  }, [config, loadUIDs]);

  const loadLedgerHistory = React.useCallback(async (uid: string) => {
    setLoadingLedger(true);
    try {
      const data = await getUIDLedgerHistory(uid);
      setLedgerHistory(data.history || []);
    } catch (e: any) {
      console.error(`Failed to load ledger history for ${uid}:`, e);
    } finally {
      setLoadingLedger(false);
    }
  }, []);

  const handleUIDClick = (uid: string) => {
    setSelectedUID(uid);
    loadLedgerHistory(uid);
  };

  const handleAddUID = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUID.trim()) return;

    setSubmitting(true);
    setError('');

    try {
      // Use new ledger-based scan recording
      await recordUIDScan(newUID.trim().toUpperCase(), {
        action: newAction,
        order_id: orderId,
        notes: newNotes || undefined,
        source: 'ADMIN_MANUAL'
      });

      // Reload UIDs
      await loadUIDs();
      
      // Reset form
      setNewUID('');
      setNewNotes('');
      setShowAddForm(false);
    } catch (e: any) {
      setError(e.message || 'Failed to add UID');
    } finally {
      setSubmitting(false);
    }
  };


  const getActionBadgeColor = (action: string) => {
    switch (action) {
      case 'ISSUE':
      case 'DELIVER':
        return 'bg-green-100 text-green-800';
      case 'RETURN':
      case 'LOAD_IN':
        return 'bg-orange-100 text-orange-800';
      case 'LOAD_OUT':
        return 'bg-blue-100 text-blue-800';
      case 'REPAIR':
        return 'bg-red-100 text-red-800';
      case 'SWAP':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'ADMIN_MANUAL':
        return 'bg-blue-100 text-blue-800';
      case 'DRIVER_SYNC':
        return 'bg-green-100 text-green-800';
      case 'ORDER_OPERATION':
        return 'bg-purple-100 text-purple-800';
      case 'INVENTORY_AUDIT':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <h3 className="m-0 text-lg font-semibold">UID Tracking & Ledger</h3>
          <div className="flex gap-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${config?.inventory_mode === 'required' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>
              {config?.inventory_mode === 'required' ? 'Required' : 'Optional'}
            </span>
          </div>
        </div>
        
        <div className="flex gap-2">
          <div className="flex rounded-lg overflow-hidden border border-gray-200">
            <button
              className={`px-3 py-1 text-sm font-medium transition-colors ${
                activeView === 'summary' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setActiveView('summary')}
            >
              Summary
            </button>
            <button
              className={`px-3 py-1 text-sm font-medium transition-colors ${
                activeView === 'detailed' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
              onClick={() => setActiveView('detailed')}
            >
              Detailed View
            </button>
          </div>
          
          <button 
            className="btn secondary text-sm"
            onClick={() => setShowAddForm(!showAddForm)}
            disabled={loading}
          >
            {showAddForm ? 'Cancel' : 'Record Scan'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg mb-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-red-500">⚠️</span>
            {error}
          </div>
        </div>
      )}

      {showAddForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6">
          <h4 className="text-sm font-semibold mb-4 text-gray-900">Record New UID Scan</h4>
          <form onSubmit={handleAddUID}>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">UID</label>
                <input
                  type="text"
                  className="input w-full"
                  value={newUID}
                  onChange={(e) => setNewUID(e.target.value)}
                  placeholder="Enter UID (e.g., AA123456789)"
                  required
                  disabled={submitting}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Action</label>
                <select
                  className="input w-full"
                  value={newAction}
                  onChange={(e) => setNewAction(e.target.value)}
                  disabled={submitting}
                >
                  <option value="ISSUE">Issue (Delivery)</option>
                  <option value="RETURN">Return (Collection)</option>
                  <option value="LOAD_OUT">Load Out</option>
                  <option value="DELIVER">Deliver</option>
                  <option value="LOAD_IN">Load In</option>
                  <option value="REPAIR">Repair</option>
                  <option value="SWAP">Swap</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Notes (Optional)</label>
                <input
                  type="text"
                  className="input w-full"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="Optional notes"
                  disabled={submitting}
                />
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button 
                type="submit" 
                className="btn bg-blue-600 text-white hover:bg-blue-700"
                disabled={submitting || !newUID.trim()}
              >
                {submitting ? (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Recording...
                  </div>
                ) : (
                  'Record Scan'
                )}
              </button>
              <button 
                type="button" 
                className="btn secondary"
                onClick={() => setShowAddForm(false)}
                disabled={submitting}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="text-sm text-gray-500 mt-3">Loading UID data...</p>
        </div>
      )}

      {!loading && (
        <>
          {activeView === 'summary' ? (
            <>
              {uids.length > 0 ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-900">{uids.length}</div>
                      <div className="text-sm text-gray-600">Total UIDs</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{uids.filter(u => u.action === 'ISSUE').length}</div>
                      <div className="text-sm text-gray-600">Issued</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">{uids.filter(u => u.action === 'RETURN').length}</div>
                      <div className="text-sm text-gray-600">Returned</div>
                    </div>
                  </div>
                  
                  <div className="overflow-x-auto">
                    <table className="table w-full">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="text-left font-medium text-gray-700">UID</th>
                          <th className="text-left font-medium text-gray-700">Action</th>
                          <th className="text-left font-medium text-gray-700">SKU</th>
                          <th className="text-left font-medium text-gray-700">Scanned</th>
                          <th className="text-left font-medium text-gray-700">Driver</th>
                          <th className="text-left font-medium text-gray-700">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {uids.map((uid) => (
                          <tr key={uid.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td>
                              <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">
                                {uid.uid}
                              </code>
                            </td>
                            <td>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionBadgeColor(uid.action)}`}>
                                {uid.action === 'ISSUE' ? 'Issued' : 'Returned'}
                              </span>
                            </td>
                            <td>
                              {uid.sku_name ? (
                                <div>
                                  <div className="font-medium text-sm text-gray-900">{uid.sku_name}</div>
                                  <div className="text-xs text-gray-500">ID: {uid.sku_id}</div>
                                </div>
                              ) : (
                                <span className="text-gray-400">Unknown SKU</span>
                              )}
                            </td>
                            <td>
                              <div className="text-sm text-gray-900">
                                {new Date(uid.scanned_at).toLocaleDateString()}
                              </div>
                              <div className="text-xs text-gray-500">
                                {new Date(uid.scanned_at).toLocaleTimeString()}
                              </div>
                            </td>
                            <td>
                              {uid.driver_name ? (
                                <span className="text-sm text-gray-900">{uid.driver_name}</span>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                            <td>
                              <button
                                onClick={() => handleUIDClick(uid.uid)}
                                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                              >
                                View History
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-6xl mb-4">📦</div>
                  <div className="font-medium text-lg mb-2">No UIDs tracked</div>
                  <div className="text-sm mb-6">
                    {config?.inventory_mode === 'required' 
                      ? 'UIDs are required for this order but none have been scanned yet.'
                      : 'No UIDs have been scanned for this order yet.'
                    }
                  </div>
                  {!showAddForm && (
                    <button 
                      className="btn bg-blue-600 text-white hover:bg-blue-700"
                      onClick={() => setShowAddForm(true)}
                    >
                      Record First Scan
                    </button>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="space-y-6">
              {selectedUID ? (
                <div>
                  <div className="flex items-center gap-4 mb-4">
                    <button
                      onClick={() => setSelectedUID(null)}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      ← Back to list
                    </button>
                    <h4 className="text-lg font-semibold">
                      Ledger History for <code className="bg-gray-100 px-2 py-1 rounded">{selectedUID}</code>
                    </h4>
                  </div>
                  
                  {loadingLedger ? (
                    <div className="text-center py-8">
                      <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                      <p className="text-sm text-gray-500 mt-2">Loading ledger history...</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {ledgerHistory.map((entry) => (
                        <div key={entry.id} className="border border-gray-200 rounded-lg p-4 bg-white">
                          <div className="flex justify-between items-start mb-3">
                            <div className="flex items-center gap-3">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionBadgeColor(entry.action)}`}>
                                {entry.action}
                              </span>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSourceBadgeColor(entry.source)}`}>
                                {entry.source.replace('_', ' ')}
                              </span>
                            </div>
                            <div className="text-right text-sm text-gray-500">
                              <div>{new Date(entry.scanned_at).toLocaleString()}</div>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                            <div>
                              <div className="font-medium text-gray-900 mb-1">Scanner</div>
                              <div className="text-gray-600">
                                {entry.scanner.name} 
                                <span className="text-gray-400 ml-1">({entry.scanner.type})</span>
                              </div>
                            </div>
                            
                            {entry.order_reference && (
                              <div>
                                <div className="font-medium text-gray-900 mb-1">Order</div>
                                <div className="text-gray-600">{entry.order_reference}</div>
                              </div>
                            )}
                            
                            {entry.customer_name && (
                              <div>
                                <div className="font-medium text-gray-900 mb-1">Customer</div>
                                <div className="text-gray-600">{entry.customer_name}</div>
                              </div>
                            )}
                            
                            {entry.lorry_id && (
                              <div>
                                <div className="font-medium text-gray-900 mb-1">Lorry</div>
                                <div className="text-gray-600">{entry.lorry_id}</div>
                              </div>
                            )}
                          </div>
                          
                          {entry.notes && (
                            <div className="mt-3 pt-3 border-t border-gray-100">
                              <div className="font-medium text-gray-900 mb-1">Notes</div>
                              <div className="text-gray-600 text-sm">{entry.notes}</div>
                            </div>
                          )}
                        </div>
                      ))}
                      
                      {ledgerHistory.length === 0 && (
                        <div className="text-center py-8 text-gray-500">
                          <div className="text-4xl mb-2">📋</div>
                          <div className="font-medium">No ledger entries</div>
                          <div className="text-sm">No scan history found for this UID.</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <h4 className="text-lg font-semibold mb-4">Select UID to View Detailed History</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {uids.map((uid) => (
                      <button
                        key={uid.id}
                        onClick={() => handleUIDClick(uid.uid)}
                        className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
                      >
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono block mb-2">
                          {uid.uid}
                        </code>
                        <div className="text-sm text-gray-600">
                          {uid.sku_name || 'Unknown SKU'}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Last: {new Date(uid.scanned_at).toLocaleDateString()}
                        </div>
                      </button>
                    ))}
                  </div>
                  
                  {uids.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      <div className="text-4xl mb-2">📦</div>
                      <div className="font-medium">No UIDs to display</div>
                      <div className="text-sm">Record some UID scans first to view detailed history.</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </Card>
  );
}