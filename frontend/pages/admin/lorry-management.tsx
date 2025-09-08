import React, { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { formatInTimeZone } from 'date-fns-tz';
import { 
  Truck, 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  Plus, 
  Clock, 
  MapPin, 
  Package, 
  Users,
  Search,
  Filter,
  RefreshCw,
  Eye,
  Edit,
  UserX,
  Settings
} from 'lucide-react';
import AdminLayout from '@/components/Layout/AdminLayout';

// Types for the integrated lorry management system
interface LorryAssignment {
  id: number;
  driver_id: number;
  driver_name: string;
  lorry_id: string;
  assignment_date: string;
  status: 'PENDING' | 'ACTIVE' | 'COMPLETED';
  stock_verified: boolean;
  stock_verified_at?: string;
  shift_id?: number;
  assigned_by: number;
  assigned_at: string;
  notes?: string;
  current_stock_count?: number;
  expected_stock_count?: number;
}

interface DriverHold {
  id: number;
  driver_id: number;
  driver_name: string;
  reason: 'STOCK_VARIANCE' | 'MISSING_ITEMS' | 'DAMAGED_ITEMS' | 'OTHER';
  description: string;
  status: 'ACTIVE' | 'RESOLVED' | 'ESCALATED';
  created_by: number;
  created_at: string;
  resolved_by?: number;
  resolved_at?: string;
  resolution_notes?: string;
  lorry_id?: string;
  variance_count?: number;
}

interface Driver {
  id: number;
  name: string;
  phone?: string;
  is_active: boolean;
  current_assignment?: LorryAssignment;
}

interface LorryStock {
  lorry_id: string;
  current_items: number;
  total_capacity: number;
  last_verified: string;
  verification_status: 'VERIFIED' | 'PENDING' | 'VARIANCE_DETECTED';
  assigned_driver?: string;
}

export default function LorryManagementPage() {
  const { data: session } = useSession();
  
  // State management
  const [activeTab, setActiveTab] = useState<'assignments' | 'holds' | 'stock' | 'overview'>('overview');
  const [assignments, setAssignments] = useState<LorryAssignment[]>([]);
  const [holds, setHolds] = useState<DriverHold[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [lorryStock, setLorryStock] = useState<LorryStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Form states
  const [showAssignmentForm, setShowAssignmentForm] = useState(false);
  const [showHoldForm, setShowHoldForm] = useState(false);
  const [showStockForm, setShowStockForm] = useState(false);
  
  // Assignment form
  const [assignmentForm, setAssignmentForm] = useState({
    driver_id: '',
    lorry_id: '',
    assignment_date: formatInTimeZone(new Date(), 'UTC', 'yyyy-MM-dd'),
    notes: ''
  });

  // Hold form
  const [holdForm, setHoldForm] = useState({
    driver_id: '',
    reason: 'STOCK_VARIANCE',
    description: '',
    lorry_id: ''
  });

  // Stock management form
  const [stockForm, setStockForm] = useState({
    lorry_id: '',
    action: 'LOAD', // LOAD or UNLOAD
    item_count: '',
    notes: ''
  });

  // Load all data
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('Loading lorry management data from proxy');
      
      const [assignmentsRes, holdsRes, driversRes] = await Promise.all([
        fetch(`/_api/lorry-management/assignments`, { credentials: 'include' }),
        fetch(`/_api/lorry-management/holds`, { credentials: 'include' }),
        fetch(`/_api/drivers`, { credentials: 'include' })
      ]);

      console.log('Response status:', {
        assignments: assignmentsRes.status,
        holds: holdsRes.status,
        drivers: driversRes.status
      });

      // Check for 401s and redirect to login
      if (assignmentsRes.status === 401 || holdsRes.status === 401 || driversRes.status === 401) {
        console.log('401 Unauthorized - redirecting to login');
        window.location.href = '/login';
        return;
      }

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
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle assignment creation
  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch(`/_api/lorry-management/assignments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
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
        loadData();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create assignment');
      }
    } catch (err) {
      setError('Failed to create assignment');
    }
  };

  // Handle driver hold creation
  const handleCreateHold = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch(`/_api/lorry-management/holds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          driver_id: parseInt(holdForm.driver_id),
          reason: holdForm.reason,
          description: holdForm.description,
          lorry_id: holdForm.lorry_id || null
        })
      });

      if (response.ok) {
        setShowHoldForm(false);
        setHoldForm({
          driver_id: '',
          reason: 'STOCK_VARIANCE',
          description: '',
          lorry_id: ''
        });
        loadData();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create hold');
      }
    } catch (err) {
      setError('Failed to create hold');
    }
  };

  // Handle hold resolution
  const handleResolveHold = async (holdId: number) => {
    const resolutionNotes = prompt('Enter resolution notes:');
    if (!resolutionNotes) return;

    try {
      const response = await fetch(`/_api/lorry-management/holds/${holdId}/resolve`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ resolution_notes: resolutionNotes })
      });

      if (response.ok) {
        loadData();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to resolve hold');
      }
    } catch (err) {
      setError('Failed to resolve hold');
    }
  };

  // Loading state
  if (!session) {
    return (
      <div className="main">
        <div className="container">
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="main">
        <div className="container">
          <div className="loading">
            <RefreshCw className="animate-spin" size={20} />
            Loading lorry management system...
          </div>
        </div>
      </div>
    );
  }

  // Statistics for overview
  const activeAssignments = assignments.filter(a => a.status === 'ACTIVE').length;
  const pendingVerifications = assignments.filter(a => !a.stock_verified).length;
  const activeHolds = holds.filter(h => h.status === 'ACTIVE').length;
  const totalDrivers = drivers.length;

  return (
    <div className="main">
      <div className="container">
        {/* Header */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'flex-start',
          marginBottom: 'var(--space-6)' 
        }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
              <Shield size={24} style={{ display: 'inline', marginRight: 'var(--space-2)' }} />
              Lorry Management System
            </h1>
            <p style={{ opacity: 0.8, marginBottom: 'var(--space-4)' }}>
              Complete integrated system for assignments, stock verification, and driver accountability
            </p>
          </div>
          
          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <button 
              className="btn btn-secondary"
              onClick={loadData}
              disabled={loading}
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="card" style={{ 
            borderLeft: '4px solid var(--color-error)',
            backgroundColor: 'var(--color-error-light)',
            marginBottom: 'var(--space-4)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <AlertTriangle size={16} color="var(--color-error)" />
              <span>{error}</span>
              <button 
                onClick={() => setError(null)}
                style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Overview Stats */}
        <div className="grid" style={{ 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: 'var(--space-4)',
          marginBottom: 'var(--space-6)'
        }}>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <div style={{ 
                padding: 'var(--space-2)', 
                borderRadius: 'var(--radius-2)',
                backgroundColor: 'var(--color-primary-light)'
              }}>
                <Truck size={20} color="var(--color-primary)" />
              </div>
              <div>
                <p style={{ fontSize: '0.875rem', opacity: 0.8, margin: 0 }}>Active Assignments</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>{activeAssignments}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <div style={{ 
                padding: 'var(--space-2)', 
                borderRadius: 'var(--radius-2)',
                backgroundColor: 'var(--color-warning-light)'
              }}>
                <Clock size={20} color="var(--color-warning)" />
              </div>
              <div>
                <p style={{ fontSize: '0.875rem', opacity: 0.8, margin: 0 }}>Pending Verifications</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>{pendingVerifications}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <div style={{ 
                padding: 'var(--space-2)', 
                borderRadius: 'var(--radius-2)',
                backgroundColor: 'var(--color-error-light)'
              }}>
                <UserX size={20} color="var(--color-error)" />
              </div>
              <div>
                <p style={{ fontSize: '0.875rem', opacity: 0.8, margin: 0 }}>Active Holds</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>{activeHolds}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <div style={{ 
                padding: 'var(--space-2)', 
                borderRadius: 'var(--radius-2)',
                backgroundColor: 'var(--color-success-light)'
              }}>
                <Users size={20} color="var(--color-success)" />
              </div>
              <div>
                <p style={{ fontSize: '0.875rem', opacity: 0.8, margin: 0 }}>Total Drivers</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>{totalDrivers}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{ 
          display: 'flex', 
          borderBottom: '1px solid var(--color-border)',
          marginBottom: 'var(--space-6)'
        }}>
          {[
            { key: 'overview', label: 'System Overview', icon: Shield },
            { key: 'assignments', label: `Assignments (${assignments.length})`, icon: Truck },
            { key: 'holds', label: `Driver Holds (${activeHolds})`, icon: UserX },
            { key: 'stock', label: 'Stock Management', icon: Package }
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key as any)}
              style={{
                padding: 'var(--space-3) var(--space-4)',
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                borderBottom: `2px solid ${activeTab === key ? 'var(--color-primary)' : 'transparent'}`,
                color: activeTab === key ? 'var(--color-primary)' : 'var(--color-text-muted)',
                fontWeight: activeTab === key ? 600 : 400,
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)'
              }}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Morning Workflow Status */}
            <div className="card">
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                🌅 Morning Accountability Workflow
              </h2>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--space-4)' }}>
                <div style={{ 
                  padding: 'var(--space-3)', 
                  border: '1px solid var(--color-border)', 
                  borderRadius: 'var(--radius-2)' 
                }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-2)' }}>
                    📋 Step 1: Assignment
                  </h3>
                  <p style={{ fontSize: '0.875rem', opacity: 0.8 }}>
                    Driver clocks in → Assigned Lorry #123
                  </p>
                </div>
                
                <div style={{ 
                  padding: 'var(--space-3)', 
                  border: '1px solid var(--color-border)', 
                  borderRadius: 'var(--radius-2)' 
                }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-2)' }}>
                    📱 Step 2: Stock Scan
                  </h3>
                  <p style={{ fontSize: '0.875rem', opacity: 0.8 }}>
                    Mandatory: Scan all UIDs in lorry
                  </p>
                </div>
                
                <div style={{ 
                  padding: 'var(--space-3)', 
                  border: '1px solid var(--color-border)', 
                  borderRadius: 'var(--radius-2)' 
                }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-2)' }}>
                    ⚖️ Step 3: Accountability
                  </h3>
                  <p style={{ fontSize: '0.875rem', opacity: 0.8 }}>
                    Variance? Both drivers held. Clean? Orders unlocked.
                  </p>
                </div>
              </div>
            </div>

            {/* UID Action Types */}
            <div className="card">
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                🔄 Integrated Delivery Workflow
              </h2>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-3)' }}>
                {[
                  { 
                    action: 'DELIVER', 
                    desc: 'Giving item to customer', 
                    validation: 'Must scan UID that exists IN lorry',
                    color: 'var(--color-success)'
                  },
                  { 
                    action: 'COLLECT', 
                    desc: 'Taking item from customer', 
                    validation: 'Scan UID NOT in lorry',
                    color: 'var(--color-primary)'
                  },
                  { 
                    action: 'REPAIR', 
                    desc: 'Taking broken item', 
                    validation: 'Scan broken UID, mark for repair',
                    color: 'var(--color-warning)'
                  },
                  { 
                    action: 'SWAP', 
                    desc: 'Exchange items', 
                    validation: 'Scan 2 UIDs: giving + receiving',
                    color: 'var(--color-info)'
                  }
                ].map(({ action, desc, validation, color }) => (
                  <div key={action} style={{ 
                    padding: 'var(--space-3)', 
                    border: `1px solid ${color}30`, 
                    borderRadius: 'var(--radius-2)',
                    backgroundColor: `${color}10`
                  }}>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color, marginBottom: 'var(--space-2)' }}>
                      {action}
                    </h3>
                    <p style={{ fontSize: '0.75rem', marginBottom: 'var(--space-1)' }}>{desc}</p>
                    <p style={{ fontSize: '0.75rem', opacity: 0.7 }}>{validation}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Current System Status */}
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--space-4)' }}>
              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-3)' }}>
                  📊 Today&apos;s Activity
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ opacity: 0.8 }}>Assignments Created:</span>
                    <span style={{ fontWeight: 600 }}>{assignments.filter(a => 
                      new Date(a.assignment_date).toDateString() === new Date().toDateString()
                    ).length}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ opacity: 0.8 }}>Stock Verified:</span>
                    <span style={{ fontWeight: 600 }}>{assignments.filter(a => a.stock_verified).length}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ opacity: 0.8 }}>Holds Created:</span>
                    <span style={{ fontWeight: 600, color: 'var(--color-error)' }}>{activeHolds}</span>
                  </div>
                </div>
              </div>

              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-3)' }}>
                  🚨 Urgent Actions Required
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {pendingVerifications > 0 && (
                    <div style={{ 
                      padding: 'var(--space-2)', 
                      backgroundColor: 'var(--color-warning-light)',
                      borderRadius: 'var(--radius-1)',
                      fontSize: '0.875rem'
                    }}>
                      {pendingVerifications} assignments need stock verification
                    </div>
                  )}
                  {activeHolds > 0 && (
                    <div style={{ 
                      padding: 'var(--space-2)', 
                      backgroundColor: 'var(--color-error-light)',
                      borderRadius: 'var(--radius-1)',
                      fontSize: '0.875rem'
                    }}>
                      {activeHolds} driver holds require investigation
                    </div>
                  )}
                  {pendingVerifications === 0 && activeHolds === 0 && (
                    <div style={{ 
                      padding: 'var(--space-2)', 
                      backgroundColor: 'var(--color-success-light)',
                      borderRadius: 'var(--radius-1)',
                      fontSize: '0.875rem',
                      color: 'var(--color-success)'
                    }}>
                      ✅ All systems operational
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'assignments' && (
          <div className="space-y-4">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Lorry Assignments</h2>
              <button 
                className="btn btn-primary"
                onClick={() => setShowAssignmentForm(true)}
              >
                <Plus size={16} />
                Create Assignment
              </button>
            </div>
            
            <div className="card">
              <div style={{ overflowX: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Driver</th>
                      <th>Lorry ID</th>
                      <th>Status</th>
                      <th>Stock Verified</th>
                      <th>Stock Count</th>
                      <th>Notes</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.map((assignment) => (
                      <tr key={assignment.id}>
                        <td>{assignment.assignment_date}</td>
                        <td style={{ fontWeight: 500 }}>{assignment.driver_name}</td>
                        <td>
                          <span style={{ 
                            fontFamily: 'monospace', 
                            backgroundColor: 'var(--color-surface)',
                            padding: '2px 6px',
                            borderRadius: 'var(--radius-1)'
                          }}>
                            {assignment.lorry_id}
                          </span>
                        </td>
                        <td>
                          <span className={`status ${assignment.status.toLowerCase()}`}>
                            {assignment.status}
                          </span>
                        </td>
                        <td>
                          <span style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: 'var(--space-1)',
                            color: assignment.stock_verified ? 'var(--color-success)' : 'var(--color-warning)'
                          }}>
                            {assignment.stock_verified ? (
                              <>
                                <CheckCircle size={14} />
                                Verified
                              </>
                            ) : (
                              <>
                                <Clock size={14} />
                                Pending
                              </>
                            )}
                          </span>
                        </td>
                        <td>
                          {assignment.current_stock_count !== undefined ? (
                            <span>
                              {assignment.current_stock_count}
                              {assignment.expected_stock_count && 
                                ` / ${assignment.expected_stock_count}`
                              }
                            </span>
                          ) : (
                            <span style={{ opacity: 0.5 }}>-</span>
                          )}
                        </td>
                        <td>
                          <span style={{ fontSize: '0.875rem', opacity: 0.8 }}>
                            {assignment.notes || '-'}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                            <button className="btn btn-sm btn-outline">
                              <Eye size={12} />
                            </button>
                            <button className="btn btn-sm btn-outline">
                              <Edit size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'holds' && (
          <div className="space-y-4">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Driver Holds & Accountability</h2>
              <button 
                className="btn btn-primary"
                onClick={() => setShowHoldForm(true)}
              >
                <UserX size={16} />
                Create Hold
              </button>
            </div>
            
            <div className="card">
              <div style={{ overflowX: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Driver</th>
                      <th>Lorry</th>
                      <th>Reason</th>
                      <th>Description</th>
                      <th>Variance</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holds.map((hold) => (
                      <tr key={hold.id}>
                        <td style={{ fontWeight: 500 }}>{hold.driver_name}</td>
                        <td>
                          {hold.lorry_id ? (
                            <span style={{ 
                              fontFamily: 'monospace', 
                              backgroundColor: 'var(--color-surface)',
                              padding: '2px 6px',
                              borderRadius: 'var(--radius-1)'
                            }}>
                              {hold.lorry_id}
                            </span>
                          ) : (
                            <span style={{ opacity: 0.5 }}>-</span>
                          )}
                        </td>
                        <td>
                          <span style={{ 
                            backgroundColor: `var(--color-${hold.reason.includes('STOCK') ? 'warning' : 'error'}-light)`,
                            color: `var(--color-${hold.reason.includes('STOCK') ? 'warning' : 'error'})`,
                            padding: '2px 8px',
                            borderRadius: 'var(--radius-1)',
                            fontSize: '0.75rem',
                            fontWeight: 500
                          }}>
                            {hold.reason.replace('_', ' ')}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.875rem', maxWidth: '200px' }}>
                          {hold.description}
                        </td>
                        <td>
                          {hold.variance_count !== undefined ? (
                            <span style={{ 
                              color: hold.variance_count > 0 ? 'var(--color-error)' : 'var(--color-success)',
                              fontWeight: 500
                            }}>
                              {hold.variance_count > 0 ? `+${hold.variance_count}` : hold.variance_count} items
                            </span>
                          ) : (
                            <span style={{ opacity: 0.5 }}>-</span>
                          )}
                        </td>
                        <td>
                          <span className={`status ${hold.status.toLowerCase()}`}>
                            {hold.status}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.875rem', opacity: 0.8 }}>
                          {new Date(hold.created_at).toLocaleDateString()}
                        </td>
                        <td>
                          {hold.status === 'ACTIVE' && (
                            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                              <button 
                                className="btn btn-sm btn-success"
                                onClick={() => handleResolveHold(hold.id)}
                              >
                                Resolve
                              </button>
                              <button className="btn btn-sm btn-outline">
                                Investigate
                              </button>
                            </div>
                          )}
                          {hold.status === 'RESOLVED' && (
                            <span style={{ 
                              fontSize: '0.75rem', 
                              color: 'var(--color-success)',
                              display: 'flex',
                              alignItems: 'center',
                              gap: 'var(--space-1)'
                            }}>
                              <CheckCircle size={12} />
                              Resolved
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'stock' && (
          <div className="space-y-4">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Lorry Stock Management</h2>
              <button 
                className="btn btn-primary"
                onClick={() => setShowStockForm(true)}
              >
                <Package size={16} />
                Manage Stock
              </button>
            </div>
            
            <div className="card">
              <p style={{ opacity: 0.8, marginBottom: 'var(--space-4)' }}>
                Real-time lorry inventory tracking and management. Control loading/unloading operations with full audit trail.
              </p>
              
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--space-4)' }}>
                {/* Sample lorry stock data - this would come from API */}
                {['LRY001', 'LRY002', 'LRY003'].map((lorryId, index) => (
                  <div key={lorryId} className="card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
                      <h3 style={{ fontSize: '1rem', fontWeight: 600, fontFamily: 'monospace' }}>
                        {lorryId}
                      </h3>
                      <span style={{ 
                        fontSize: '0.75rem',
                        backgroundColor: index === 0 ? 'var(--color-success-light)' : 'var(--color-surface)',
                        color: index === 0 ? 'var(--color-success)' : 'var(--color-text-muted)',
                        padding: '2px 6px',
                        borderRadius: 'var(--radius-1)'
                      }}>
                        {index === 0 ? 'ACTIVE' : 'IDLE'}
                      </span>
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ opacity: 0.8 }}>Current Items:</span>
                        <span style={{ fontWeight: 600 }}>{45 + index * 10}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ opacity: 0.8 }}>Capacity:</span>
                        <span>100</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ opacity: 0.8 }}>Assigned Driver:</span>
                        <span style={{ fontSize: '0.875rem' }}>
                          {index === 0 ? 'John Doe' : '-'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ opacity: 0.8 }}>Last Verified:</span>
                        <span style={{ fontSize: '0.875rem' }}>Today 09:15</span>
                      </div>
                    </div>
                    
                    <div style={{ marginTop: 'var(--space-3)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border)' }}>
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button className="btn btn-sm btn-outline">
                          <Eye size={12} />
                          View
                        </button>
                        <button className="btn btn-sm btn-outline">
                          <Settings size={12} />
                          Manage
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
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

        {/* Hold Form Modal */}
        {showHoldForm && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h2>Create Driver Hold</h2>
                <button 
                  className="modal-close"
                  onClick={() => setShowHoldForm(false)}
                >
                  ×
                </button>
              </div>
              
              <form onSubmit={handleCreateHold}>
                <div className="form-group">
                  <label>Driver</label>
                  <select 
                    value={holdForm.driver_id}
                    onChange={(e) => setHoldForm({...holdForm, driver_id: e.target.value})}
                    required
                  >
                    <option value="">Select Driver</option>
                    {drivers.map(driver => (
                      <option key={driver.id} value={driver.id}>
                        {driver.name}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Hold Reason</label>
                  <select 
                    value={holdForm.reason}
                    onChange={(e) => setHoldForm({...holdForm, reason: e.target.value})}
                    required
                  >
                    <option value="STOCK_VARIANCE">Stock Variance</option>
                    <option value="MISSING_ITEMS">Missing Items</option>
                    <option value="DAMAGED_ITEMS">Damaged Items</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Lorry ID (Optional)</label>
                  <input
                    type="text"
                    value={holdForm.lorry_id}
                    onChange={(e) => setHoldForm({...holdForm, lorry_id: e.target.value})}
                    placeholder="e.g. LRY001"
                  />
                </div>
                
                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    value={holdForm.description}
                    onChange={(e) => setHoldForm({...holdForm, description: e.target.value})}
                    rows={3}
                    placeholder="Detailed description of the issue..."
                    required
                  />
                </div>
                
                <div className="modal-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowHoldForm(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Create Hold
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

(LorryManagementPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;