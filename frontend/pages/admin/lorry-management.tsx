import { useSession } from 'next-auth/react';
import { useEffect, useMemo, useState } from 'react';
import { request } from '../../utils/api';
import AdminLayout from '@/components/Layout/AdminLayout';

type Assignment = { id:number; lorry_id:string; driver_id:number; date:string; notes?:string|null; driver_name?: string; assignment_date?: string };
type Hold       = { id:number; driver_id:number; reason:string; status:'ACTIVE'|'RESOLVED'; created_at:string; driver_name?: string };
type Driver     = { id:number; name?:string|null; phone?:string|null };

async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await request<T>(path, init);
  } catch (e: any) {
    throw new Error(e.message || `Failed to fetch ${path}`);
  }
}

const asArray = <T,>(x: unknown): T[] => (Array.isArray(x) ? (x as T[]) : []);

function LorryManagementPage() {
  const { status } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [holds, setHolds] = useState<Hold[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);

  // Only block UI while NextAuth is resolving, otherwise show a friendly message
  if (status === 'loading') {
    return <div className="p-6 text-gray-500">Loading session…</div>;
  }
  if (status === 'unauthenticated') {
    return (
      <div className="p-6">
        <h1 className="text-xl font-semibold mb-2">Please sign in</h1>
        <p className="text-gray-600">You need admin access to view Lorry Management.</p>
      </div>
    );
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        // Never let one failure blank the page — use allSettled
        const [A, H, D] = await Promise.allSettled([
          api<Assignment[]>('/lorry-management/assignments'),
          api<Hold[]>('/lorry-management/holds'),
          api<Driver[]>('/drivers'),
        ]);

        if (!cancelled) {
          setAssignments(A.status === 'fulfilled' ? asArray<Assignment>(A.value) : []);
          setHolds(H.status === 'fulfilled' ? asArray<Hold>(H.value) : []);
          setDrivers(D.status === 'fulfilled' ? asArray<Driver>(D.value) : []);
          if ([A, H, D].some(r => r.status === 'rejected')) {
            const reasons = [A, H, D]
              .map(r => (r.status === 'rejected' ? (r.reason?.message || String(r.reason)) : null))
              .filter(Boolean)
              .join(' | ');
            setError(`Some data failed to load: ${reasons}`);
          }
        }
      } catch (e:any) {
        if (!cancelled) setError(e?.message || 'Failed to load data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []); // ✅ no unstable deps → no infinite loops

  const driverById = useMemo(() => {
    const m = new Map<number, Driver>();
    for (const dr of drivers) m.set(dr.id as number, dr);
    return m;
  }, [drivers]);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Lorry Management</h1>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3">{error}</div>
      )}

      {loading ? (
        <div className="text-gray-500">Loading data…</div>
      ) : (
        <>
          {/* Assignments */}
          <section>
            <h2 className="text-lg font-medium mb-2">Assignments (Today)</h2>
            {assignments.length === 0 ? (
              <div className="text-gray-500 text-sm">No assignments found.</div>
            ) : (
              <table className="min-w-full border rounded overflow-hidden text-sm">
                <thead className="bg-gray-50 text-left">
                  <tr><th className="p-2">ID</th><th className="p-2">Date</th><th className="p-2">Lorry</th><th className="p-2">Driver</th><th className="p-2">Notes</th></tr>
                </thead>
                <tbody>
                  {assignments.map(a => (
                    <tr key={a.id} className="border-t">
                      <td className="p-2">{a.id}</td>
                      <td className="p-2">{a.date || a.assignment_date || '-'}</td>
                      <td className="p-2">{a.lorry_id}</td>
                      <td className="p-2">{a.driver_name || driverById.get(a.driver_id)?.name || a.driver_id}</td>
                      <td className="p-2">{a.notes ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* Holds */}
          <section>
            <h2 className="text-lg font-medium mb-2">Driver Holds</h2>
            {holds.length === 0 ? (
              <div className="text-gray-500 text-sm">No active holds.</div>
            ) : (
              <table className="min-w-full border rounded overflow-hidden text-sm">
                <thead className="bg-gray-50 text-left">
                  <tr><th className="p-2">ID</th><th className="p-2">Driver</th><th className="p-2">Reason</th><th className="p-2">Status</th><th className="p-2">Created</th></tr>
                </thead>
                <tbody>
                  {holds.map(h => (
                    <tr key={h.id} className="border-t">
                      <td className="p-2">{h.id}</td>
                      <td className="p-2">{h.driver_name || driverById.get(h.driver_id)?.name || h.driver_id}</td>
                      <td className="p-2">{h.reason}</td>
                      <td className="p-2">{h.status}</td>
                      <td className="p-2">{new Date(h.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}

(LorryManagementPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

export default LorryManagementPage;