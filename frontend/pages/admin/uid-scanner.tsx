import React, { useState, useEffect, useRef } from 'react';
import PageHeader from '@/components/PageHeader';
import Card from '@/components/Card';
import { 
  scanUID, 
  getOrderUIDs, 
  getInventoryConfig,
  getAllSKUs
} from '@/lib/api';

interface ScanResult {
  id: string;
  uid: string;
  action: string;
  order_id: number;
  sku_name?: string;
  message: string;
  success: boolean;
  timestamp: string;
}

interface SKU {
  id: number;
  code: string;
  name: string;
}

export default function UIDScannerPage() {
  const [config, setConfig] = useState<any>(null);
  const [skus, setSKUs] = useState<SKU[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Scanner state
  const [manualUID, setManualUID] = useState<string>('');
  const [selectedAction, setSelectedAction] = useState<string>('DELIVER');
  const [selectedOrderId, setSelectedOrderId] = useState<string>('');
  const [selectedSKUId, setSelectedSKUId] = useState<string>('');
  const [scanNotes, setScanNotes] = useState<string>('');

  // Camera scanner state
  const [cameraEnabled, setCameraEnabled] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string>('');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Results
  const [scanHistory, setScanHistory] = useState<ScanResult[]>([]);
  const [orderUIDs, setOrderUIDs] = useState<any>(null);

  // Actions available for UID scanning
  const SCAN_ACTIONS = [
    { value: 'LOAD_OUT', label: 'Load Out (To Driver)', description: 'Load items onto driver vehicle' },
    { value: 'DELIVER', label: 'Deliver (To Customer)', description: 'Deliver items to customer location' },
    { value: 'RETURN', label: 'Return (From Customer)', description: 'Collect items from customer' },
    { value: 'LOAD_IN', label: 'Load In (From Driver)', description: 'Receive items back from driver' },
    { value: 'REPAIR', label: 'Send for Repair', description: 'Mark item as needing repair' },
    { value: 'SWAP', label: 'Swap Item', description: 'Exchange item for another' }
  ];

  const loadData = async () => {
    try {
      setLoading(true);
      const [configData, skuData] = await Promise.all([
        getInventoryConfig(),
        getAllSKUs()
      ]);
      
      setConfig(configData);
      setSKUs(skuData.filter((sku: SKU) => sku.is_active));
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    if (!manualUID.trim()) {
      setError('Please enter a UID to scan');
      return;
    }

    if (!selectedOrderId.trim()) {
      setError('Please enter an Order ID');
      return;
    }

    try {
      setScanning(true);
      setError('');
      setSuccess('');

      const response = await scanUID({
        uid: manualUID.trim(),
        action: selectedAction as any,
        order_id: parseInt(selectedOrderId),
        sku_id: selectedSKUId ? parseInt(selectedSKUId) : undefined,
        notes: scanNotes || undefined
      });

      const scanResult: ScanResult = {
        id: Date.now().toString(),
        uid: manualUID.trim(),
        action: selectedAction,
        order_id: parseInt(selectedOrderId),
        sku_name: response.sku_name,
        message: response.message,
        success: response.success,
        timestamp: new Date().toISOString()
      };

      setScanHistory(prev => [scanResult, ...prev.slice(0, 19)]); // Keep last 20

      if (response.success) {
        setSuccess(response.message);
        setManualUID('');
        setScanNotes('');
        
        // Refresh order UIDs if we're viewing them
        if (orderUIDs && orderUIDs.order_id === parseInt(selectedOrderId)) {
          loadOrderUIDs(selectedOrderId);
        }
      } else {
        setError(response.message);
      }

    } catch (err: any) {
      setError(err.message || 'Failed to scan UID');
      
      const scanResult: ScanResult = {
        id: Date.now().toString(),
        uid: manualUID.trim(),
        action: selectedAction,
        order_id: parseInt(selectedOrderId),
        message: err.message || 'Scan failed',
        success: false,
        timestamp: new Date().toISOString()
      };
      
      setScanHistory(prev => [scanResult, ...prev.slice(0, 19)]);
    } finally {
      setScanning(false);
    }
  };

  const loadOrderUIDs = async (orderId: string) => {
    if (!orderId.trim()) return;

    try {
      const response = await getOrderUIDs(orderId);
      setOrderUIDs(response);
    } catch (err: any) {
      console.error('Failed to load order UIDs:', err);
    }
  };

  // Camera functions
  const startCamera = async () => {
    try {
      setCameraError('');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' } // Use back camera if available
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraEnabled(true);
      }
    } catch (err: any) {
      setCameraError('Failed to access camera. Please check permissions.');
      console.error('Camera error:', err);
    }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setCameraEnabled(false);
  };

  const captureFromCamera = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const context = canvas.getContext('2d');
    
    if (context) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0);
      
      // In a real implementation, you would use a QR code library like qr-scanner
      // For now, we'll just show a placeholder
      setError('QR code scanning requires additional libraries. Please enter UID manually.');
    }
  };

  useEffect(() => {
    loadData();
    
    // Cleanup camera on unmount
    return () => {
      stopCamera();
    };
  }, []);

  useEffect(() => {
    if (selectedOrderId) {
      loadOrderUIDs(selectedOrderId);
    }
  }, [selectedOrderId]);

  if (loading) {
    return <Card>Loading UID Scanner...</Card>;
  }

  if (!config?.uid_inventory_enabled) {
    return (
      <div>
        <PageHeader title="UID Scanner" />
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🚫</div>
            <h2 className="text-xl font-semibold mb-2">UID System Disabled</h2>
            <p className="text-gray-600">
              The UID inventory system is currently disabled. Please contact your administrator.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="UID Scanner" />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scanner Interface */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Scan UID</h3>
          
          <div className="space-y-4">
            {/* Camera Scanner */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
              <div className="text-center">
                {!cameraEnabled ? (
                  <div>
                    <div className="text-4xl mb-2">📷</div>
                    <p className="text-gray-600 mb-4">Use camera to scan QR codes</p>
                    <button className="btn secondary" onClick={startCamera}>
                      Enable Camera
                    </button>
                    {cameraError && (
                      <div className="text-red-600 text-sm mt-2">{cameraError}</div>
                    )}
                  </div>
                ) : (
                  <div>
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      className="max-w-full h-48 bg-black rounded"
                    />
                    <div className="mt-2 space-x-2">
                      <button className="btn" onClick={captureFromCamera}>
                        Scan QR Code
                      </button>
                      <button className="btn secondary" onClick={stopCamera}>
                        Stop Camera
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="text-center text-gray-500">OR</div>

            {/* Manual UID Entry */}
            <div>
              <label className="block text-sm font-medium mb-1">Enter UID Manually *</label>
              <input
                type="text"
                className="input"
                value={manualUID}
                onChange={(e) => setManualUID(e.target.value)}
                placeholder="e.g., SKU001-DRV123-20240306-001"
                onKeyPress={(e) => e.key === 'Enter' && handleScan()}
              />
            </div>

            {/* Order ID */}
            <div>
              <label className="block text-sm font-medium mb-1">Order ID *</label>
              <input
                type="number"
                className="input"
                value={selectedOrderId}
                onChange={(e) => setSelectedOrderId(e.target.value)}
                placeholder="Enter order ID"
              />
            </div>

            {/* Action Selection */}
            <div>
              <label className="block text-sm font-medium mb-1">Action *</label>
              <select
                className="input"
                value={selectedAction}
                onChange={(e) => setSelectedAction(e.target.value)}
              >
                {SCAN_ACTIONS.map((action) => (
                  <option key={action.value} value={action.value}>
                    {action.label}
                  </option>
                ))}
              </select>
              <div className="text-xs text-gray-500 mt-1">
                {SCAN_ACTIONS.find(a => a.value === selectedAction)?.description}
              </div>
            </div>

            {/* Manual SKU Selection */}
            <div>
              <label className="block text-sm font-medium mb-1">SKU (if UID not found)</label>
              <select
                className="input"
                value={selectedSKUId}
                onChange={(e) => setSelectedSKUId(e.target.value)}
              >
                <option value="">Auto-detect from UID</option>
                {skus.map((sku) => (
                  <option key={sku.id} value={sku.id}>
                    {sku.code} - {sku.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium mb-1">Notes (Optional)</label>
              <input
                type="text"
                className="input"
                value={scanNotes}
                onChange={(e) => setScanNotes(e.target.value)}
                placeholder="Additional notes about this scan"
              />
            </div>

            {/* Scan Button */}
            <button
              className="btn w-full"
              onClick={handleScan}
              disabled={scanning || !manualUID.trim() || !selectedOrderId.trim()}
            >
              {scanning ? 'Scanning...' : 'Scan UID'}
            </button>

            {/* Messages */}
            {error && (
              <div className="text-red-600 bg-red-50 p-3 rounded text-sm">
                {error}
              </div>
            )}
            {success && (
              <div className="text-green-600 bg-green-50 p-3 rounded text-sm">
                {success}
              </div>
            )}
          </div>
        </Card>

        {/* Results and Order UIDs */}
        <div className="space-y-6">
          {/* Order UIDs */}
          {orderUIDs && (
            <Card>
              <h3 className="text-lg font-semibold mb-4">
                Order #{orderUIDs.order_id} UIDs
              </h3>
              
              <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
                <div className="bg-blue-50 p-3 rounded text-center">
                  <div className="text-xl font-bold text-blue-600">{orderUIDs.total_issued}</div>
                  <div className="text-blue-800">Issued</div>
                </div>
                <div className="bg-green-50 p-3 rounded text-center">
                  <div className="text-xl font-bold text-green-600">{orderUIDs.total_returned}</div>
                  <div className="text-green-800">Returned</div>
                </div>
                <div className="bg-gray-50 p-3 rounded text-center">
                  <div className="text-xl font-bold text-gray-600">{orderUIDs.uids.length}</div>
                  <div className="text-gray-800">Total Scans</div>
                </div>
              </div>

              {orderUIDs.uids.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="table text-sm">
                    <thead>
                      <tr>
                        <th>UID</th>
                        <th>Action</th>
                        <th>SKU</th>
                        <th>Scanned</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orderUIDs.uids.slice(0, 10).map((uid: any) => (
                        <tr key={uid.id}>
                          <td className="font-mono text-xs">{uid.uid}</td>
                          <td>
                            <span className={`px-2 py-1 rounded text-xs ${
                              uid.action === 'DELIVER' ? 'bg-green-100 text-green-800' :
                              uid.action === 'RETURN' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {uid.action}
                            </span>
                          </td>
                          <td className="text-xs">{uid.sku_name || 'Unknown'}</td>
                          <td className="text-xs">
                            {new Date(uid.scanned_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {orderUIDs.uids.length > 10 && (
                    <div className="text-center text-xs text-gray-500 mt-2">
                      Showing first 10 of {orderUIDs.uids.length} scans
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}

          {/* Scan History */}
          <Card>
            <h3 className="text-lg font-semibold mb-4">Recent Scans</h3>
            
            {scanHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <div className="text-3xl mb-2">📋</div>
                <p>Scan results will appear here</p>
              </div>
            ) : (
              <div className="space-y-3">
                {scanHistory.slice(0, 10).map((scan) => (
                  <div
                    key={scan.id}
                    className={`border-l-4 p-3 rounded ${
                      scan.success 
                        ? 'border-green-400 bg-green-50' 
                        : 'border-red-400 bg-red-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="font-mono text-sm font-medium">
                          {scan.uid}
                        </div>
                        <div className="text-xs text-gray-600 mt-1">
                          Order #{scan.order_id} • {scan.action}
                          {scan.sku_name && ` • ${scan.sku_name}`}
                        </div>
                        <div className="text-sm mt-1">{scan.message}</div>
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(scan.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Hidden canvas for camera capture */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Usage Instructions */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">Scanner Usage</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>• <strong>Camera Scanning:</strong> Enable camera to scan QR codes automatically (requires camera permissions)</p>
          <p>• <strong>Manual Entry:</strong> Type or paste UID directly into the input field</p>
          <p>• <strong>Actions:</strong> Select appropriate action based on what you&apos;re doing with the item</p>
          <p>• <strong>Order Tracking:</strong> Enter order ID to see all UIDs associated with that order</p>
          <p>• <strong>Manual SKU:</strong> Override SKU detection if UID is not in system database</p>
        </div>
      </Card>
    </div>
  );
}