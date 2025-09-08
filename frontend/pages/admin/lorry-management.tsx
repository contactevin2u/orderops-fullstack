// frontend/pages/admin/lorry-management.tsx
import { useSession } from 'next-auth/react';
import { useEffect, useMemo, useState } from 'react';
import { request } from '../../utils/api';
import AdminLayout from '@/components/Layout/AdminLayout';

type Assignment = { id:number; lorry_id:string; driver_id:number; date:string; notes?:string|null; driver_name?: string; assignment_date?: string };
type Hold       = { id:number; driver_id:number; reason:string; status:'ACTIVE'|'RESOLVED'; created_at:string; driver_name?: string };
type Driver     = { id:number; name?:string|null; phone?:string|null };

async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  try { return await request<T>(path, init); }
  catch (e: any) { throw new Error(e.message || `Failed to fetch ${path}`); }
}

const asArray = <T,>(x: unknown): T[] => (Array.isArray(x) ? (x as T[]) : []);

function LorryManagementPage() {
  const { status } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [holds, setHolds] = useState<Hold[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);

  // ✅ Hooks must always run, so keep them above any conditional return
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [A, H, D] = await Promise.allSettled([
          api<Assignment[]>('/lorry-management/assignments'),
          api<Hold[]>('/lorry-management/holds'),
          api<Driver[]>('/drivers'),
        ]);
        if (!cancelled) {
          setAssignments(A.status === 'fulfilled' ? asArray<Assignment>(A.value) : []);
          setHolds(H.status === 'fulfilled' ? asArray<Hold>(H.value) : []);
          setDrivers(D.status === 'fulfilled' ? asArray<Driver>(D.value) : []);
          if ([A,H,D].some(r => r.status === 'rejected')) {
            const reasons = [A,H,D].map(r => (r.status === 'rejected'
              ? (r.reason?.message || String(r.reason)) : null)).filter(Boolean).join(' | ');
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
  }, []);

  const driverById = useMemo(() => {
    const m = new Map<number, Driver>();
    for (const dr of drivers) m.set(dr.id as number, dr);
    return m;
  }, [drivers]);

  // 🔻 Render different UI states without returning before hooks run
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Lorry Management</h1>

      {status === 'loading' && (
        <div className="text-gray-500">Loading session…</div>
      )}

      {status === 'unauthenticated' && (
        <div>
          <h1 className="text-xl font-semibold mb-2">Please sign in</h1>
          <p className="text-gray-600">You need admin access to view Lorry Management.</p>
        </div>
      )}

      {status === 'authenticated' && (
        <>
          {error && (
            <div className="rounded border border-red-200 bg-red-50 text-red-700 p-3">{error}</div>
          )}

          {loading ? (
            <div className="text-gray-500">Loading data…</div>
          ) : (
            <>
              {/* Assignments */}
              {/* ... keep your existing table JSX unchanged ... */}

              {/* Holds */}
              {/* ... keep your existing table JSX unchanged ... */}
            </>
          )}
        </>
      )}
    </div>
  );
}

(LorryManagementPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
export default LorryManagementPage;
