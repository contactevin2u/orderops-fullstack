import React from 'react';
import Image from 'next/image';
import AdminLayout from '@/components/admin/AdminLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDrivers, listDriverOrders, addPayment, markSuccess, updateCommission } from '@/utils/api';
import StatusBadge from '@/components/StatusBadge';
import PodPhotosViewer from '@/components/PodPhotosViewer';
import { 
  DollarSign, 
  CheckCircle, 
  AlertTriangle,
  Truck,
  Calendar,
  Eye,
  Image as ImageIcon,
  CreditCard,
  Banknote,
  Smartphone,
  FileText,
  Clock,
  Shield,
  RefreshCw,
  Search,
  Filter,
  Download,
  TrendingUp,
  Users
} from 'lucide-react';

export default function DriverCommissionsPage() {
  const qc = useQueryClient();
  const [driverId, setDriverId] = React.useState<string>('');
  const [month, setMonth] = React.useState<string>(new Date().toISOString().slice(0, 7)); // yyyy-mm

  const driversQuery = useQuery({
    queryKey: ['drivers'],
    queryFn: listDrivers,
  });
  const rowsQuery = useQuery({
    queryKey: ['driver-orders', driverId, month],
    queryFn: () => (driverId ? listDriverOrders(Number(driverId), month) : Promise.resolve([])),
    enabled: !!driverId,
  });
  const drivers = driversQuery.data || [];
  const rows = rowsQuery.data || [];

  // Separate mutations for better control
  const updateCommissionMutation = useMutation({
    mutationFn: async ({ orderId, amount }: any) => updateCommission(orderId, Number(amount)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['driver-orders', driverId, month] }),
  });

  const releaseCommissionMutation = useMutation({
    mutationFn: async ({ orderId, amount, method, reference }: any) => {
      // First add payment if provided
      if (method && amount) {
        await addPayment({
          order_id: orderId,
          amount: Number(amount),
          method,
          reference,
          category: 'INITIAL',
          idempotencyKey: crypto.randomUUID(),
        });
      }
      // Then mark as success (this releases commission)
      await markSuccess(orderId);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['driver-orders', driverId, month] }),
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600">
                <DollarSign className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Driver Commission Center
                </h1>
                <p className="mt-1 text-gray-600 dark:text-gray-300">
                  Review deliveries, verify proof and release driver commissions
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-8">
          <div className="flex items-center space-x-3 mb-4">
            <Filter className="h-5 w-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Filters</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <Truck className="inline h-4 w-4 mr-1" />
                Select Driver
              </label>
              <select
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-colors"
                value={driverId}
                onChange={(e) => setDriverId(e.target.value)}
              >
                <option value="">Select driver…</option>
                {drivers.map((d: any) => (
                  <option key={d.id} value={d.id}>
                    {d.name || `Driver ${d.id}`}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <Calendar className="inline h-4 w-4 mr-1" />
                Select Month
              </label>
              <input
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-colors"
                type="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Orders List */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Commission Review</h2>
              {!rowsQuery.isLoading && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {rows.length} orders loaded
                </span>
              )}
            </div>
          </div>

          <div className="p-6">
            {rowsQuery.isLoading && (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-green-600 border-t-transparent"></div>
                <p className="mt-4 text-gray-600 dark:text-gray-400">Loading orders...</p>
              </div>
            )}

            {rowsQuery.isError && (
              <div className="text-center py-12">
                <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
                <p className="text-red-600 dark:text-red-400 mb-4">Failed to load orders</p>
                <button
                  onClick={() => rowsQuery.refetch()}
                  className="inline-flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </button>
              </div>
            )}

            {!rowsQuery.isLoading && rows.length === 0 && (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">No orders found for the selected criteria</p>
              </div>
            )}

            {!rowsQuery.isLoading && rows.length > 0 && (
              <div className="space-y-4">
                {rows.map((o: any) => (
                  <OrderCard
                    key={o.id}
                    order={o}
                    onUpdateCommission={updateCommissionMutation.mutateAsync}
                    onReleaseCommission={releaseCommissionMutation.mutateAsync}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function OrderCard({ order: o, onUpdateCommission, onReleaseCommission }: { 
  order: any; 
  onUpdateCommission: any; 
  onReleaseCommission: any; 
}) {
  const [method, setMethod] = React.useState('');
  const [amount, setAmount] = React.useState('');
  const [reference, setReference] = React.useState('');
  const [commission, setCommission] = React.useState(
    String(o?.trip?.commission?.computed_amount ?? o?.commission ?? '')
  );
  const [msg, setMsg] = React.useState('');
  const [isProcessing, setIsProcessing] = React.useState(false);

  // Get PoD photo URLs - support both new multiple photos and legacy single photo
  const podPhotoUrls = o?.trip?.pod_photo_urls || [];
  const legacyPodUrl = o?.trip?.pod_photo_url || o?.pod_photo_url;
  const hasAnyPodPhoto = podPhotoUrls.length > 0 || !!legacyPodUrl;
  
  const canRelease =
    o.status === 'DELIVERED' &&
    hasAnyPodPhoto &&
    commission &&
    ((method === '' && amount === '') || (!!method && !!amount));

  // Auto-save commission when it changes (debounced)
  const debouncedUpdateCommission = React.useMemo(
    () => {
      let timeoutId: NodeJS.Timeout;
      return (newCommission: string) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(async () => {
          if (newCommission && newCommission !== String(o?.trip?.commission?.computed_amount ?? o?.commission ?? '')) {
            try {
              await onUpdateCommission({ orderId: o.id, amount: newCommission });
            } catch (e: any) {
              console.error('Failed to update commission:', e);
            }
          }
        }, 1000);
      };
    },
    [o.id, onUpdateCommission, o?.trip?.commission?.computed_amount, o?.commission]
  );

  React.useEffect(() => {
    debouncedUpdateCommission(commission);
  }, [commission, debouncedUpdateCommission]);

  const handleReleaseCommission = async () => {
    setIsProcessing(true);
    try {
      await onReleaseCommission({ orderId: o.id, amount, method, reference });
      setMsg('✅ Commission released successfully!');
      setMethod('');
      setAmount('');
      setReference('');
    } catch (e: any) {
      setMsg(`❌ ${e?.message || 'Error releasing commission'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      {/* Order Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center h-10 w-10 rounded-full bg-blue-500 text-white font-semibold">
            {o.code ? o.code.slice(-2) : o.id.toString().slice(-2)}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Order #{o.code || o.id}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              <StatusBadge value={o.status} />
              {hasAnyPodPhoto && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200">
                  <ImageIcon className="h-3 w-3 mr-1" />
                  POD Available
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-500 dark:text-gray-400">Commission</div>
          <div className="text-xl font-bold text-gray-900 dark:text-white">
            RM {commission || '0'}
          </div>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Proof of Delivery */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <ImageIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h4 className="font-medium text-gray-900 dark:text-white">Proof of Delivery</h4>
          </div>
          {hasAnyPodPhoto ? (
            <PodPhotosViewer 
              podPhotoUrls={podPhotoUrls}
              legacyPodUrl={legacyPodUrl}
            />
          ) : (
            <div className="text-center py-8 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
              <AlertTriangle className="h-8 w-8 text-amber-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">No POD photo available</p>
            </div>
          )}
        </div>

        {/* Payment Information */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <CreditCard className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h4 className="font-medium text-gray-900 dark:text-white">Payment Confirmation</h4>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Payment Method
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                <option value="">No payment required</option>
                <option value="Cash">💵 Cash</option>
                <option value="Online">💳 Online Payment</option>
              </select>
            </div>
            {method && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Amount (RM)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="0.00"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Reference (Optional)
                  </label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="Transaction ID, receipt number, etc."
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>
        </div>

        {/* Commission Settings */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <DollarSign className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h4 className="font-medium text-gray-900 dark:text-white">Commission Amount</h4>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Driver Commission (RM)
            </label>
            <input
              type="number"
              step="0.01"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="0.00"
              value={commission}
              onChange={(e) => setCommission(e.target.value)}
            />
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              💡 Auto-saves as you type
            </p>
          </div>
        </div>
      </div>

      {/* Action Section */}
      <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* Validation Checklist */}
            <div className="flex items-center space-x-4 text-sm">
              <div className={`flex items-center space-x-1 ${
                o.status === 'DELIVERED' ? 'text-green-600 dark:text-green-400' : 'text-gray-400'
              }`}>
                {o.status === 'DELIVERED' ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                <span>Order Delivered</span>
              </div>
              <div className={`flex items-center space-x-1 ${
                hasAnyPodPhoto ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'
              }`}>
                {hasAnyPodPhoto ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                <span>POD Photo</span>
              </div>
              <div className={`flex items-center space-x-1 ${
                commission ? 'text-green-600 dark:text-green-400' : 'text-gray-400'
              }`}>
                {commission ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                <span>Commission Set</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {msg && (
              <span className={`text-sm font-medium ${
                msg.includes('✅') ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              }`}>
                {msg}
              </span>
            )}
            <button
              onClick={handleReleaseCommission}
              disabled={!canRelease || isProcessing}
              className={`inline-flex items-center px-6 py-3 rounded-lg font-semibold transition-all duration-200 ${
                canRelease && !isProcessing
                  ? 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white shadow-lg hover:shadow-xl'
                  : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
              }`}
              title={!canRelease ? 'Complete all requirements to release commission' : 'Release commission to driver'}
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  <Shield className="h-4 w-4 mr-2" />
                  Release Commission
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

(DriverCommissionsPage as any).getLayout = (page:any) => <AdminLayout>{page}</AdminLayout>;