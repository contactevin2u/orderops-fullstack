import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import AdminLayout from '@/components/admin/AdminLayout';
import { fetchDrivers, type Driver } from '@/utils/apiAdapter';
import { createDriver } from '@/utils/api';

interface DriverFormData {
  email: string;
  password: string;
  name: string;
  phone: string;
}

const initialFormData: DriverFormData = {
  email: '',
  password: '',
  name: '',
  phone: '',
};

export default function AdminDriversPage() {
  const [formData, setFormData] = useState<DriverFormData>(initialFormData);
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const queryClient = useQueryClient();

  const driversQuery = useQuery({
    queryKey: ['drivers'],
    queryFn: fetchDrivers,
  });

  const createDriverMutation = useMutation({
    mutationFn: createDriver,
    onSuccess: () => {
      setMessage({ type: 'success', text: 'Driver created successfully' });
      setFormData(initialFormData);
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ['drivers'] });
    },
    onError: (error: any) => {
      const errorMessage = error?.detail || 'Failed to create driver';
      setMessage({ type: 'error', text: errorMessage });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    if (!formData.email || !formData.password || !formData.name) {
      setMessage({ type: 'error', text: 'Email, password, and name are required' });
      return;
    }

    createDriverMutation.mutate(formData);
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
        <button
          className="btn"
          onClick={() => {
            setShowForm(!showForm);
            setMessage(null);
            if (showForm) {
              setFormData(initialFormData);
            }
          }}
        >
          {showForm ? 'Cancel' : 'Add New Driver'}
        </button>
      </div>

      {message && (
        <div
          className={`mb-4 p-4 rounded-md ${
            message.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
          role="alert"
        >
          {message.text}
        </div>
      )}

      {showForm && (
        <div className="mb-8 p-6 bg-gray-50 rounded-lg border">
          <h2 className="text-lg font-semibold mb-4">Create New Driver</h2>
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
                  placeholder="+1 (555) 123-4567"
                />
              </div>
            </div>
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
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={createDriverMutation.isPending}
                className="btn flex-1 md:flex-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createDriverMutation.isPending ? 'Creating...' : 'Create Driver'}
              </button>
              <button
                type="button"
                className="btn secondary flex-1 md:flex-none"
                onClick={() => {
                  setShowForm(false);
                  setFormData(initialFormData);
                  setMessage(null);
                }}
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

        {driversQuery.isLoading && (
          <div className="p-6 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading drivers...</p>
          </div>
        )}

        {driversQuery.isError && (
          <div className="p-6 text-center text-red-600" role="alert">
            <p>Failed to load drivers. Please try again.</p>
            <button
              className="btn secondary mt-2"
              onClick={() => driversQuery.refetch()}
            >
              Retry
            </button>
          </div>
        )}

        {driversQuery.data && driversQuery.data.length === 0 && (
          <div className="p-6 text-center text-gray-600">
            <p>No drivers found. Create your first driver to get started.</p>
          </div>
        )}

        {driversQuery.data && driversQuery.data.length > 0 && (
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
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {driversQuery.data.map((driver: Driver) => (
                  <tr key={driver.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      #{driver.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {driver.name || (
                        <span className="text-gray-400 italic">No name provided</span>
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
                          onClick={() => {
                            // TODO: Implement view driver details
                          }}
                        >
                          View
                        </button>
                        <button
                          className="text-indigo-600 hover:text-indigo-800"
                          onClick={() => {
                            // TODO: Implement edit driver
                          }}
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