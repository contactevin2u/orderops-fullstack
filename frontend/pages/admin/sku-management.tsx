import React, { useState, useEffect } from 'react';
import PageHeader from '@/components/PageHeader';
import Card from '@/components/Card';
import { 
  getAllSKUs, 
  createSKU, 
  updateSKU, 
  deleteSKU,
  resolveSKU, 
  addSKUAlias,
  getInventoryConfig 
} from '@/lib/api';

interface SKU {
  id: number;
  code: string;
  name: string;
  category?: string;
  description?: string;
  price: number;
  is_serialized: boolean;
  is_active: boolean;
  created_at: string;
}

interface SKUFormData {
  code: string;
  name: string;
  category: string;
  description: string;
  price: number;
  is_serialized: boolean;
  is_active: boolean;
}

export default function SKUManagementPage() {
  const [config, setConfig] = useState<any>(null);
  const [skus, setSKUs] = useState<SKU[]>([]);
  const [filteredSKUs, setFilteredSKUs] = useState<SKU[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingSKU, setEditingSKU] = useState<SKU | null>(null);
  const [formData, setFormData] = useState<SKUFormData>({
    code: '',
    name: '',
    category: '',
    description: '',
    price: 0,
    is_serialized: false,
    is_active: true
  });

  // Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('active');

  // Search and alias state
  const [skuSearchTerm, setSKUSearchTerm] = useState('');
  const [skuResults, setSKUResults] = useState<any[]>([]);
  const [skuLoading, setSKULoading] = useState(false);

  const resetForm = () => {
    setFormData({
      code: '',
      name: '',
      category: '',
      description: '',
      price: 0,
      is_serialized: false,
      is_active: true
    });
    setEditingSKU(null);
    setShowForm(false);
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [configData, skuData] = await Promise.all([
        getInventoryConfig(),
        getAllSKUs()
      ]);
      
      setConfig(configData);
      setSKUs(skuData);
      setFilteredSKUs(skuData);
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = skus;

    // Text search
    if (searchTerm) {
      filtered = filtered.filter(sku =>
        sku.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        sku.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        sku.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Category filter
    if (categoryFilter) {
      filtered = filtered.filter(sku => sku.category === categoryFilter);
    }

    // Status filter
    if (statusFilter === 'active') {
      filtered = filtered.filter(sku => sku.is_active);
    } else if (statusFilter === 'inactive') {
      filtered = filtered.filter(sku => !sku.is_active);
    }

    setFilteredSKUs(filtered);
  };

  const handleEdit = (sku: SKU) => {
    setEditingSKU(sku);
    setFormData({
      code: sku.code,
      name: sku.name,
      category: sku.category || '',
      description: sku.description || '',
      price: sku.price || 0,
      is_serialized: sku.is_serialized,
      is_active: sku.is_active
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.code.trim() || !formData.name.trim()) {
      setError('Code and Name are required');
      return;
    }

    if (formData.price < 0) {
      setError('Price must be 0 or greater');
      return;
    }

    try {
      setSaving(true);
      setError('');
      setSuccess('');

      if (editingSKU) {
        // Update existing SKU
        const response = await updateSKU(editingSKU.id, formData);
        if (response.success) {
          setSuccess('SKU updated successfully');
        }
      } else {
        // Create new SKU
        const response = await createSKU(formData);
        if (response.success) {
          setSuccess('SKU created successfully');
        }
      }

      await loadData();
      resetForm();
    } catch (err: any) {
      setError(err.message || 'Failed to save SKU');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (sku: SKU) => {
    if (!confirm(`Are you sure you want to delete SKU "${sku.code} - ${sku.name}"?`)) {
      return;
    }

    try {
      setSaving(true);
      setError('');
      const response = await deleteSKU(sku.id);
      if (response.success) {
        setSuccess('SKU deleted successfully');
        await loadData();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete SKU');
    } finally {
      setSaving(false);
    }
  };

  const searchSKU = async () => {
    if (!skuSearchTerm.trim()) return;

    setSKULoading(true);
    try {
      const results = await resolveSKU(skuSearchTerm);
      setSKUResults(results.matches || []);
    } catch (err: any) {
      console.error('SKU search failed:', err);
      setSKUResults([]);
    } finally {
      setSKULoading(false);
    }
  };

  const addAlias = async (skuId: number, alias: string) => {
    try {
      await addSKUAlias(skuId, alias);
      setSuccess('Alias added successfully');
      setSKUResults([]);
      setSKUSearchTerm('');
    } catch (err: any) {
      setError(`Failed to add alias: ${err.message}`);
    }
  };

  const getUniqueCategories = () => {
    const categories = new Set(skus.map(sku => sku.category).filter(Boolean));
    return Array.from(categories).sort();
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [skus, searchTerm, categoryFilter, statusFilter]);

  if (loading) {
    return <Card>Loading SKU Management...</Card>;
  }

  return (
    <div>
      <PageHeader title="SKU Management" />
      
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Product Catalog</h2>
          <button
            className="btn"
            onClick={() => setShowForm(true)}
          >
            Add New SKU
          </button>
        </div>

        {/* Filters */}
        <Card>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Search</label>
              <input
                type="text"
                className="input"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name, code, or description..."
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select
                className="input"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="">All Categories</option>
                {getUniqueCategories().map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                className="input"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All</option>
                <option value="active">Active Only</option>
                <option value="inactive">Inactive Only</option>
              </select>
            </div>

            <div className="flex items-end">
              <div className="text-sm text-gray-600">
                {filteredSKUs.length} of {skus.length} SKUs
              </div>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SKU List */}
        <div className="lg:col-span-2">
          <Card>
            <h3 className="text-lg font-semibold mb-4">SKU List</h3>
            
            {filteredSKUs.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-2">📦</div>
                <p>No SKUs found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Name</th>
                      <th>Category</th>
                      <th>Price</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSKUs.map((sku) => (
                      <tr key={sku.id}>
                        <td className="font-mono">{sku.code}</td>
                        <td>
                          <div className="font-medium">{sku.name}</div>
                          {sku.description && (
                            <div className="text-xs text-gray-500">
                              {sku.description.substring(0, 50)}...
                            </div>
                          )}
                        </td>
                        <td>
                          {sku.category && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                              {sku.category}
                            </span>
                          )}
                        </td>
                        <td className="font-medium">
                          ${sku.price?.toFixed(2) || '0.00'}
                        </td>
                        <td>
                          {sku.is_serialized ? (
                            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">
                              📦 Serialized
                            </span>
                          ) : (
                            <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
                              Standard
                            </span>
                          )}
                        </td>
                        <td>
                          <span className={`px-2 py-1 rounded text-xs ${
                            sku.is_active 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {sku.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td>
                          <div className="flex gap-1">
                            <button
                              className="btn secondary text-xs"
                              onClick={() => handleEdit(sku)}
                            >
                              Edit
                            </button>
                            <button
                              className="btn secondary text-xs text-red-600"
                              onClick={() => handleDelete(sku)}
                              disabled={saving}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* SKU Search & Alias Management */}
        <div>
          <Card>
            <h3 className="text-lg font-semibold mb-4">SKU Search & Aliases</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Search SKU by Name</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    className="input flex-1"
                    value={skuSearchTerm}
                    onChange={(e) => setSKUSearchTerm(e.target.value)}
                    placeholder="Enter product name..."
                    onKeyPress={(e) => e.key === 'Enter' && searchSKU()}
                  />
                  <button
                    className="btn"
                    onClick={searchSKU}
                    disabled={skuLoading || !skuSearchTerm.trim()}
                  >
                    {skuLoading ? '...' : 'Search'}
                  </button>
                </div>
              </div>

              {skuResults.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Search Results</h4>
                  <div className="space-y-2">
                    {skuResults.map((result: any, index: number) => (
                      <div key={index} className="border p-3 rounded text-sm">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="font-medium">{result.sku_name}</div>
                            <div className="text-xs text-gray-500">
                              ID: {result.sku_id} • 
                              {result.match_type} • 
                              {(result.confidence * 100).toFixed(1)}%
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
            </div>
          </Card>
        </div>
      </div>

      {/* SKU Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">
                {editingSKU ? 'Edit SKU' : 'Add New SKU'}
              </h3>
              <button
                className="text-gray-500 hover:text-gray-700"
                onClick={resetForm}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">SKU Code *</label>
                  <input
                    type="text"
                    className="input"
                    value={formData.code}
                    onChange={(e) => setFormData({...formData, code: e.target.value})}
                    placeholder="e.g., BED001"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Price (RM) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="input"
                    value={formData.price}
                    onChange={(e) => setFormData({...formData, price: parseFloat(e.target.value) || 0})}
                    placeholder="0.00"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Product Name *</label>
                <input
                  type="text"
                  className="input"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="Enter descriptive product name"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Category</label>
                <select
                  className="input"
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                >
                  <option value="">Select Category</option>
                  <option value="BED">Bed</option>
                  <option value="WHEELCHAIR">Wheelchair</option>
                  <option value="OXYGEN">Oxygen Equipment</option>
                  <option value="ACCESSORY">Accessory</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  className="input"
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  placeholder="Optional detailed description"
                />
              </div>

              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.is_serialized}
                    onChange={(e) => setFormData({...formData, is_serialized: e.target.checked})}
                    className="mr-2"
                  />
                  Serialized Item (requires UID scanning)
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                    className="mr-2"
                  />
                  Active (available for use)
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  className="btn secondary"
                  onClick={resetForm}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : editingSKU ? 'Update SKU' : 'Create SKU'}
                </button>
              </div>
            </form>
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