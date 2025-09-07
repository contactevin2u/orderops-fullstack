import React, { useState } from 'react';
import AdminLayout from '@/components/Layout/AdminLayout';
import { Button } from '@/components/ui/button';
import { useDrivers, useCreateDriver, useUpdateDriver } from '@/hooks/useDrivers';
import { useToast } from '@/hooks/useToast';
import { formatPhone } from '@/lib/format';
import { driverCreateSchema, driverUpdateSchema, type DriverCreateForm, type DriverUpdateForm } from '@/lib/zod-schemas';
import type { Driver } from '@/lib/apiAdapter';

interface DriverFormData {
  email: string;
  password: string;
  name: string;
  phone: string;
  base_warehouse: string;
  firebase_uid: string;
}

const initialFormData: DriverFormData = {
  email: '',
  password: '',
  name: '',
  phone: '',
  base_warehouse: 'BATU_CAVES',
  firebase_uid: '',
};

export default function AdminDriversPage() {
  const [formData, setFormData] = useState<DriverFormData>(initialFormData);
  const [showForm, setShowForm] = useState(false);
  const [editingDriver, setEditingDriver] = useState<Driver | null>(null);
  const [viewingDriver, setViewingDriver] = useState<Driver | null>(null);

  const { success, error } = useToast();
  const { data: drivers, isLoading, isError, refetch } = useDrivers();

  const createDriverMutation = useCreateDriver();
  const updateDriverMutation = useUpdateDriver();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (editingDriver) {
        // Update existing driver
        const updateData = driverUpdateSchema.parse({
          name: formData.name,
          phone: formData.phone,
          base_warehouse: formData.base_warehouse,
        });
        
        await updateDriverMutation.mutateAsync({
          id: editingDriver.id,
          data: updateData
        });
        
        success('Driver updated successfully');
        setEditingDriver(null);
      } else {
        // Create new driver
        const createData = driverCreateSchema.parse(formData);
        await createDriverMutation.mutateAsync(createData);
        
        success('Driver created successfully');
        setFormData(initialFormData);
        setShowForm(false);
      }
    } catch (err: any) {
      const errorMessage = err?.detail || err?.message || 'Operation failed';
      error(errorMessage);
    }
  };

  const handleEdit = (driver: Driver) => {
    setEditingDriver(driver);
    setFormData({
      email: '', // Not editable
      password: '', // Not editable
      name: driver.name || '',
      phone: driver.phone || '',
      base_warehouse: driver.base_warehouse || 'BATU_CAVES',
    });
    setShowForm(true);
  };

  const handleView = (driver: Driver) => {
    setViewingDriver(driver);
  };

  const closeModals = () => {
    setShowForm(false);
    setEditingDriver(null);
    setViewingDriver(null);
    setFormData(initialFormData);
  };

  const handleInputChange = (field: keyof DriverFormData) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }));
  };

  return (
    <div className="max-w-6xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Driver Management</h1>
        <Button
          onClick={() => {
            if (showForm) {
              closeModals();
            } else {
              setShowForm(true);
              setFormData(initialFormData);
            }
          }}
        >
          {showForm ? 'Cancel' : 'Add New Driver'}
        </Button>
      </div>


      {showForm && (
        <div className="mb-8 p-6 bg-gray-50 rounded-lg border">
          <h2 className="text-lg font-semibold mb-4">
            {editingDriver ? `Edit Driver: ${editingDriver.name}` : 'Create New Driver'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name *
                </label>
                <input
                  id="name"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={formData.name}
                  onChange={handleInputChange('name')}
                  required
                  placeholder="Enter driver's full name"
                />
              </div>
              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                  Phone Number
                </label>
                <input
                  id="phone"
                  type="tel"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={formData.phone}
                  onChange={handleInputChange('phone')}
                  placeholder="+60 12-345 6789"
                />
              </div>
            </div>
            <div>
              <label htmlFor="base_warehouse" className="block text-sm font-medium text-gray-700 mb-1">
                Base Warehouse *
              </label>
              <select
                id="base_warehouse"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={formData.base_warehouse}
                onChange={(e) => setFormData(prev => ({ ...prev, base_warehouse: e.target.value }))}
                required
              >
                <option value="BATU_CAVES">🏢 Batu Caves, Selangor (Peninsular Malaysia)</option>
                <option value="KOTA_KINABALU">🏢 Kota Kinabalu, Sabah (East Malaysia)</option>
              </select>
              <p className="mt-1 text-sm text-gray-500">
                Determines which region this driver will handle deliveries for
              </p>
            </div>
            
            {!editingDriver && (
              <>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                    Email Address *
                  </label>
                  <input
                    id="email"
                    type="email"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={formData.email}
                    onChange={handleInputChange('email')}
                    required
                    placeholder="driver@company.com"
                  />
                </div>
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                    Password *
                  </label>
                  <input
                    id="password"
                    type="password"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={formData.password}
                    onChange={handleInputChange('password')}
                    required
                    placeholder="Secure password for driver login"
                    minLength={6}
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Password will be used by the driver to log into the mobile app
                  </p>
                </div>
                <div>
                  <label htmlFor="firebase_uid" className="block text-sm font-medium text-gray-700 mb-1">
                    Firebase UID (Optional)
                  </label>
                  <input
                    id="firebase_uid"
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={formData.firebase_uid}
                    onChange={handleInputChange('firebase_uid')}
                    placeholder="Firebase User ID for existing Firebase account"
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    If the driver already has a Firebase account, enter their UID here to link it
                  </p>
                </div>
              </>
            )}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={createDriverMutation.isPending || updateDriverMutation.isPending}
                className="btn flex-1 md:flex-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {editingDriver 
                  ? (updateDriverMutation.isPending ? 'Updating...' : 'Update Driver')
                  : (createDriverMutation.isPending ? 'Creating...' : 'Create Driver')
                }
              </button>
              <button
                type="button"
                className="btn secondary flex-1 md:flex-none"
                onClick={closeModals}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Active Drivers</h2>
        </div>

        {isLoading && (
          <div className="p-6 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading drivers...</p>
          </div>
        )}

        {isError && (
          <div className="p-6 text-center text-red-600" role="alert">
            <p>Failed to load drivers. Please try again.</p>
            <Button variant="secondary" className="mt-2" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        )}

        {drivers && drivers.length === 0 && (
          <div className="p-6 text-center text-gray-600">
            <p>No drivers found. Create your first driver to get started.</p>
          </div>
        )}

        {drivers && drivers.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Driver ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Base Warehouse
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {drivers.map((driver: Driver) => (
                  <tr key={driver.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      #{driver.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {driver.name || (
                        <span className="text-gray-400 italic">No name provided</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {driver.base_warehouse === 'KOTA_KINABALU' ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          🏢 Kota Kinabalu
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          🏢 Batu Caves
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Active
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex gap-2">
                        <button
                          className="text-blue-600 hover:text-blue-800"
                          onClick={() => handleView(driver)}
                        >
                          View
                        </button>
                        <button
                          className="text-indigo-600 hover:text-indigo-800"
                          onClick={() => handleEdit(driver)}
                        >
                          Edit
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* View Driver Modal */}
      {viewingDriver && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Driver Details</h2>
              <button
                onClick={closeModals}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Basic Information</h3>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    <div>
                      <span className="font-medium">Driver ID:</span>
                      <span className="ml-2">#{viewingDriver.id}</span>
                    </div>
                    <div>
                      <span className="font-medium">Name:</span>
                      <span className="ml-2">{viewingDriver.name || 'No name provided'}</span>
                    </div>
                    <div>
                      <span className="font-medium">Phone:</span>
                      <span className="ml-2">{viewingDriver.phone || 'No phone provided'}</span>
                    </div>
                    <div>
                      <span className="font-medium">Status:</span>
                      <span className="ml-2">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Active
                        </span>
                      </span>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="font-medium text-gray-700 mb-2">Warehouse Assignment</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div>
                      <span className="font-medium">Base Warehouse:</span>
                      <div className="mt-2">
                        {viewingDriver.base_warehouse === 'KOTA_KINABALU' ? (
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                            🏢 Kota Kinabalu, Sabah
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                            🏢 Batu Caves, Selangor
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-sm text-gray-600">
                        {viewingDriver.base_warehouse === 'KOTA_KINABALU' 
                          ? 'Handles deliveries in East Malaysia (Sabah region)'
                          : 'Handles deliveries in Peninsular Malaysia from Batu Caves hub'
                        }
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex gap-3 pt-4">
                <button
                  className="btn"
                  onClick={() => {
                    closeModals();
                    handleEdit(viewingDriver);
                  }}
                >
                  Edit Driver
                </button>
                <button
                  className="btn secondary"
                  onClick={closeModals}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h3 className="font-medium text-blue-800 mb-2">📱 Driver Mobile App</h3>
        <p className="text-sm text-blue-700">
          Once a driver is created, they can download the mobile app and log in using their email and password.
          The app will show them their assigned orders and allow them to update delivery status.
        </p>
      </div>
    </div>
  );
}

(AdminDriversPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;