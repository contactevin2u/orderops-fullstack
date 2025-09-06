import React, { useState, useEffect } from 'react';
import PageHeader from '@/components/PageHeader';
import Card from '@/components/Card';
import { 
  getDriverStockStatus,
  getLorryStock,
  uploadLorryStock,
  listDrivers,
  getInventoryConfig,
  getAllSKUs
} from '@/lib/api';

interface Driver {
  id: number;
  name?: string;
  phone?: string;
}

interface StockItem {
  sku_name: string;
  count: number;
  items: Array<{
    uid: string;
    serial?: string;
    type: string;
    copy_number?: number;
  }>;
}

interface LorryStockItem {
  sku_id: number;
  sku_code: string;
  sku_name: string;
  qty_counted: number;
  uploaded_at: string;
}

interface StockUploadItem {
  sku_id: number;
  counted_quantity: number;
}

export default function DriverStockPage() {
  const [config, setConfig] = useState<any>(null);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [skus, setSKUs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [stockLoading, setStockLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Current view state
  const [selectedDriver, setSelectedDriver] = useState<string>('');
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [viewMode, setViewMode] = useState<'current' | 'count'>('current');

  // Data state
  const [currentStock, setCurrentStock] = useState<{
    driver_id: number;
    stock_items: StockItem[];
    total_items: number;
  } | null>(null);
  
  const [lorryStock, setLorryStock] = useState<{
    date: string;
    lines: LorryStockItem[];
  } | null>(null);

  // Stock count form
  const [stockCounts, setStockCounts] = useState<Record<number, number>>({});
  const [showCountForm, setShowCountForm] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configData, driverData, skuData] = await Promise.all([
        getInventoryConfig(),
        listDrivers(),
        getAllSKUs()
      ]);
      
      setConfig(configData);
      setDrivers(driverData);
      setSKUs(skuData.filter((sku: any) => sku.is_active));
      
      if (driverData.length > 0) {
        setSelectedDriver(String(driverData[0].id));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadCurrentStock = async () => {
    if (!selectedDriver) return;

    try {
      setStockLoading(true);
      const response = await getDriverStockStatus(parseInt(selectedDriver));
      setCurrentStock(response);
    } catch (err: any) {
      setError(err.message || 'Failed to load current stock');
      setCurrentStock(null);
    } finally {
      setStockLoading(false);
    }
  };

  const loadLorryStock = async () => {
    if (!selectedDriver || !selectedDate) return;

    try {
      setStockLoading(true);
      const response = await getLorryStock(parseInt(selectedDriver), selectedDate);
      setLorryStock({ date: response.date, lines: response.items.map(item => ({
        sku_id: item.sku_id,
        sku_name: item.sku_name,
        expected_count: item.expected_count,
        scanned_count: item.scanned_count,
        variance: item.variance
      })) });
    } catch (err: any) {
      console.log('No lorry stock data for this date:', err);
      setLorryStock({ date: selectedDate, lines: [] });
    } finally {
      setStockLoading(false);
    }
  };

  const handleStockCountSubmit = async () => {
    if (!selectedDriver || !selectedDate) return;

    const stockData: StockUploadItem[] = Object.entries(stockCounts)
      .filter(([_, count]) => count > 0)
      .map(([skuId, count]) => ({
        sku_id: parseInt(skuId),
        counted_quantity: count
      }));

    if (stockData.length === 0) {
      setError('Please enter stock counts for at least one SKU');
      return;
    }

    try {
      setUploading(true);
      setError('');
      setSuccess('');

      const response = await uploadLorryStock({
        date: selectedDate,
        stock_data: stockData
      });

      if (response.success) {
        setSuccess(`Successfully uploaded stock count for ${response.items_processed} SKUs`);
        setStockCounts({});
        setShowCountForm(false);
        await loadLorryStock();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload stock count');
    } finally {
      setUploading(false);
    }
  };

  const initializeCountForm = () => {
    // Initialize with existing counts or zeros
    const initialCounts: Record<number, number> = {};
    
    if (lorryStock) {
      lorryStock.lines.forEach(line => {
        initialCounts[line.sku_id] = line.qty_counted;
      });
    }

    // Add any SKUs that might be with the driver but not yet counted
    if (currentStock) {
      currentStock.stock_items.forEach(item => {
        const sku = skus.find(s => s.name === item.sku_name);
        if (sku && !(sku.id in initialCounts)) {
          initialCounts[sku.id] = item.count;
        }
      });
    }

    setStockCounts(initialCounts);
    setShowCountForm(true);
  };

  const updateStockCount = (skuId: number, count: number) => {
    setStockCounts(prev => ({
      ...prev,
      [skuId]: Math.max(0, count)
    }));
  };

  const getDriverName = (driverId: string) => {
    const driver = drivers.find(d => d.id === parseInt(driverId));
    return driver?.name || `Driver ${driverId}`;
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedDriver) {
      loadCurrentStock();
      if (viewMode === 'count') {
        loadLorryStock();
      }
    }
  }, [selectedDriver, selectedDate, viewMode]);

  if (loading) {
    return <Card>Loading Driver Stock Management...</Card>;
  }

  if (!config?.uid_inventory_enabled) {
    return (
      <div>
        <PageHeader title="Driver Stock Management" />
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🚫</div>
            <h2 className="text-xl font-semibold mb-2">UID System Disabled</h2>
            <p className="text-gray-600">
              The UID inventory system is currently disabled. Please contact your administrator.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Driver Stock Management" />
      
      {/* Controls */}
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Driver</label>
            <select
              className="input"
              value={selectedDriver}
              onChange={(e) => setSelectedDriver(e.target.value)}
            >
              <option value="">Select Driver</option>
              {drivers.map((driver) => (
                <option key={driver.id} value={driver.id}>
                  {driver.name || `Driver ${driver.id}`}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">View Mode</label>
            <div className="flex gap-2">
              <button
                className={`px-3 py-2 text-sm rounded ${
                  viewMode === 'current' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 text-gray-700'
                }`}
                onClick={() => setViewMode('current')}
              >
                Current Stock
              </button>
              <button
                className={`px-3 py-2 text-sm rounded ${
                  viewMode === 'count' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 text-gray-700'
                }`}
                onClick={() => setViewMode('count')}
              >
                Daily Count
              </button>
            </div>
          </div>

          {viewMode === 'count' && (
            <div>
              <label className="block text-sm font-medium mb-1">Date</label>
              <input
                type="date"
                className="input"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
            </div>
          )}

          {viewMode === 'count' && selectedDriver && (
            <div className="flex items-end">
              <button
                className="btn"
                onClick={initializeCountForm}
                disabled={stockLoading}
              >
                {lorryStock?.lines.length ? 'Update Count' : 'New Count'}
              </button>
            </div>
          )}
        </div>
      </Card>

      {selectedDriver && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Current Stock */}
          {viewMode === 'current' && (
            <Card>
              <h3 className="text-lg font-semibold mb-4">
                Current Stock - {getDriverName(selectedDriver)}
              </h3>
              
              {stockLoading ? (
                <div className="text-center py-8">Loading stock data...</div>
              ) : currentStock ? (
                <div className="space-y-4">
                  <div className="bg-blue-50 p-4 rounded">
                    <div className="text-2xl font-bold text-blue-600">
                      {currentStock.total_items}
                    </div>
                    <div className="text-blue-800">Total Items with Driver</div>
                  </div>

                  {currentStock.stock_items.length > 0 ? (
                    <div className="space-y-3">
                      {currentStock.stock_items.map((item, index) => (
                        <div key={index} className="border rounded-lg p-4">
                          <div className="flex justify-between items-center mb-2">
                            <div className="font-medium">{item.sku_name}</div>
                            <div className="text-lg font-bold text-gray-900">
                              {item.count}
                            </div>
                          </div>
                          
                          <div className="space-y-1">
                            {item.items.slice(0, 3).map((uid, uidIndex) => (
                              <div key={uidIndex} className="text-xs text-gray-600 font-mono">
                                {uid.uid}
                                {uid.serial && ` (Serial: ${uid.serial})`}
                                {uid.copy_number && ` (Copy ${uid.copy_number})`}
                              </div>
                            ))}
                            {item.items.length > 3 && (
                              <div className="text-xs text-gray-500">
                                +{item.items.length - 3} more items
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <div className="text-3xl mb-2">📦</div>
                      <p>No items currently with this driver</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-3xl mb-2">❓</div>
                  <p>Unable to load stock data</p>
                </div>
              )}
            </Card>
          )}

          {/* Daily Count */}
          {viewMode === 'count' && (
            <Card>
              <h3 className="text-lg font-semibold mb-4">
                Daily Count - {getDriverName(selectedDriver)} ({selectedDate})
              </h3>
              
              {stockLoading ? (
                <div className="text-center py-8">Loading count data...</div>
              ) : lorryStock && lorryStock.lines.length > 0 ? (
                <div className="space-y-4">
                  <div className="bg-green-50 p-4 rounded">
                    <div className="text-2xl font-bold text-green-600">
                      {lorryStock.lines.length}
                    </div>
                    <div className="text-green-800">SKUs Counted</div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="table text-sm">
                      <thead>
                        <tr>
                          <th>SKU</th>
                          <th>Count</th>
                          <th>Uploaded</th>
                        </tr>
                      </thead>
                      <tbody>
                        {lorryStock.lines.map((line) => (
                          <tr key={line.sku_id}>
                            <td>
                              <div className="font-medium">{line.sku_name}</div>
                              <div className="text-xs text-gray-500">{line.sku_code}</div>
                            </td>
                            <td className="text-lg font-bold">
                              {line.qty_counted}
                            </td>
                            <td className="text-xs">
                              {new Date(line.uploaded_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-3xl mb-2">📋</div>
                  <p>No count data for this date</p>
                  <p className="text-xs">Click &quot;New Count&quot; to start counting</p>
                </div>
              )}
            </Card>
          )}

          {/* Additional Info */}
          <Card>
            <h3 className="text-lg font-semibold mb-4">Stock Information</h3>
            
            <div className="space-y-4 text-sm">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Current Stock View</h4>
                <p className="text-gray-600">
                  Shows items currently with the selected driver based on real-time UID scanning data. 
                  This reflects items that have been loaded out but not yet delivered or returned.
                </p>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-2">Daily Count View</h4>
                <p className="text-gray-600">
                  Shows manually counted stock for a specific date. Drivers can upload their 
                  physical stock counts for reconciliation and variance tracking.
                </p>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-2">Usage Tips</h4>
                <ul className="text-gray-600 space-y-1">
                  <li>• Use &quot;Current Stock&quot; to see real-time UID-tracked items</li>
                  <li>• Use &quot;Daily Count&quot; for manual inventory reconciliation</li>
                  <li>• Compare both views to identify discrepancies</li>
                  <li>• Upload counts at end of each day for accurate tracking</li>
                </ul>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Stock Count Form Modal */}
      {showCountForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">
                Stock Count - {getDriverName(selectedDriver)} ({selectedDate})
              </h3>
              <button
                className="text-gray-500 hover:text-gray-700"
                onClick={() => setShowCountForm(false)}
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Enter the physical count for each SKU. Leave empty or 0 for items not present.
              </p>

              <div className="grid grid-cols-1 gap-3">
                {skus.map((sku) => (
                  <div key={sku.id} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex-1">
                      <div className="font-medium">{sku.name}</div>
                      <div className="text-xs text-gray-500">{sku.code}</div>
                    </div>
                    <div className="w-20">
                      <input
                        type="number"
                        min="0"
                        className="input text-center"
                        value={stockCounts[sku.id] || 0}
                        onChange={(e) => updateStockCount(sku.id, parseInt(e.target.value) || 0)}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  className="btn secondary"
                  onClick={() => setShowCountForm(false)}
                >
                  Cancel
                </button>
                <button
                  className="btn"
                  onClick={handleStockCountSubmit}
                  disabled={uploading}
                >
                  {uploading ? 'Uploading...' : 'Upload Count'}
                </button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Messages */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded z-50">
          {error}
          <button 
            className="ml-2 text-red-500 hover:text-red-700"
            onClick={() => setError('')}
          >
            ✕
          </button>
        </div>
      )}
      
      {success && (
        <div className="fixed top-4 right-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded z-50">
          {success}
          <button 
            className="ml-2 text-green-500 hover:text-green-700"
            onClick={() => setSuccess('')}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}