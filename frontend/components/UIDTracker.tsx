import React from 'react';
import { getOrderUIDs, getInventoryConfig, scanUID, resolveSKU } from '@/lib/api';
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
  
  // Form state
  const [newUID, setNewUID] = React.useState('');
  const [newAction, setNewAction] = React.useState<'ISSUE' | 'RETURN'>('ISSUE');
  const [newNotes, setNewNotes] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  const loadConfig = React.useCallback(async () => {
    try {
      const configData = await getInventoryConfig();
      setConfig(configData);
    } catch (e: any) {
      console.error('Failed to load inventory config:', e);
      // If config loading fails, assume disabled
      setConfig({
        uid_inventory_enabled: false,
        uid_scan_required_after_pod: false,
        inventory_mode: 'off'
      });
    }
  }, []);

  const loadUIDs = React.useCallback(async () => {
    if (!config?.uid_inventory_enabled) return;
    
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

  const handleAddUID = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUID.trim()) return;

    setSubmitting(true);
    setError('');

    try {
      await scanUID({
        order_id: orderId,
        action: newAction,
        uid: newUID.trim().toUpperCase(),
        notes: newNotes || undefined
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

  // Don't render if inventory system is disabled
  if (!config || !config.uid_inventory_enabled) {
    return null;
  }

  return (
    <Card>
      <div className="flex justify-between items-center mb-4">
        <h3 className="m-0">UID Tracking</h3>
        <div className="flex gap-2">
          <span className={`badge ${config.inventory_mode === 'required' ? 'text-red-600' : 'text-blue-600'}`}>
            {config.inventory_mode === 'required' ? 'Required' : 'Optional'}
          </span>
          <button 
            className="btn secondary text-sm"
            onClick={() => setShowAddForm(!showAddForm)}
            disabled={loading}
          >
            {showAddForm ? 'Cancel' : 'Add UID'}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-red-600 bg-red-50 p-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {showAddForm && (
        <form onSubmit={handleAddUID} className="bg-gray-50 p-4 rounded mb-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">UID</label>
              <input
                type="text"
                className="input"
                value={newUID}
                onChange={(e) => setNewUID(e.target.value)}
                placeholder="Enter UID (e.g., AA123456789)"
                required
                disabled={submitting}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Action</label>
              <select
                className="input"
                value={newAction}
                onChange={(e) => setNewAction(e.target.value as 'ISSUE' | 'RETURN')}
                disabled={submitting}
              >
                <option value="ISSUE">Issue (Delivery)</option>
                <option value="RETURN">Return (Pickup)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Notes (Optional)</label>
              <input
                type="text"
                className="input"
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                placeholder="Optional notes"
                disabled={submitting}
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button 
              type="submit" 
              className="btn"
              disabled={submitting || !newUID.trim()}
            >
              {submitting ? 'Adding...' : 'Add UID'}
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
      )}

      {loading && (
        <div className="text-center py-4">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <p className="text-sm text-gray-500 mt-2">Loading UID data...</p>
        </div>
      )}

      {!loading && (
        <>
          {uids.length > 0 ? (
            <div className="space-y-3">
              <div className="text-sm text-gray-600 mb-3">
                Total: {uids.length} UIDs • 
                Issued: {uids.filter(u => u.action === 'ISSUE').length} • 
                Returned: {uids.filter(u => u.action === 'RETURN').length}
              </div>
              
              <div className="overflow-x-auto">
                <table className="table">
                  <thead>
                    <tr>
                      <th>UID</th>
                      <th>Action</th>
                      <th>SKU</th>
                      <th>Scanned</th>
                      <th>Driver</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {uids.map((uid) => (
                      <tr key={uid.id}>
                        <td>
                          <code className="bg-gray-100 px-2 py-1 rounded text-sm">
                            {uid.uid}
                          </code>
                        </td>
                        <td>
                          <span className={`badge ${uid.action === 'ISSUE' ? 'text-green-600' : 'text-orange-600'}`}>
                            {uid.action === 'ISSUE' ? 'Issued' : 'Returned'}
                          </span>
                        </td>
                        <td>
                          {uid.sku_name ? (
                            <div>
                              <div className="font-medium text-sm">{uid.sku_name}</div>
                              <div className="text-xs text-gray-500">ID: {uid.sku_id}</div>
                            </div>
                          ) : (
                            <span className="text-gray-400">Unknown SKU</span>
                          )}
                        </td>
                        <td>
                          <div className="text-sm">
                            {new Date(uid.scanned_at).toLocaleDateString()}
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(uid.scanned_at).toLocaleTimeString()}
                          </div>
                        </td>
                        <td>
                          {uid.driver_name ? (
                            <span className="text-sm">{uid.driver_name}</span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td>
                          {uid.notes ? (
                            <span className="text-sm">{uid.notes}</span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">📦</div>
              <div className="font-medium">No UIDs tracked</div>
              <div className="text-sm">
                {config.inventory_mode === 'required' 
                  ? 'UIDs are required for this order but none have been scanned yet.'
                  : 'No UIDs have been scanned for this order yet.'
                }
              </div>
              {!showAddForm && (
                <button 
                  className="btn mt-3"
                  onClick={() => setShowAddForm(true)}
                >
                  Add First UID
                </button>
              )}
            </div>
          )}
        </>
      )}
    </Card>
  );
}