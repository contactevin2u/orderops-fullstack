import React from 'react';
import Card from '@/components/Card';
import Button from '@/components/ui/button';
import TermsModal from '@/components/ui/TermsModal';
import { useTranslation } from 'react-i18next';
import { parseAdvancedMessage, createOrderFromParsed, createParseJob, getJobStatus, listJobs, normalizeParsedForOrder } from '@/lib/api';
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

export default function IntakePage() {
  const { t } = useTranslation();
  const [text, setText] = React.useState('');
  const [parsed, setParsed] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState('');
  const [msg, setMsg] = React.useState('');
  const [termsOpen, setTermsOpen] = React.useState(false);
  const [accepted, setAccepted] = React.useState(false);
  
  // True non-blocking processing state
  const [useBackground, setUseBackground] = React.useState(true);
  const [allJobs, setAllJobs] = React.useState<Job[]>([]);
  const [sessionId] = React.useState(() => crypto.randomUUID());

  // Load recent jobs on mount and poll for updates
  React.useEffect(() => {
    loadRecentJobs();
    
    // Poll all jobs every 3 seconds to show real-time updates
    const interval = setInterval(loadRecentJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadRecentJobs = React.useCallback(async () => {
    try {
      const response = await listJobs(sessionId, 10);
      setAllJobs(response.jobs || []);
    } catch (e) {
      console.error('Failed to load jobs:', e);
    }
  }, [sessionId]);

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

  async function onSubmit() {
    if (!text.trim()) return;
    
    setBusy(true); setErr(''); setMsg('');
    
    if (useBackground) {
      // True non-blocking: Submit and forget
      try {
        const response = await createParseJob(text.trim(), sessionId);
        
        // Clear input immediately - user can continue with next message
        setText('');
        setMsg(`✅ Message submitted! Processing in background...`);
        
        // Refresh jobs list to show new submission
        setTimeout(loadRecentJobs, 500);
        
      } catch (e: any) {
        setErr(e?.message || 'Failed to submit message');
      } finally {
        setBusy(false);
        // Clear success message after 3 seconds
        setTimeout(() => setMsg(''), 3000);
      }
    } else {
      // Legacy synchronous parsing (kept for compatibility)
      try {
        const res = await parseAdvancedMessage(text);
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
              Submit & continue • Results appear below • Orders created automatically
            </span>
          )}
        </div>

        <div className="cluster" style={{ justifyContent: 'flex-end' }}>
          <Button disabled={busy || !text.trim()} onClick={onSubmit}>
            {useBackground ? 'Submit Message' : t('intake.parse')}
          </Button>
          {!useBackground && (
            <Button variant="secondary" disabled={busy || !toPost} onClick={onCreate}>
              {t('intake.create')}
            </Button>
          )}
        </div>
        {err && <p style={{ fontSize: '0.875rem', color: '#ff4d4f' }}>{err}</p>}
        {msg && <p style={{ fontSize: '0.875rem', color: '#16a34a' }}>{msg}</p>}
      </Card>
      
      {/* Show parsed JSON in legacy mode */}
      {!useBackground && toPost && (
        <Card className="stack">
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>{JSON.stringify(toPost, null, 2)}</pre>
        </Card>
      )}

      {/* Processing Queue - All Jobs */}
      {useBackground && (
        <Card>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '1.25rem', fontWeight: 600 }}>
            Processing Queue
            {allJobs.length > 0 && (
              <span style={{ fontSize: '0.875rem', fontWeight: 400, color: '#6b7280', marginLeft: 8 }}>
                ({allJobs.filter(j => j.status === 'pending' || j.status === 'processing').length} processing, {allJobs.filter(j => j.status === 'completed').length} completed)
              </span>
            )}
          </h3>
          
          {allJobs.length === 0 ? (
            <div style={{ 
              padding: '24px', 
              textAlign: 'center', 
              color: '#6b7280',
              fontSize: '0.875rem'
            }}>
              No messages submitted yet. Submit a WhatsApp message above to get started.
            </div>
          ) : (
            <div className="stack" style={{ gap: 8 }}>
              {allJobs.map((job) => {
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
                    padding: 12,
                    backgroundColor: job.status === 'failed' ? '#fef2f2' : 
                                      job.status === 'completed' ? '#f0fdf4' : 
                                      job.status === 'processing' ? '#eff6ff' : '#fefce8',
                    borderRadius: 6,
                    border: '1px solid #e5e7eb',
                    borderLeft: `4px solid ${getStatusColor(job.status)}`
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 18 }}>{getStatusIcon(job.status)}</span>
                      <span style={{ fontSize: 14, color: getStatusColor(job.status), fontWeight: 600, textTransform: 'capitalize' }}>
                        {job.status}
                      </span>
                    </div>
                    <span style={{ fontSize: 11, color: '#6b7280' }}>
                      {new Date(job.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  <div style={{ fontSize: 13, color: '#374151', marginBottom: 8 }}>
                    {job.status === 'completed' ? getJobResultMessage(job) : job.progress_message}
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
