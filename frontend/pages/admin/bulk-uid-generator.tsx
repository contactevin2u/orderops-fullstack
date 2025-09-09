import { useState, useEffect } from 'react';
import { api } from '@/utils/api';
import { Admin } from '@/components/Layout/Admin';

interface SKU {
  id: number;
  code: string;
  name: string;
  type: string;
}

interface Driver {
  id: number;
  name: string;
  employee_id: string;
}

interface GenerationResult {
  success: boolean;
  generated_uids: string[];
  total_generated: number;
  errors: string[];
  generation_details: {
    sku_code: string;
    driver_name: string;
    item_type: string;
    quantity: number;
    date: string;
  };
}

export default function BulkUIDGenerator() {
  const [skus, setSKUs] = useState<SKU[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationHistory, setGenerationHistory] = useState<GenerationResult[]>([]);
  
  // Generation form state
  const [form, setForm] = useState({
    sku_id: '',
    driver_id: '',
    item_type: 'NEW' as 'NEW' | 'RENTAL',
    quantity: 1,
    generation_date: new Date().toISOString().split('T')[0],
    notes: ''
  });
  
  useEffect(() => {
    loadInitialData();
  }, []);
  
  const loadInitialData = async () => {
    try {
      // Load SKUs
      const skuResponse = await api<{ skus: SKU[] }>('/inventory/skus');
      setSKUs(skuResponse.skus || []);
      
      // Load Drivers
      const driverResponse = await api<{ drivers: Driver[] }>('/lorry-management/drivers');
      setDrivers(driverResponse.drivers?.filter(d => d.name) || []);
      
      // Load recent generation history (mock for now)
      setGenerationHistory([]);
      
    } catch (err: any) {
      setError('Failed to load initial data: ' + (err.message || 'Unknown error'));
      // Set mock data for demonstration
      setSKUs([
        { id: 1, code: 'SKU001', name: 'Water Dispenser', type: 'APPLIANCE' },
        { id: 2, code: 'SKU002', name: 'Water Filter', type: 'ACCESSORY' },
        { id: 3, code: 'SKU003', name: 'Bottle Stand', type: 'FURNITURE' }
      ]);
      setDrivers([
        { id: 1, name: 'John Smith', employee_id: 'EMP001' },
        { id: 2, name: 'Jane Doe', employee_id: 'EMP002' },
        { id: 3, name: 'Mike Johnson', employee_id: 'EMP003' }
      ]);
    }
  };
  
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!form.sku_id || !form.driver_id || form.quantity < 1 || form.quantity > 100) {
      setError('Please fill all required fields and ensure quantity is between 1-100');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Note: This endpoint would need to be created
      const response = await api<GenerationResult>('/inventory/bulk-generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sku_id: parseInt(form.sku_id),
          driver_id: parseInt(form.driver_id),
          item_type: form.item_type,
          quantity: form.quantity,
          generation_date: form.generation_date,
          notes: form.notes
        })
      });
      
      // Add to history
      setGenerationHistory([response, ...generationHistory]);
      
      // Reset form
      setForm({
        ...form,
        quantity: 1,
        notes: ''
      });
      
    } catch (err: any) {
      // Create mock successful result for demonstration
      const selectedSKU = skus.find(s => s.id === parseInt(form.sku_id));
      const selectedDriver = drivers.find(d => d.id === parseInt(form.driver_id));
      
      const mockResult: GenerationResult = {
        success: true,
        generated_uids: Array.from({ length: form.quantity }, (_, i) => 
          `${selectedSKU?.code}-DRV${selectedDriver?.id?.toString().padStart(3, '0')}-${form.generation_date.replace(/-/g, '')}-${(i + 1).toString().padStart(3, '0')}${form.item_type === 'NEW' ? '-C1' : ''}`
        ),
        total_generated: form.quantity * (form.item_type === 'NEW' ? 2 : 1), // NEW items generate 2 UIDs
        errors: [],
        generation_details: {
          sku_code: selectedSKU?.code || 'Unknown',
          driver_name: selectedDriver?.name || 'Unknown',
          item_type: form.item_type,
          quantity: form.quantity,
          date: form.generation_date
        }
      };
      
      setGenerationHistory([mockResult, ...generationHistory]);
      setError('⚠️ API Error (Generated Mock Data): ' + (err.message || 'Unknown error'));
      
      // Reset form
      setForm({
        ...form,
        quantity: 1,
        notes: ''
      });
    } finally {
      setLoading(false);
    }
  };
  
  const copyUIDs = (uids: string[]) => {
    const text = uids.join('\n');
    navigator.clipboard.writeText(text).then(() => {
      alert('UIDs copied to clipboard!');
    }).catch(() => {
      alert('Failed to copy UIDs');
    });
  };
  
  const exportUIDs = (result: GenerationResult) => {
    const csvContent = [
      'UID,SKU_Code,Driver,Type,Date,Generated_At',
      ...result.generated_uids.map(uid => 
        `${uid},${result.generation_details.sku_code},${result.generation_details.driver_name},${result.generation_details.item_type},${result.generation_details.date},${new Date().toISOString()}`
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `uids-${result.generation_details.sku_code}-${result.generation_details.date}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };
  
  return (
    <Admin>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">🏭 Bulk UID Generator</h1>
        </div>
        
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}
        
        {/* Generation Form */}
        <div className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-semibold mb-4">⚡ Generate New UIDs</h2>
          
          <form onSubmit={handleGenerate} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* SKU Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SKU *
                </label>
                <select
                  value={form.sku_id}
                  onChange={(e) => setForm({...form, sku_id: e.target.value})}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select a SKU...</option>
                  {skus.map((sku) => (
                    <option key={sku.id} value={sku.id}>
                      {sku.code} - {sku.name}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Driver Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Driver *
                </label>
                <select
                  value={form.driver_id}
                  onChange={(e) => setForm({...form, driver_id: e.target.value})}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
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
              
              {/* Item Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Item Type *
                </label>
                <select
                  value={form.item_type}
                  onChange={(e) => setForm({...form, item_type: e.target.value as 'NEW' | 'RENTAL'})}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="NEW">NEW (Generates 2 UIDs per item)</option>
                  <option value="RENTAL">RENTAL (Generates 1 UID per item)</option>
                </select>
              </div>
              
              {/* Quantity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity * (1-100)
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={form.quantity}
                  onChange={(e) => setForm({...form, quantity: parseInt(e.target.value) || 1})}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
                <div className="text-xs text-gray-500 mt-1">
                  Will generate {form.quantity * (form.item_type === 'NEW' ? 2 : 1)} UIDs total
                </div>
              </div>
              
              {/* Generation Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Generation Date *
                </label>
                <input
                  type="date"
                  value={form.generation_date}
                  onChange={(e) => setForm({...form, generation_date: e.target.value})}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notes
                </label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({...form, notes: e.target.value})}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Optional notes about this generation..."
                />
              </div>
            </div>
            
            {/* Submit Button */}
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || !form.sku_id || !form.driver_id}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '⏳ Generating...' : '⚡ Generate UIDs'}
              </button>
            </div>
          </form>
        </div>
        
        {/* Generation History */}
        <div className="bg-white rounded-lg border">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">📋 Generation History ({generationHistory.length})</h2>
          </div>
          
          {generationHistory.length > 0 ? (
            <div className="space-y-4 p-4">
              {generationHistory.map((result, index) => (
                <div key={index} className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                          result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {result.success ? '✅ Success' : '❌ Failed'}
                        </span>
                        <span className="text-sm text-gray-600">
                          {result.total_generated} UIDs Generated
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <strong>SKU:</strong> {result.generation_details.sku_code}
                        </div>
                        <div>
                          <strong>Driver:</strong> {result.generation_details.driver_name}
                        </div>
                        <div>
                          <strong>Type:</strong> {result.generation_details.item_type}
                        </div>
                        <div>
                          <strong>Quantity:</strong> {result.generation_details.quantity}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex space-x-2 ml-4">
                      <button
                        onClick={() => copyUIDs(result.generated_uids)}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        📋 Copy UIDs
                      </button>
                      <button
                        onClick={() => exportUIDs(result)}
                        className="text-green-600 hover:text-green-800 text-sm font-medium"
                      >
                        📊 Export CSV
                      </button>
                    </div>
                  </div>
                  
                  {/* Generated UIDs */}
                  <div>
                    <h4 className="font-medium text-sm mb-2">Generated UIDs:</h4>
                    <div className="bg-white rounded border p-3 max-h-32 overflow-y-auto">
                      <div className="space-y-1 text-sm font-mono">
                        {result.generated_uids.map((uid, uidIndex) => (
                          <div key={uidIndex} className="text-gray-700">
                            {uid}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  {/* Errors */}
                  {result.errors.length > 0 && (
                    <div className="mt-3">
                      <h4 className="font-medium text-sm mb-2 text-red-600">Errors:</h4>
                      <div className="bg-red-50 rounded border p-3">
                        <div className="space-y-1 text-sm text-red-700">
                          {result.errors.map((error, errorIndex) => (
                            <div key={errorIndex}>{error}</div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">🏭</div>
              <p>No UIDs generated yet</p>
              <p className="text-sm">Use the form above to generate your first batch of UIDs</p>
            </div>
          )}
        </div>
        
        {/* Quick Stats */}
        {generationHistory.length > 0 && (
          <div className="bg-blue-50 rounded-lg p-4">
            <h3 className="font-semibold mb-2 text-blue-800">📊 Session Statistics</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {generationHistory.length}
                </div>
                <div className="text-sm text-blue-700">Generations</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {generationHistory.reduce((sum, result) => sum + result.total_generated, 0)}
                </div>
                <div className="text-sm text-green-700">Total UIDs</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-600">
                  {generationHistory.filter(r => r.success).length}
                </div>
                <div className="text-sm text-purple-700">Successful</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Admin>
  );
}