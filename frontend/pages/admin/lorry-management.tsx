import React, { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { formatInTimeZone } from 'date-fns-tz';
import AdminNav from '../../components/admin/AdminNav';

// Types for lorry management
interface LorryAssignment {
  id: number;
  driver_id: number;
  driver_name: string;
  lorry_id: string;
  assignment_date: string;
  status: string;
  stock_verified: boolean;
  stock_verified_at?: string;
  shift_id?: number;
  assigned_by: number;
  assigned_at: string;
  notes?: string;
}

interface DriverHold {
  id: number;
  driver_id: number;
  driver_name: string;
  reason: string;
  description: string;
  status: string;
  created_by: number;
  created_at: string;
  resolved_by?: number;
  resolved_at?: string;
  resolution_notes?: string;
}

interface Driver {
  id: number;
  name: string;
  phone?: string;
}

export default function LorryManagement() {
  const { data: session } = useSession() || {};
  const [assignments, setAssignments] = useState<LorryAssignment[]>([]);
  const [holds, setHolds] = useState<DriverHold[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'assignments' | 'holds'>('assignments');
  
  // Form states
  const [showAssignmentForm, setShowAssignmentForm] = useState(false);
  const [assignmentForm, setAssignmentForm] = useState({
    driver_id: '',
    lorry_id: '',
    assignment_date: formatInTimeZone(new Date(), 'UTC', 'yyyy-MM-dd'),
    notes: ''
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load assignments, holds, and drivers in parallel
      const [assignmentsRes, holdsRes, driversRes] = await Promise.all([
        fetch('/api/lorry-management/assignments'),
        fetch('/api/lorry-management/holds'),
        fetch('/api/drivers')
      ]);

      if (assignmentsRes.ok) {
        const assignmentsData = await assignmentsRes.json();
        setAssignments(assignmentsData.data || []);
      }

      if (holdsRes.ok) {
        const holdsData = await holdsRes.json();
        setHolds(holdsData.data || []);
      }

      if (driversRes.ok) {
        const driversData = await driversRes.json();
        setDrivers(driversData.data || []);
      }
    } catch (err) {
      setError('Failed to load lorry management data');
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);
  
  // Handle SSR case where session might be undefined
  if (!session) {
    return (
      <div className="admin-container">
        <div className="admin-main">
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/lorry-management/assignments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          driver_id: parseInt(assignmentForm.driver_id),
          lorry_id: assignmentForm.lorry_id,
          assignment_date: assignmentForm.assignment_date,
          notes: assignmentForm.notes || null
        })
      });

      if (response.ok) {
        setShowAssignmentForm(false);
        setAssignmentForm({
          driver_id: '',
          lorry_id: '',
          assignment_date: formatInTimeZone(new Date(), 'UTC', 'yyyy-MM-dd'),
          notes: ''
        });
        loadData(); // Refresh data
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create assignment');
      }
    } catch (err) {
      setError('Failed to create assignment');
      console.error('Error creating assignment:', err);
    }
  };

  const handleResolveHold = async (holdId: number) => {
    const resolutionNotes = prompt('Enter resolution notes:');
    if (!resolutionNotes) return;

    try {
      const response = await fetch(`/api/lorry-management/holds/${holdId}/resolve`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(resolutionNotes)
      });

      if (response.ok) {
        loadData(); // Refresh data
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to resolve hold');
      }
    } catch (err) {
      setError('Failed to resolve hold');
      console.error('Error resolving hold:', err);
    }
  };

  if (loading) {
    return (
      <div className="admin-container">
        <AdminNav />
        <main className="admin-main">
          <div className="loading">Loading lorry management...</div>
        </main>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <AdminNav />
      <main className="admin-main">
        <div className="admin-header">
          <h1>Lorry Management</h1>
          <div className="admin-actions">
            <button 
              className="btn btn-primary"
              onClick={() => setShowAssignmentForm(true)}
            >
              Create Assignment
            </button>
          </div>
        </div>

        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError(null)} className="error-close">×</button>
          </div>
        )}

        {/* Tabs */}
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'assignments' ? 'active' : ''}`}
            onClick={() => setActiveTab('assignments')}
          >
            Assignments ({assignments.length})
          </button>
          <button 
            className={`tab ${activeTab === 'holds' ? 'active' : ''}`}
            onClick={() => setActiveTab('holds')}
          >
            Driver Holds ({holds.filter(h => h.status === 'ACTIVE').length})
          </button>
        </div>

        {/* Assignments Tab */}
        {activeTab === 'assignments' && (
          <div className="tab-content">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Driver</th>
                    <th>Lorry ID</th>
                    <th>Status</th>
                    <th>Stock Verified</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {assignments.map((assignment) => (
                    <tr key={assignment.id}>
                      <td>{assignment.assignment_date}</td>
                      <td>{assignment.driver_name}</td>
                      <td>{assignment.lorry_id}</td>
                      <td>
                        <span className={`status ${assignment.status.toLowerCase()}`}>
                          {assignment.status}
                        </span>
                      </td>
                      <td>
                        <span className={`status ${assignment.stock_verified ? 'verified' : 'pending'}`}>
                          {assignment.stock_verified ? '✓ Verified' : '⏳ Pending'}
                        </span>
                      </td>
                      <td>{assignment.notes || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Holds Tab */}
        {activeTab === 'holds' && (
          <div className="tab-content">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Driver</th>
                    <th>Reason</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {holds.map((hold) => (
                    <tr key={hold.id}>
                      <td>{hold.driver_name}</td>
                      <td>
                        <span className={`reason ${hold.reason.toLowerCase().replace('_', '-')}`}>
                          {hold.reason.replace('_', ' ')}
                        </span>
                      </td>
                      <td>{hold.description}</td>
                      <td>
                        <span className={`status ${hold.status.toLowerCase()}`}>
                          {hold.status}
                        </span>
                      </td>
                      <td>{new Date(hold.created_at).toLocaleDateString()}</td>
                      <td>
                        {hold.status === 'ACTIVE' && (
                          <button 
                            className="btn btn-sm btn-success"
                            onClick={() => handleResolveHold(hold.id)}
                          >
                            Resolve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Assignment Form Modal */}
        {showAssignmentForm && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h2>Create Lorry Assignment</h2>
                <button 
                  className="modal-close"
                  onClick={() => setShowAssignmentForm(false)}
                >
                  ×
                </button>
              </div>
              
              <form onSubmit={handleCreateAssignment}>
                <div className="form-group">
                  <label>Driver</label>
                  <select 
                    value={assignmentForm.driver_id}
                    onChange={(e) => setAssignmentForm({...assignmentForm, driver_id: e.target.value})}
                    required
                  >
                    <option value="">Select Driver</option>
                    {drivers.map(driver => (
                      <option key={driver.id} value={driver.id}>
                        {driver.name} {driver.phone && `(${driver.phone})`}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Lorry ID</label>
                  <input
                    type="text"
                    value={assignmentForm.lorry_id}
                    onChange={(e) => setAssignmentForm({...assignmentForm, lorry_id: e.target.value})}
                    placeholder="e.g. LRY001"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Assignment Date</label>
                  <input
                    type="date"
                    value={assignmentForm.assignment_date}
                    onChange={(e) => setAssignmentForm({...assignmentForm, assignment_date: e.target.value})}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Notes (Optional)</label>
                  <textarea
                    value={assignmentForm.notes}
                    onChange={(e) => setAssignmentForm({...assignmentForm, notes: e.target.value})}
                    rows={3}
                    placeholder="Any additional notes..."
                  />
                </div>
                
                <div className="modal-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowAssignmentForm(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Create Assignment
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
      
      <style jsx>{`
        .tabs {
          display: flex;
          border-bottom: 1px solid #ddd;
          margin-bottom: 20px;
        }
        
        .tab {
          padding: 12px 24px;
          border: none;
          background: none;
          cursor: pointer;
          border-bottom: 2px solid transparent;
        }
        
        .tab.active {
          border-bottom-color: #0070f3;
          color: #0070f3;
          font-weight: 600;
        }
        
        .status.verified { color: #10b981; }
        .status.pending { color: #f59e0b; }
        .reason.stock-variance { 
          background: #fef3c7; 
          color: #92400e; 
          padding: 2px 8px; 
          border-radius: 4px; 
          font-size: 12px;
        }
        
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        
        .modal {
          background: white;
          border-radius: 8px;
          padding: 0;
          width: 500px;
          max-width: 90vw;
        }
        
        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          border-bottom: 1px solid #eee;
        }
        
        .modal-close {
          border: none;
          background: none;
          font-size: 24px;
          cursor: pointer;
        }
        
        .modal form {
          padding: 20px;
        }
        
        .modal-actions {
          display: flex;
          gap: 10px;
          justify-content: flex-end;
          margin-top: 20px;
        }
        
        .error-banner {
          background: #fee;
          color: #c53030;
          padding: 12px;
          border-radius: 4px;
          margin-bottom: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .error-close {
          border: none;
          background: none;
          color: #c53030;
          font-size: 18px;
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}