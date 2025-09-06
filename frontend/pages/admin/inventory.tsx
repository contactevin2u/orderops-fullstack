import React from 'react';
import Link from 'next/link';
import PageHeader from '@/components/PageHeader';
import Card from '@/components/Card';
import { 
  getInventoryConfig, 
  getLorryStock, 
  resolveSKU, 
  addSKUAlias, 
  listDrivers 
} from '@/lib/api';

export default function InventoryPage() {
  const [config, setConfig] = React.useState<any>(null);
  const [drivers, setDrivers] = React.useState<any[]>([]);
  const [selectedDriver, setSelectedDriver] = React.useState<string>('');
  const [selectedDate, setSelectedDate] = React.useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [stockData, setStockData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string>('');

  // SKU Resolution
  const [skuSearchTerm, setSKUSearchTerm] = React.useState('');
  const [skuResults, setSKUResults] = React.useState<any[]>([]);
  const [skuLoading, setSKULoading] = React.useState(false);

  const loadConfig = React.useCallback(async () => {
    try {
      const configData = await getInventoryConfig();
      setConfig(configData);
    } catch (e: any) {
      console.error('Failed to load inventory config:', e);
    }
  }, []);

  const loadDrivers = React.useCallback(async () => {
    try {
      const driversData = await listDrivers();
      setDrivers(driversData);
      if (driversData.length > 0) {
        setSelectedDriver(String(driversData[0].id));
      }
    } catch (e: any) {
      console.error('Failed to load drivers:', e);
    }
  }, []);

  const loadStock = React.useCallback(async () => {
    if (!selectedDriver) return;

    setLoading(true);
    setError('');
    
    try {
      const stockData = await getLorryStock(Number(selectedDriver), selectedDate);
      setStockData(stockData);
    } catch (e: any) {
      setError(e.message || 'Failed to load stock data');
      setStockData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedDriver, selectedDate, config]);

  const searchSKU = React.useCallback(async () => {
    if (!skuSearchTerm.trim()) return;

    setSKULoading(true);
    try {
      const results = await resolveSKU(skuSearchTerm);
      setSKUResults(results.matches || []);
    } catch (e: any) {
      console.error('SKU search failed:', e);
      setSKUResults([]);
    } finally {
      setSKULoading(false);
    }
  }, [skuSearchTerm]);

  const addAlias = async (skuId: number, alias: string) => {
    try {
      await addSKUAlias(skuId, alias);
      alert('Alias added successfully');
      // Clear search to refresh
      setSKUResults([]);
      setSKUSearchTerm('');
    } catch (e: any) {
      alert(`Failed to add alias: ${e.message}`);
    }
  };

  React.useEffect(() => {
    loadConfig();
    loadDrivers();
  }, [loadConfig, loadDrivers]);

  React.useEffect(() => {
    loadStock();
  }, [loadStock]);

  if (!config) {
    return <Card>Loading inventory configuration...</Card>;
  }


  return (
    <div>
      <PageHeader title="Inventory Management" />
      <div className="flex items-center gap-2 text-sm mb-4">
        <span className={`px-2 py-1 rounded ${config.inventory_mode === 'required' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}>
          {config.inventory_mode === 'required' ? 'Required' : 'Optional'}
        </span>
        <span className="text-gray-500">Mode</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stock Management */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Driver Stock Levels</h3>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
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
                <label className="block text-sm font-medium mb-1">Date</label>
                <input
                  type="date"
                  className="input"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
              </div>
            </div>

            <button
              className="btn w-full"
              onClick={loadStock}
              disabled={loading || !selectedDriver}
            >
              {loading ? 'Loading...' : 'Load Stock Data'}
            </button>

            {error && (
              <div className="text-red-600 bg-red-50 p-3 rounded text-sm">
                {error}
              </div>
            )}

            {stockData && (
              <div className="space-y-4">
                {/* Summary */}
                <div className="bg-blue-50 p-4 rounded">
                  <h4 className="font-medium mb-2">Stock Summary</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="font-medium text-lg">{stockData.total_expected}</div>
                      <div className="text-gray-600">Expected</div>
                    </div>
                    {stockData.total_scanned !== null && (
                      <div>
                        <div className="font-medium text-lg">{stockData.total_scanned}</div>
                        <div className="text-gray-600">Scanned</div>
                      </div>
                    )}
                    {stockData.total_variance !== null && (
                      <div>
                        <div className={`font-medium text-lg ${stockData.total_variance > 0 ? 'text-green-600' : stockData.total_variance < 0 ? 'text-red-600' : ''}`}>
                          {stockData.total_variance > 0 ? '+' : ''}{stockData.total_variance}
                        </div>
                        <div className="text-gray-600">Variance</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Items */}
                {stockData.items && stockData.items.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Stock Items ({stockData.items.length})</h4>
                    <div className="overflow-x-auto">
                      <table className="table text-sm">
                        <thead>
                          <tr>
                            <th>SKU</th>
                            <th>Expected</th>
                            <th>Scanned</th>
                            <th>Variance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {stockData.items.map((item: any, index: number) => (
                            <tr key={index}>
                              <td>
                                <div className="font-medium">{item.sku_name}</div>
                                <div className="text-xs text-gray-500">ID: {item.sku_id}</div>
                              </td>
                              <td>{item.expected_count}</td>
                              <td>{item.scanned_count !== null ? item.scanned_count : '-'}</td>
                              <td>
                                {item.variance !== null && (
                                  <span className={`${item.variance > 0 ? 'text-green-600' : item.variance < 0 ? 'text-red-600' : ''}`}>
                                    {item.variance > 0 ? '+' : ''}{item.variance}
                                  </span>
                                )}
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
          </div>
        </Card>

        {/* SKU Management */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">SKU Management</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Search SKU by Name</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input flex-1"
                  value={skuSearchTerm}
                  onChange={(e) => setSKUSearchTerm(e.target.value)}
                  placeholder="Enter product name to search..."
                  onKeyPress={(e) => e.key === 'Enter' && searchSKU()}
                />
                <button
                  className="btn"
                  onClick={searchSKU}
                  disabled={skuLoading || !skuSearchTerm.trim()}
                >
                  {skuLoading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>

            {skuResults.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Search Results</h4>
                <div className="space-y-2">
                  {skuResults.map((result: any, index: number) => (
                    <div key={index} className="border p-3 rounded">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="font-medium">{result.sku_name}</div>
                          <div className="text-xs text-gray-500">
                            SKU ID: {result.sku_id} • 
                            Match: {result.match_type} • 
                            Confidence: {(result.confidence * 100).toFixed(1)}%
                          </div>
                        </div>
                        <button
                          className="btn secondary text-xs"
                          onClick={() => {
                            const alias = prompt('Enter alias for this SKU:', skuSearchTerm);
                            if (alias) addAlias(result.sku_id, alias);
                          }}
                        >
                          Add Alias
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
              <h4 className="font-medium mb-2">SKU Management Tools</h4>
              <ul className="space-y-1">
                <li>• Search for SKUs by product name or alias</li>
                <li>• Add aliases to improve matching accuracy</li>
                <li>• View stock levels across different drivers</li>
                <li>• Monitor inventory discrepancies</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>

      {/* Inventory Tools */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">Inventory Management Tools</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link href="/admin/uid-generator" className="btn text-center">
            🏷️ UID Generator
          </Link>
          <Link href="/admin/qr-generator" className="btn text-center">
            📱 QR Code Generator  
          </Link>
          <Link href="/admin/sku-management" className="btn text-center">
            📦 SKU Management
          </Link>
          <Link href="/admin/uid-scanner" className="btn text-center">
            📷 UID Scanner
          </Link>
          <Link href="/admin/driver-stock" className="btn text-center">
            🚚 Driver Stock
          </Link>
          <Link href="/admin" className="btn secondary text-center">
            🏠 Admin Dashboard
          </Link>
        </div>
      </Card>
    </div>
  );
}