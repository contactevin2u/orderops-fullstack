import React from 'react';
import Card from '@/components/Card';
import Button from '@/components/ui/button';
import { createParseJob, getJobStatus, listJobs } from '@/utils/api';
import Link from 'next/link';

type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

interface Job {
  id: string;
  status: JobStatus;
  progress: number;
  progress_message: string;
  error_message?: string;
  result_data?: any;
  created_at: string;
}

export default function BackgroundParsePage() {
  const [text, setText] = React.useState('');
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [sessionId] = React.useState(() => crypto.randomUUID());
  
  // Polling for job updates
  const activeJobsRef = React.useRef<Set<string>>(new Set());
  
  const loadJobs = React.useCallback(async () => {
    try {
      const response = await listJobs(sessionId);
      setJobs(response.jobs || []);
      
      // Update active jobs set
      const activeJobs = response.jobs?.filter((job: Job) => 
        job.status === 'pending' || job.status === 'processing'
      ).map((job: Job) => job.id) || [];
      
      activeJobsRef.current = new Set(activeJobs);
    } catch (e) {
      console.error('Failed to load jobs:', e);
    }
  }, [sessionId]);

  // Poll active jobs for updates
  React.useEffect(() => {
    const pollJobs = async () => {
      if (activeJobsRef.current.size === 0) return;
      
      const updatedJobs = await Promise.allSettled(
        Array.from(activeJobsRef.current).map(jobId => getJobStatus(jobId))
      );
      
      let hasUpdates = false;
      const newJobs = [...jobs];
      
      updatedJobs.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          const jobId = Array.from(activeJobsRef.current)[index];
          const jobIndex = newJobs.findIndex(j => j.id === jobId);
          if (jobIndex >= 0) {
            newJobs[jobIndex] = result.value;
            hasUpdates = true;
            
            // Remove from active set if completed/failed
            if (result.value.status === 'completed' || result.value.status === 'failed') {
              activeJobsRef.current.delete(jobId);
            }
          }
        }
      });
      
      if (hasUpdates) {
        setJobs(newJobs);
      }
    };

    // Poll every 2 seconds if there are active jobs
    const interval = setInterval(pollJobs, 2000);
    return () => clearInterval(interval);
  }, [jobs]);

  // Load jobs on mount
  React.useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || loading) return;
    
    setLoading(true);
    try {
      const response = await createParseJob(text.trim(), sessionId);
      
      // Add new job to the list immediately
      const newJob: Job = {
        id: response.job_id,
        status: 'pending',
        progress: 0,
        progress_message: 'Queued for processing...',
        created_at: new Date().toISOString()
      };
      
      setJobs([newJob, ...jobs]);
      activeJobsRef.current.add(response.job_id);
      
      setText(''); // Clear the input
    } catch (e: any) {
      alert(`Failed to queue job: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: JobStatus) => {
    switch (status) {
      case 'pending': return '#fbbf24'; // yellow
      case 'processing': return '#3b82f6'; // blue
      case 'completed': return '#10b981'; // green
      case 'failed': return '#ef4444'; // red
      default: return '#6b7280'; // gray
    }
  };

  const getStatusIcon = (status: JobStatus) => {
    switch (status) {
      case 'pending': return '⏳';
      case 'processing': return '⚙️';
      case 'completed': return '✅';
      case 'failed': return '❌';
      default: return '❓';
    }
  };

  const formatResultMessage = (job: Job) => {
    if (!job.result_data) return '';
    
    const result = job.result_data;
    if (result.status === 'success') {
      if (result.type === 'delivery') {
        return `📦 Created order: ${result.order_code}`;
      } else if (result.type === 'return') {
        return `🔄 Applied ${result.adjustment_type.toLowerCase()} to ${result.mother_order_code}`;
      }
    } else if (result.status === 'order_not_found') {
      return '🔍 Could not find original order';
    } else if (result.status === 'unclear') {
      return '❓ Message unclear - needs manual review';
    }
    
    return result.message || '';
  };

  return (
    <div className="container stack" style={{ maxWidth: '64rem' }}>
      <Card>
        <h1 style={{ marginTop: 0 }}>Background Message Parser</h1>
        <p style={{ color: '#6b7280', marginBottom: 24 }}>
          Paste WhatsApp messages and they'll be processed automatically in the background. 
          Orders will be created automatically for deliveries, and adjustments applied for returns.
        </p>

        <form onSubmit={handleSubmit} className="stack" style={{ marginBottom: 32 }}>
          <textarea
            className="input"
            rows={6}
            placeholder="Paste WhatsApp message here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{ fontSize: 16, fontFamily: 'monospace', resize: 'vertical' }}
          />
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Button 
              type="submit" 
              disabled={!text.trim() || loading}
              style={{ minWidth: 120 }}
            >
              {loading ? 'Queuing...' : 'Parse Message'}
            </Button>
            <span style={{ color: '#6b7280', fontSize: 14 }}>
              No manual order creation needed - everything happens automatically
            </span>
          </div>
        </form>
      </Card>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>Processing Queue</h2>
          <Button variant="secondary" onClick={loadJobs} style={{ fontSize: 12 }}>
            Refresh
          </Button>
        </div>

        {jobs.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>
            No messages processed yet. Paste a message above to get started.
          </div>
        ) : (
          <div className="stack">
            {jobs.map((job) => (
              <div 
                key={job.id}
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: 8,
                  padding: 16,
                  backgroundColor: job.status === 'failed' ? '#fef2f2' : 
                                    job.status === 'completed' ? '#f0fdf4' : 'white'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 18 }}>{getStatusIcon(job.status)}</span>
                    <span style={{ 
                      fontWeight: 'bold', 
                      color: getStatusColor(job.status),
                      textTransform: 'capitalize'
                    }}>
                      {job.status}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, color: '#6b7280' }}>
                    {new Date(job.created_at).toLocaleString()}
                  </span>
                </div>

                {/* Progress bar for processing jobs */}
                {(job.status === 'processing' || job.status === 'pending') && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{
                      width: '100%',
                      height: 8,
                      backgroundColor: '#e5e7eb',
                      borderRadius: 4,
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${Math.max(job.progress, 5)}%`,
                        height: '100%',
                        backgroundColor: getStatusColor(job.status),
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                  </div>
                )}

                <div style={{ fontSize: 14, marginBottom: 8 }}>
                  {job.progress_message}
                </div>

                {job.status === 'completed' && job.result_data && (
                  <div style={{ 
                    fontSize: 14, 
                    color: '#059669',
                    fontWeight: 500,
                    marginBottom: 8
                  }}>
                    {formatResultMessage(job)}
                  </div>
                )}

                {job.status === 'failed' && job.error_message && (
                  <div style={{ 
                    fontSize: 14, 
                    color: '#dc2626',
                    backgroundColor: '#fef2f2',
                    padding: 8,
                    borderRadius: 4,
                    marginBottom: 8
                  }}>
                    Error: {job.error_message}
                  </div>
                )}

                {/* Show order link for completed deliveries */}
                {job.status === 'completed' && 
                 job.result_data?.status === 'success' && 
                 job.result_data?.type === 'delivery' && 
                 job.result_data?.order_id && (
                  <div>
                    <Link href={`/orders/${job.result_data.order_id}`}>
                      <Button variant="secondary" style={{ fontSize: 12 }}>
                        View Order {job.result_data.order_code}
                      </Button>
                    </Link>
                  </div>
                )}

                {/* Show mother order link for completed returns */}
                {job.status === 'completed' && 
                 job.result_data?.status === 'success' && 
                 job.result_data?.type === 'return' && 
                 job.result_data?.mother_order_id && (
                  <div>
                    <Link href={`/orders/${job.result_data.mother_order_id}`}>
                      <Button variant="secondary" style={{ fontSize: 12 }}>
                        View Order {job.result_data.mother_order_code}
                      </Button>
                    </Link>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}