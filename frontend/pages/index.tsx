import React from 'react';
import Card from '@/components/Card';
import Button from '@/components/ui/button';
import TermsModal from '@/components/ui/TermsModal';
import { useTranslation } from 'react-i18next';
import { parseMessage, createOrderFromParsed, createParseJob, getJobStatus, listJobs } from '@/utils/api';
import Link from 'next/link';

function normalizeParsedForOrder(input: any) {
  if (!input) return null;
  const payload = typeof input === 'object' && 'parsed' in input ? input.parsed : input;
  const core = payload && payload.data ? payload.data : payload;

  if (core?.customer && core?.order) return { customer: core.customer, order: core.order };
  if (!core) return null;
  if (!core.customer && (core.order || core.items)) {
    return { customer: core.customer || {}, order: core.order || core };
  }
  return core;
}

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

export default function IntakePage() {
  const { t } = useTranslation();
  const [text, setText] = React.useState('');
  const [parsed, setParsed] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState('');
  const [msg, setMsg] = React.useState('');
  const [termsOpen, setTermsOpen] = React.useState(false);
  const [accepted, setAccepted] = React.useState(false);
  
  // Background processing state
  const [useBackground, setUseBackground] = React.useState(true);
  const [currentJob, setCurrentJob] = React.useState<Job | null>(null);
  const [recentJobs, setRecentJobs] = React.useState<Job[]>([]);
  const [sessionId] = React.useState(() => crypto.randomUUID());

  // Load recent jobs on mount
  React.useEffect(() => {
    loadRecentJobs();
  }, []);

  const loadRecentJobs = React.useCallback(async () => {
    try {
      const response = await listJobs(sessionId, 5);
      setRecentJobs(response.jobs || []);
    } catch (e) {
      console.error('Failed to load recent jobs:', e);
    }
  }, [sessionId]);

  // Poll current job status
  React.useEffect(() => {
    if (!currentJob || (currentJob.status !== 'pending' && currentJob.status !== 'processing')) {
      return;
    }

    const pollJob = async () => {
      try {
        const updatedJob = await getJobStatus(currentJob.id);
        setCurrentJob(updatedJob);
        
        if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
          loadRecentJobs(); // Refresh recent jobs list
          
          if (updatedJob.status === 'completed') {
            setMsg(getJobResultMessage(updatedJob));
          } else {
            setErr(updatedJob.error_message || 'Processing failed');
          }
        }
      } catch (e) {
        console.error('Failed to poll job status:', e);
      }
    };

    const interval = setInterval(pollJob, 2000);
    return () => clearInterval(interval);
  }, [currentJob, loadRecentJobs]);

  const getJobResultMessage = (job: Job) => {
    if (!job.result_data) return 'Processing completed';
    
    const result = job.result_data;
    if (result.status === 'success') {
      if (result.type === 'delivery') {
        return `✅ Order created automatically: ${result.order_code}`;
      } else if (result.type === 'return') {
        return `✅ Applied ${result.adjustment_type.toLowerCase()} to ${result.mother_order_code}`;
      }
    } else if (result.status === 'order_not_found') {
      return '⚠️ Could not find original order for adjustment';
    } else if (result.status === 'unclear') {
      return '❓ Message unclear - manual review needed';
    }
    
    return result.message || 'Processing completed';
  };

  async function onParse() {
    setBusy(true); setErr(''); setMsg('');
    
    if (useBackground) {
      // Use background processing
      try {
        const response = await createParseJob(text.trim(), sessionId);
        
        const newJob: Job = {
          id: response.job_id,
          status: 'pending',
          progress: 0,
          progress_message: 'Queued for processing...',
          created_at: new Date().toISOString()
        };
        
        setCurrentJob(newJob);
        setMsg('Processing in background...');
        setText(''); // Clear input for next message
      } catch (e: any) {
        setErr(e?.message || 'Failed to queue processing');
      } finally {
        setBusy(false);
      }
    } else {
      // Use original synchronous parsing
      try {
        const res = await parseMessage(text);
        setParsed(res);
        setMsg('Parsed successfully');
      } catch (e: any) {
        setErr(e?.message || 'Parse failed');
      } finally {
        setBusy(false);
      }
    }
  }

  async function createOrder() {
    setBusy(true); setErr(''); setMsg('');
    try {
      const out = await createOrderFromParsed(parsed);
      setMsg('Order created: ID ' + (out?.id || out?.order_id || JSON.stringify(out)));
    } catch (e: any) {
      setErr(e?.message || 'Create failed');
    } finally {
      setBusy(false);
    }
  }

  async function onCreate() {
    if (!accepted) {
      setTermsOpen(true);
      return;
    }
    await createOrder();
  }

  const toPost = normalizeParsedForOrder(parsed);

  return (
    <div className="stack" style={{ maxWidth: '48rem', margin: '0 auto' }}>
      <Card className="stack">
        <details>
          <summary>{t('help.intake.title')}</summary>
          <p>{t('help.intake.body')}</p>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{t('help.intake.sample')}</pre>
        </details>
        <textarea
          className="textarea"
          rows={10}
          placeholder={t('intake.placeholder')}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {/* Processing mode toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
            <input 
              type="checkbox" 
              checked={useBackground} 
              onChange={(e) => setUseBackground(e.target.checked)}
            />
            Smart Auto-Processing (recommended)
          </label>
          {useBackground && (
            <span style={{ fontSize: 12, color: '#6b7280' }}>
              Orders created automatically • Handles returns & adjustments
            </span>
          )}
        </div>

        <div className="cluster" style={{ justifyContent: 'flex-end' }}>
          <Button disabled={busy || !text} onClick={onParse}>
            {useBackground ? 'Process Message' : t('intake.parse')}
          </Button>
          {!useBackground && (
            <Button variant="secondary" disabled={busy || !toPost} onClick={onCreate}>
              {t('intake.create')}
            </Button>
          )}
        </div>
        {err && <p style={{ fontSize: '0.875rem', color: '#ff4d4f' }}>{err}</p>}
        {msg && <p style={{ fontSize: '0.875rem', color: '#16a34a' }}>{msg}</p>}

        {/* Current job processing status */}
        {useBackground && currentJob && (currentJob.status === 'pending' || currentJob.status === 'processing') && (
          <div style={{ 
            marginTop: 16, 
            padding: 12, 
            backgroundColor: '#f8fafc', 
            borderRadius: 6,
            border: '1px solid #e2e8f0'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 16 }}>
                {currentJob.status === 'pending' ? '⏳' : '⚙️'}
              </span>
              <span style={{ fontSize: 14, fontWeight: 500, textTransform: 'capitalize' }}>
                {currentJob.status}
              </span>
            </div>
            
            {/* Progress bar */}
            <div style={{
              width: '100%',
              height: 6,
              backgroundColor: '#e5e7eb',
              borderRadius: 3,
              overflow: 'hidden',
              marginBottom: 8
            }}>
              <div style={{
                width: `${Math.max(currentJob.progress, 5)}%`,
                height: '100%',
                backgroundColor: currentJob.status === 'processing' ? '#3b82f6' : '#fbbf24',
                transition: 'width 0.3s ease'
              }} />
            </div>
            
            <div style={{ fontSize: 13, color: '#6b7280' }}>
              {currentJob.progress_message}
            </div>
          </div>
        )}
      </Card>
      
      {/* Show parsed JSON in legacy mode */}
      {!useBackground && toPost && (
        <Card className="stack">
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>{JSON.stringify(toPost, null, 2)}</pre>
        </Card>
      )}

      {/* Recent processing results */}
      {useBackground && recentJobs.length > 0 && (
        <Card>
          <h3 style={{ margin: '0 0 12px 0' }}>Recent Processing</h3>
          <div className="stack" style={{ gap: 8 }}>
            {recentJobs.slice(0, 3).map((job) => {
              const getStatusColor = (status: JobStatus) => {
                switch (status) {
                  case 'completed': return '#10b981';
                  case 'failed': return '#ef4444';
                  case 'processing': return '#3b82f6';
                  case 'pending': return '#fbbf24';
                  default: return '#6b7280';
                }
              };

              const getStatusIcon = (status: JobStatus) => {
                switch (status) {
                  case 'completed': return '✅';
                  case 'failed': return '❌';
                  case 'processing': return '⚙️';
                  case 'pending': return '⏳';
                  default: return '❓';
                }
              };

              return (
                <div
                  key={job.id}
                  style={{
                    padding: 8,
                    backgroundColor: job.status === 'failed' ? '#fef2f2' : 
                                      job.status === 'completed' ? '#f0fdf4' : '#f8fafc',
                    borderRadius: 4,
                    border: '1px solid #e5e7eb'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span>{getStatusIcon(job.status)}</span>
                    <span style={{ fontSize: 13, color: getStatusColor(job.status), fontWeight: 500 }}>
                      {job.status === 'completed' ? getJobResultMessage(job) : job.progress_message}
                    </span>
                  </div>

                  {/* Show order links for completed jobs */}
                  {job.status === 'completed' && job.result_data?.status === 'success' && (
                    <div style={{ marginTop: 4 }}>
                      {job.result_data.type === 'delivery' && job.result_data.order_id && (
                        <Link href={`/orders/${job.result_data.order_id}`}>
                          <Button variant="secondary" style={{ fontSize: 11, padding: '4px 8px' }}>
                            View Order {job.result_data.order_code}
                          </Button>
                        </Link>
                      )}
                      {job.result_data.type === 'return' && job.result_data.mother_order_id && (
                        <Link href={`/orders/${job.result_data.mother_order_id}`}>
                          <Button variant="secondary" style={{ fontSize: 11, padding: '4px 8px' }}>
                            View Order {job.result_data.mother_order_code}
                          </Button>
                        </Link>
                      )}
                    </div>
                  )}

                  {job.status === 'failed' && job.error_message && (
                    <div style={{ fontSize: 11, color: '#dc2626', marginTop: 4 }}>
                      Error: {job.error_message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
      <TermsModal
        open={termsOpen}
        onClose={() => setTermsOpen(false)}
        onAccept={() => {
          setAccepted(true);
          setTermsOpen(false);
          createOrder();
        }}
      />
    </div>
  );
}
