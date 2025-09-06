import React, { useState, useEffect } from 'react';
import PageHeader from '@/components/PageHeader';
import Card from '@/components/Card';
import { generateQRCode, getOrderUIDs, getInventoryConfig } from '@/lib/api';

interface QRResult {
  id: string;
  content: string;
  qr_code_base64: string;
  format: string;
  size: number;
  timestamp: string;
}

export default function QRGeneratorPage() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Form state
  const [qrType, setQrType] = useState<'custom' | 'uid' | 'order'>('custom');
  const [customContent, setCustomContent] = useState<string>('');
  const [uidValue, setUidValue] = useState<string>('');
  const [orderId, setOrderId] = useState<string>('');
  const [qrSize, setQrSize] = useState<number>(200);

  // Results
  const [generatedQRs, setGeneratedQRs] = useState<QRResult[]>([]);
  const [selectedQR, setSelectedQR] = useState<QRResult | null>(null);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const configData = await getInventoryConfig();
      setConfig(configData);
    } catch (err: any) {
      setError(err.message || 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    let content = '';
    
    switch (qrType) {
      case 'custom':
        if (!customContent.trim()) {
          setError('Please enter content for the QR code');
          return;
        }
        content = customContent.trim();
        break;
      
      case 'uid':
        if (!uidValue.trim()) {
          setError('Please enter a UID');
          return;
        }
        content = `UID:${uidValue.trim()}`;
        break;
      
      case 'order':
        if (!orderId.trim()) {
          setError('Please enter an Order ID');
          return;
        }
        // Validate order exists and get UID data
        try {
          const orderUIDs = await getOrderUIDs(orderId);
          const uidList = orderUIDs.uids.map(u => u.uid).join(',');
          content = `ORDER:${orderId}|UIDS:${uidList}|TOTAL:${orderUIDs.total_issued}`;
        } catch (err) {
          setError('Failed to fetch order UID data');
          return;
        }
        break;
    }

    try {
      setGenerating(true);
      setError('');
      setSuccess('');

      const response = await generateQRCode({
        content,
        size: qrSize,
        ...(qrType === 'uid' && { uid: uidValue }),
        ...(qrType === 'order' && { order_id: parseInt(orderId) })
      });

      if (response.success) {
        const newQR: QRResult = {
          id: Date.now().toString(),
          content,
          qr_code_base64: response.qr_code_base64,
          format: response.format,
          size: qrSize,
          timestamp: new Date().toISOString()
        };
        
        setGeneratedQRs(prev => [newQR, ...prev.slice(0, 9)]); // Keep last 10
        setSelectedQR(newQR);
        setSuccess('QR code generated successfully');
        
        // Reset form
        setCustomContent('');
        setUidValue('');
        setOrderId('');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate QR code');
    } finally {
      setGenerating(false);
    }
  };

  const downloadQR = (qr: QRResult) => {
    const link = document.createElement('a');
    link.href = qr.qr_code_base64.startsWith('data:') ? qr.qr_code_base64 : `data:image/png;base64,${qr.qr_code_base64}`;
    link.download = `qr-${qr.id}.${qr.format.toLowerCase()}`;
    link.click();
  };

  const printQR = (qr: QRResult) => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>QR Code - ${qr.id}</title>
        <style>
          body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            text-align: center; 
          }
          .qr-container { 
            border: 2px solid #333; 
            padding: 20px; 
            margin: 20px auto;
            display: inline-block;
            max-width: 400px;
          }
          .qr-image { margin: 20px 0; }
          .qr-content { 
            font-size: 12px; 
            word-break: break-all; 
            color: #666; 
            margin-top: 15px;
            border-top: 1px solid #ccc;
            padding-top: 15px;
          }
          .qr-meta {
            font-size: 10px;
            color: #999;
            margin-top: 10px;
          }
          @media print {
            body { margin: 0; }
          }
        </style>
      </head>
      <body>
        <div class="qr-container">
          <div class="qr-image">
            <img src="${qr.qr_code_base64.startsWith('data:') ? qr.qr_code_base64 : `data:image/png;base64,${qr.qr_code_base64}`}" 
                 style="width: ${qr.size}px; height: ${qr.size}px;" />
          </div>
          <div class="qr-content">
            <strong>Content:</strong><br/>
            ${qr.content}
          </div>
          <div class="qr-meta">
            Generated: ${new Date(qr.timestamp).toLocaleString()}<br/>
            Size: ${qr.size}px | Format: ${qr.format}
          </div>
        </div>
        <script>window.print(); window.close();</script>
      </body>
      </html>
    `);
    printWindow.document.close();
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccess('Content copied to clipboard');
    setTimeout(() => setSuccess(''), 2000);
  };

  useEffect(() => {
    loadConfig();
  }, []);

  if (loading) {
    return <Card>Loading QR Generator...</Card>;
  }

  return (
    <div>
      <PageHeader title="QR Code Generator" />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Generator Form */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Generate QR Code</h3>
          
          <div className="space-y-4">
            {/* QR Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">QR Code Type</label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="custom"
                    checked={qrType === 'custom'}
                    onChange={(e) => setQrType(e.target.value as any)}
                    className="mr-2"
                  />
                  Custom Content
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="uid"
                    checked={qrType === 'uid'}
                    onChange={(e) => setQrType(e.target.value as any)}
                    className="mr-2"
                  />
                  UID Code
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="order"
                    checked={qrType === 'order'}
                    onChange={(e) => setQrType(e.target.value as any)}
                    className="mr-2"
                  />
                  Order Summary
                </label>
              </div>
            </div>

            {/* Content Input */}
            {qrType === 'custom' && (
              <div>
                <label className="block text-sm font-medium mb-1">Custom Content *</label>
                <textarea
                  className="input"
                  rows={4}
                  value={customContent}
                  onChange={(e) => setCustomContent(e.target.value)}
                  placeholder="Enter any text, URL, or data to encode in QR code..."
                />
                <div className="text-xs text-gray-500 mt-1">
                  Examples: URLs, contact info, WiFi credentials, plain text
                </div>
              </div>
            )}

            {qrType === 'uid' && (
              <div>
                <label className="block text-sm font-medium mb-1">UID *</label>
                <input
                  type="text"
                  className="input"
                  value={uidValue}
                  onChange={(e) => setUidValue(e.target.value)}
                  placeholder="Enter UID (e.g., SKU001-DRV123-20240306-001)"
                />
                <div className="text-xs text-gray-500 mt-1">
                  Will generate QR code for UID scanning and tracking
                </div>
              </div>
            )}

            {qrType === 'order' && (
              <div>
                <label className="block text-sm font-medium mb-1">Order ID *</label>
                <input
                  type="number"
                  className="input"
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                  placeholder="Enter Order ID"
                />
                <div className="text-xs text-gray-500 mt-1">
                  Will include order details and associated UIDs
                </div>
              </div>
            )}

            {/* QR Size */}
            <div>
              <label className="block text-sm font-medium mb-1">QR Code Size</label>
              <select
                className="input"
                value={qrSize}
                onChange={(e) => setQrSize(parseInt(e.target.value))}
              >
                <option value={100}>Small (100px)</option>
                <option value={200}>Medium (200px)</option>
                <option value={300}>Large (300px)</option>
                <option value={400}>Extra Large (400px)</option>
              </select>
            </div>

            {/* Generate Button */}
            <button
              className="btn w-full"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? 'Generating...' : 'Generate QR Code'}
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

        {/* Preview and Actions */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">QR Code Preview</h3>
          
          {selectedQR ? (
            <div className="space-y-4">
              <div className="text-center">
                <img
                  src={selectedQR.qr_code_base64.startsWith('data:') ? selectedQR.qr_code_base64 : `data:image/png;base64,${selectedQR.qr_code_base64}`}
                  alt="Generated QR Code"
                  className="mx-auto border"
                  style={{ width: selectedQR.size, height: selectedQR.size }}
                />
              </div>
              
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-600 mb-1">Content:</div>
                <div className="font-mono text-sm break-all">
                  {selectedQR.content}
                </div>
                <button
                  className="text-xs text-blue-600 hover:underline mt-1"
                  onClick={() => copyToClipboard(selectedQR.content)}
                >
                  Copy Content
                </button>
              </div>

              <div className="text-xs text-gray-500">
                Generated: {new Date(selectedQR.timestamp).toLocaleString()}<br/>
                Size: {selectedQR.size}px | Format: {selectedQR.format}
              </div>

              <div className="flex gap-2">
                <button
                  className="btn secondary flex-1"
                  onClick={() => downloadQR(selectedQR)}
                >
                  Download
                </button>
                <button
                  className="btn secondary flex-1"
                  onClick={() => printQR(selectedQR)}
                >
                  Print
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-2">📱</div>
              <p>Generated QR code will appear here</p>
            </div>
          )}
        </Card>
      </div>

      {/* Recent QR Codes */}
      {generatedQRs.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold mb-4">Recent QR Codes</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {generatedQRs.map((qr) => (
              <div
                key={qr.id}
                className={`border rounded p-2 cursor-pointer hover:shadow-lg transition-shadow ${
                  selectedQR?.id === qr.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedQR(qr)}
              >
                <img
                  src={qr.qr_code_base64.startsWith('data:') ? qr.qr_code_base64 : `data:image/png;base64,${qr.qr_code_base64}`}
                  alt={`QR ${qr.id}`}
                  className="w-full h-20 object-contain"
                />
                <div className="text-xs text-gray-500 mt-1 truncate">
                  {qr.content.substring(0, 20)}...
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(qr.timestamp).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Usage Instructions */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">QR Code Usage</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>• <strong>Custom Content:</strong> Generate QR codes for any text, URLs, contact information, etc.</p>
          <p>• <strong>UID Codes:</strong> Create QR codes specifically for UID scanning and inventory tracking</p>
          <p>• <strong>Order Summary:</strong> Generate QR codes containing order details and associated UIDs for delivery verification</p>
          <p>• <strong>Sizes:</strong> Choose appropriate size based on scanning distance and label space</p>
          <p>• <strong>Printing:</strong> Use the print function to create physical labels with proper sizing</p>
        </div>
      </Card>
    </div>
  );
}