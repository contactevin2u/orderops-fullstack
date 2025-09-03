import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, AlertTriangle } from 'lucide-react';

export default function Master88321() {
  const [confirmationText, setConfirmationText] = useState('');
  const [activeOperation, setActiveOperation] = useState<string | null>(null);
  const qc = useQueryClient();

  // Delete all orders
  const deleteAllOrdersMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/_api/admin/delete-all-orders', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Failed to delete orders');
      return response.json();
    },
    onSuccess: () => {
      alert('All orders deleted successfully');
      qc.invalidateQueries();
      setConfirmationText('');
      setActiveOperation(null);
    },
    onError: (error) => alert(`Error: ${error.message}`)
  });

  // Delete all drivers
  const deleteAllDriversMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/_api/admin/delete-all-drivers', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Failed to delete drivers');
      return response.json();
    },
    onSuccess: () => {
      alert('All drivers deleted successfully');
      qc.invalidateQueries();
      setConfirmationText('');
      setActiveOperation(null);
    },
    onError: (error) => alert(`Error: ${error.message}`)
  });

  // Delete all routes
  const deleteAllRoutesMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/_api/admin/delete-all-routes', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Failed to delete routes');
      return response.json();
    },
    onSuccess: () => {
      alert('All routes deleted successfully');
      qc.invalidateQueries();
      setConfirmationText('');
      setActiveOperation(null);
    },
    onError: (error) => alert(`Error: ${error.message}`)
  });

  // Reset entire database
  const resetDatabaseMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/_api/admin/reset-database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Failed to reset database');
      return response.json();
    },
    onSuccess: () => {
      alert('Database reset successfully');
      qc.invalidateQueries();
      setConfirmationText('');
      setActiveOperation(null);
    },
    onError: (error) => alert(`Error: ${error.message}`)
  });

  const handleOperation = (operation: string, mutationFn: () => void) => {
    if (activeOperation !== operation) {
      setActiveOperation(operation);
      setConfirmationText('');
      return;
    }

    if (confirmationText !== 'DELETE ALL DATA') {
      alert('Please type "DELETE ALL DATA" to confirm');
      return;
    }

    mutationFn();
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%)',
      color: 'white',
      padding: '2rem'
    }}>
      <div style={{
        maxWidth: '800px',
        margin: '0 auto',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        <div style={{
          textAlign: 'center',
          marginBottom: '3rem',
          padding: '2rem',
          background: 'rgba(220, 38, 38, 0.1)',
          border: '2px solid #dc2626',
          borderRadius: '12px'
        }}>
          <AlertTriangle size={48} style={{ color: '#dc2626', marginBottom: '1rem' }} />
          <h1 style={{ fontSize: '2.5rem', margin: '0 0 1rem 0', color: '#dc2626' }}>
            MASTER CONTROL PANEL
          </h1>
          <p style={{ fontSize: '1.125rem', opacity: 0.9, margin: 0 }}>
            ⚠️ DANGER ZONE - These actions are IRREVERSIBLE ⚠️
          </p>
        </div>

        <div style={{
          display: 'grid',
          gap: '2rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))'
        }}>
          
          {/* Delete All Orders */}
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '2rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
              <Trash2 size={24} style={{ color: '#ef4444', marginRight: '0.5rem' }} />
              <h3 style={{ margin: 0, color: '#ef4444' }}>Delete All Orders</h3>
            </div>
            <p style={{ marginBottom: '1.5rem', opacity: 0.8 }}>
              Permanently removes all orders, trips, and related data
            </p>
            
            {activeOperation === 'orders' && (
              <div style={{ marginBottom: '1rem' }}>
                <input
                  type="text"
                  placeholder='Type "DELETE ALL DATA" to confirm'
                  value={confirmationText}
                  onChange={(e) => setConfirmationText(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: 'rgba(0,0,0,0.3)',
                    border: '1px solid #ef4444',
                    borderRadius: '4px',
                    color: 'white',
                    fontSize: '1rem'
                  }}
                />
              </div>
            )}
            
            <button
              onClick={() => handleOperation('orders', deleteAllOrdersMutation.mutate)}
              disabled={deleteAllOrdersMutation.isLoading}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: activeOperation === 'orders' && confirmationText === 'DELETE ALL DATA' 
                  ? '#dc2626' : 'rgba(239, 68, 68, 0.2)',
                border: '1px solid #ef4444',
                borderRadius: '4px',
                color: 'white',
                fontSize: '1rem',
                cursor: deleteAllOrdersMutation.isLoading ? 'not-allowed' : 'pointer',
                opacity: deleteAllOrdersMutation.isLoading ? 0.5 : 1
              }}
            >
              {deleteAllOrdersMutation.isLoading ? 'Deleting...' : 'Delete All Orders'}
            </button>
          </div>

          {/* Delete All Drivers */}
          <div style={{
            background: 'rgba(249, 115, 22, 0.1)',
            border: '1px solid #f97316',
            borderRadius: '8px',
            padding: '2rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
              <Trash2 size={24} style={{ color: '#f97316', marginRight: '0.5rem' }} />
              <h3 style={{ margin: 0, color: '#f97316' }}>Delete All Drivers</h3>
            </div>
            <p style={{ marginBottom: '1.5rem', opacity: 0.8 }}>
              Permanently removes all driver accounts and related data
            </p>
            
            {activeOperation === 'drivers' && (
              <div style={{ marginBottom: '1rem' }}>
                <input
                  type="text"
                  placeholder='Type "DELETE ALL DATA" to confirm'
                  value={confirmationText}
                  onChange={(e) => setConfirmationText(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: 'rgba(0,0,0,0.3)',
                    border: '1px solid #f97316',
                    borderRadius: '4px',
                    color: 'white',
                    fontSize: '1rem'
                  }}
                />
              </div>
            )}
            
            <button
              onClick={() => handleOperation('drivers', deleteAllDriversMutation.mutate)}
              disabled={deleteAllDriversMutation.isLoading}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: activeOperation === 'drivers' && confirmationText === 'DELETE ALL DATA' 
                  ? '#ea580c' : 'rgba(249, 115, 22, 0.2)',
                border: '1px solid #f97316',
                borderRadius: '4px',
                color: 'white',
                fontSize: '1rem',
                cursor: deleteAllDriversMutation.isLoading ? 'not-allowed' : 'pointer',
                opacity: deleteAllDriversMutation.isLoading ? 0.5 : 1
              }}
            >
              {deleteAllDriversMutation.isLoading ? 'Deleting...' : 'Delete All Drivers'}
            </button>
          </div>

          {/* Delete All Routes */}
          <div style={{
            background: 'rgba(168, 85, 247, 0.1)',
            border: '1px solid #a855f7',
            borderRadius: '8px',
            padding: '2rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
              <Trash2 size={24} style={{ color: '#a855f7', marginRight: '0.5rem' }} />
              <h3 style={{ margin: 0, color: '#a855f7' }}>Delete All Routes</h3>
            </div>
            <p style={{ marginBottom: '1.5rem', opacity: 0.8 }}>
              Permanently removes all routes and assignments
            </p>
            
            {activeOperation === 'routes' && (
              <div style={{ marginBottom: '1rem' }}>
                <input
                  type="text"
                  placeholder='Type "DELETE ALL DATA" to confirm'
                  value={confirmationText}
                  onChange={(e) => setConfirmationText(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: 'rgba(0,0,0,0.3)',
                    border: '1px solid #a855f7',
                    borderRadius: '4px',
                    color: 'white',
                    fontSize: '1rem'
                  }}
                />
              </div>
            )}
            
            <button
              onClick={() => handleOperation('routes', deleteAllRoutesMutation.mutate)}
              disabled={deleteAllRoutesMutation.isLoading}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: activeOperation === 'routes' && confirmationText === 'DELETE ALL DATA' 
                  ? '#9333ea' : 'rgba(168, 85, 247, 0.2)',
                border: '1px solid #a855f7',
                borderRadius: '4px',
                color: 'white',
                fontSize: '1rem',
                cursor: deleteAllRoutesMutation.isLoading ? 'not-allowed' : 'pointer',
                opacity: deleteAllRoutesMutation.isLoading ? 0.5 : 1
              }}
            >
              {deleteAllRoutesMutation.isLoading ? 'Deleting...' : 'Delete All Routes'}
            </button>
          </div>

          {/* Nuclear Option - Reset Everything */}
          <div style={{
            background: 'rgba(220, 38, 38, 0.2)',
            border: '2px solid #dc2626',
            borderRadius: '8px',
            padding: '2rem',
            gridColumn: '1 / -1'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem', justifyContent: 'center' }}>
              <AlertTriangle size={32} style={{ color: '#dc2626', marginRight: '0.5rem' }} />
              <h3 style={{ margin: 0, color: '#dc2626', fontSize: '1.5rem' }}>NUCLEAR OPTION</h3>
              <AlertTriangle size={32} style={{ color: '#dc2626', marginLeft: '0.5rem' }} />
            </div>
            <p style={{ marginBottom: '1.5rem', opacity: 0.9, textAlign: 'center', fontSize: '1.125rem' }}>
              Reset entire database - removes ALL data and resets to factory state
            </p>
            
            {activeOperation === 'nuclear' && (
              <div style={{ marginBottom: '1rem', maxWidth: '400px', margin: '0 auto 1rem' }}>
                <input
                  type="text"
                  placeholder='Type "DELETE ALL DATA" to confirm'
                  value={confirmationText}
                  onChange={(e) => setConfirmationText(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '1rem',
                    background: 'rgba(0,0,0,0.5)',
                    border: '2px solid #dc2626',
                    borderRadius: '4px',
                    color: 'white',
                    fontSize: '1.125rem',
                    textAlign: 'center'
                  }}
                />
              </div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                onClick={() => handleOperation('nuclear', resetDatabaseMutation.mutate)}
                disabled={resetDatabaseMutation.isLoading}
                style={{
                  padding: '1rem 2rem',
                  background: activeOperation === 'nuclear' && confirmationText === 'DELETE ALL DATA' 
                    ? '#dc2626' : 'rgba(220, 38, 38, 0.3)',
                  border: '2px solid #dc2626',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '1.125rem',
                  fontWeight: 'bold',
                  cursor: resetDatabaseMutation.isLoading ? 'not-allowed' : 'pointer',
                  opacity: resetDatabaseMutation.isLoading ? 0.5 : 1,
                  minWidth: '200px'
                }}
              >
                {resetDatabaseMutation.isLoading ? 'RESETTING...' : 'RESET EVERYTHING'}
              </button>
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '3rem',
          padding: '1.5rem',
          background: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid #3b82f6',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <p style={{ margin: 0, color: '#60a5fa' }}>
            🔒 This page is accessible only via direct URL: <code>/master88321</code>
          </p>
        </div>
      </div>
    </div>
  );
}