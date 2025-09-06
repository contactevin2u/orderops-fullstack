import React, { useState, useEffect } from 'react';
import PageHeader from '@/components/PageHeader';
import Card from '@/components/Card';
import { 
  generateUID, 
  getAllSKUs, 
  listDrivers, 
  getInventoryConfig,
  generateQRCode 
} from '@/lib/api';

interface SKU {
  id: number;
  code: string;
  name: string;
  category?: string;
  is_serialized: boolean;
  is_active: boolean;
}

interface Driver {
  id: number;
  name?: string;
  phone?: string;
}

interface GeneratedUID {
  uid: string;
  type: string;
  copy_number?: number;
  serial?: string;
  qr_code?: string;
}

export default function UIDGeneratorPage() {
  const [config, setConfig] = useState<any>(null);
  const [skus, setSKUs] = useState<SKU[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Form state
  const [selectedSKU, setSelectedSKU] = useState<string>('');
  const [itemType, setItemType] = useState<'NEW' | 'RENTAL'>('RENTAL');
  const [serialNumber, setSerialNumber] = useState<string>('');
  const [generateQR, setGenerateQR] = useState<boolean>(true);

  // Results
  const [generatedUIDs, setGeneratedUIDs] = useState<GeneratedUID[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configData, skuData, driverData] = await Promise.all([
        getInventoryConfig(),
        getAllSKUs(),
        listDrivers()
      ]);
      
      setConfig(configData);
      setSKUs(skuData.filter((sku: SKU) => sku.is_active));
      setDrivers(driverData);
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedSKU) {
      setError('Please select a SKU');
      return;
    }

    try {
      setGenerating(true);
      setError('');
      setSuccess('');

      const response = await generateUID({
        sku_id: parseInt(selectedSKU),
        item_type: itemType,
        serial_number: serialNumber || undefined
      });

      if (response.success) {
        const uidsWithQR: GeneratedUID[] = [];
        
        for (const item of response.items) {
          let qr_code = '';
          if (generateQR) {
            try {
              const qrResponse = await generateQRCode({
                uid: item.uid,
                content: `UID:${item.uid}|SKU:${selectedSKU}|TYPE:${item.type}${item.serial ? `|SERIAL:${item.serial}` : ''}`,
                size: 200
              });
              if (qrResponse.success) {
                qr_code = qrResponse.qr_code_base64;
              }
            } catch (qrErr) {
              console.warn('Failed to generate QR code for UID:', item.uid);
            }
          }
          
          uidsWithQR.push({
            ...item,
            qr_code
          });
        }
        
        setGeneratedUIDs(uidsWithQR);
        setSuccess(`Successfully generated ${response.items.length} UID${response.items.length > 1 ? 's' : ''}`);
        
        // Reset form
        setSelectedSKU('');
        setSerialNumber('');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate UID');
    } finally {
      setGenerating(false);
    }
  };

  const downloadQRCode = (uid: string, qrCode: string) => {
    const link = document.createElement('a');
    link.href = qrCode.startsWith('data:') ? qrCode : `data:image/png;base64,${qrCode}`;
    link.download = `qr-${uid}.png`;
    link.click();
  };

  const printUIDLabels = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const selectedSKUData = skus.find(s => s.id === parseInt(selectedSKU));
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>UID Labels</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
          .label { 
            display: inline-block; 
            border: 1px solid #333; 
            padding: 10px; 
            margin: 5px; 
            width: 300px;
            text-align: center;
            page-break-inside: avoid;
          }
          .uid { font-weight: bold; font-size: 14px; margin-bottom: 5px; }
          .details { font-size: 11px; color: #666; }
          .qr { margin: 5px 0; }
          .qr img { width: 80px; height: 80px; }
          @media print {
            body { margin: 0; }
            .label { margin: 2px; }
          }
        </style>
      </head>
      <body>
        ${generatedUIDs.map(uid => `
          <div class="label">
            <div class="uid">${uid.uid}</div>
            ${uid.qr_code ? `<div class="qr"><img src="${uid.qr_code.startsWith('data:') ? uid.qr_code : `data:image/png;base64,${uid.qr_code}`}" /></div>` : ''}
            <div class="details">
              ${selectedSKUData ? selectedSKUData.name : ''}<br/>
              Type: ${uid.type}${uid.copy_number ? ` (Copy ${uid.copy_number})` : ''}<br/>
              ${uid.serial ? `Serial: ${uid.serial}<br/>` : ''}
              Generated: ${new Date().toLocaleDateString()}
            </div>
          </div>
        `).join('')}
        <script>window.print(); window.close();</script>
      </body>
      </html>
    `);
    printWindow.document.close();
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <Card>Loading UID Generator...</Card>;
  }


  return (
    <div>
      <PageHeader title="UID Generator" />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Generator Form */}
        <Card>
          <h3 className="text-lg font-semibold mb-4">Generate New UIDs</h3>
          
          <div className="space-y-4">
            {/* SKU Selection */}
            <div>
              <label className="block text-sm font-medium mb-1">SKU *</label>
              <select
                className="input"
                value={selectedSKU}
                onChange={(e) => setSelectedSKU(e.target.value)}
                required
              >
                <option value="">Select SKU</option>
                {skus.map((sku) => (
                  <option key={sku.id} value={sku.id}>
                    {sku.code} - {sku.name} {sku.is_serialized && '📦'}
                  </option>
                ))}
              </select>
              <div className="text-xs text-gray-500 mt-1">
                📦 indicates serialized items that require UID scanning
              </div>
            </div>

            {/* Item Type */}
            <div>
              <label className="block text-sm font-medium mb-1">Item Type *</label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="RENTAL"
                    checked={itemType === 'RENTAL'}
                    onChange={(e) => setItemType(e.target.value as 'RENTAL')}
                    className="mr-2"
                  />
                  Rental (1 UID)
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="NEW"
                    checked={itemType === 'NEW'}
                    onChange={(e) => setItemType(e.target.value as 'NEW')}
                    className="mr-2"
                  />
                  New Item (2 UIDs)
                </label>
              </div>
            </div>

            {/* Serial Number */}
            <div>
              <label className="block text-sm font-medium mb-1">Serial Number (Optional)</label>
              <input
                type="text"
                className="input"
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                placeholder="Enter manufacturer serial number"
              />
            </div>

            {/* QR Code Option */}
            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={generateQR}
                  onChange={(e) => setGenerateQR(e.target.checked)}
                  className="mr-2"
                />
                Generate QR codes for UIDs
              </label>
            </div>

            {/* Generate Button */}
            <button
              className="btn w-full"
              onClick={handleGenerate}
              disabled={generating || !selectedSKU}
            >
              {generating ? 'Generating...' : `Generate ${itemType === 'NEW' ? '2' : '1'} UID${itemType === 'NEW' ? 's' : ''}`}
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

        {/* Generated UIDs */}
        <Card>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Generated UIDs</h3>
            {generatedUIDs.length > 0 && (
              <button className="btn secondary text-sm" onClick={printUIDLabels}>
                Print Labels
              </button>
            )}
          </div>

          {generatedUIDs.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-2">📋</div>
              <p>Generated UIDs will appear here</p>
            </div>
          ) : (
            <div className="space-y-4">
              {generatedUIDs.map((uid, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="font-mono text-lg font-bold text-blue-600">
                        {uid.uid}
                      </div>
                      <div className="text-sm text-gray-600 mt-1">
                        Type: {uid.type}
                        {uid.copy_number && ` (Copy ${uid.copy_number})`}
                        {uid.serial && (
                          <>
                            <br />Serial: {uid.serial}
                          </>
                        )}
                      </div>
                    </div>
                    
                    {uid.qr_code && (
                      <div className="flex flex-col items-center ml-4">
                        <img 
                          src={uid.qr_code.startsWith('data:') ? uid.qr_code : `data:image/png;base64,${uid.qr_code}`}
                          alt={`QR Code for ${uid.uid}`}
                          className="w-16 h-16 border"
                        />
                        <button
                          className="text-xs text-blue-600 hover:underline mt-1"
                          onClick={() => downloadQRCode(uid.uid, uid.qr_code!)}
                        >
                          Download
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Usage Instructions */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">How to Use</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>• <strong>Rental Items:</strong> Generate 1 UID for items that will be rented out and returned</p>
          <p>• <strong>New Items:</strong> Generate 2 UIDs (Copy 1 & Copy 2) for items being sold - one stays with customer, one for records</p>
          <p>• <strong>Serial Numbers:</strong> Add manufacturer serial numbers for warranty and tracking purposes</p>
          <p>• <strong>QR Codes:</strong> Enable QR generation for easy scanning with mobile devices</p>
          <p>• <strong>Labels:</strong> Use &quot;Print Labels&quot; to create physical labels with UID and QR codes</p>
        </div>
      </Card>
    </div>
  );
}