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
        <title>UID Labels - A6 Format</title>
        <style>
          @page {
            size: A6 portrait; /* 105mm × 148mm */
            margin: 3mm;
          }
          
          body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; 
            padding: 0;
            font-size: 12px;
            line-height: 1.2;
          }
          
          .label-container {
            display: flex;
            flex-direction: column;
            width: 99mm; /* A6 width minus margins */
            height: 142mm; /* A6 height minus margins */
            border: 2px solid #000;
            padding: 4mm;
            box-sizing: border-box;
            page-break-after: always;
            background: white;
          }
          
          .label-container:last-child {
            page-break-after: auto;
          }
          
          .header {
            text-align: center;
            border-bottom: 1px solid #333;
            padding-bottom: 3mm;
            margin-bottom: 3mm;
          }
          
          .company-name {
            font-size: 14px;
            font-weight: bold;
            color: #1a365d;
            margin-bottom: 1mm;
          }
          
          .label-title {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
          }
          
          .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
          }
          
          .uid-section {
            margin-bottom: 4mm;
          }
          
          .uid-label {
            font-size: 9px;
            color: #666;
            margin-bottom: 1mm;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          
          .uid-value {
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: bold;
            color: #000;
            background: #f8f9fa;
            padding: 2mm;
            border: 1px solid #ddd;
            border-radius: 2mm;
            word-break: break-all;
          }
          
          .qr-section {
            margin: 3mm 0;
          }
          
          .qr-code {
            width: 35mm;
            height: 35mm;
            border: 1px solid #ddd;
            background: white;
          }
          
          .product-info {
            margin-top: 3mm;
            padding-top: 3mm;
            border-top: 1px solid #eee;
            width: 100%;
          }
          
          .sku-name {
            font-size: 12px;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 2mm;
          }
          
          .details-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2mm;
            font-size: 9px;
            color: #4a5568;
          }
          
          .detail-item {
            text-align: left;
          }
          
          .detail-label {
            font-weight: bold;
            color: #2d3748;
          }
          
          .footer {
            margin-top: auto;
            padding-top: 2mm;
            border-top: 1px solid #eee;
            font-size: 8px;
            color: #666;
            text-align: center;
          }
          
          .generated-date {
            font-style: italic;
          }
          
          /* Malaysian printing optimization */
          @media print {
            body { -webkit-print-color-adjust: exact; }
            .label-container { break-inside: avoid; }
          }
        </style>
      </head>
      <body>
        ${generatedUIDs.map(uid => `
          <div class="label-container">
            <div class="header">
              <div class="company-name">OrderOps</div>
              <div class="label-title">Product Identification Label</div>
            </div>
            
            <div class="main-content">
              <div class="uid-section">
                <div class="uid-label">Unique ID</div>
                <div class="uid-value">${uid.uid}</div>
              </div>
              
              ${uid.qr_code ? `
                <div class="qr-section">
                  <img src="${uid.qr_code.startsWith('data:') ? uid.qr_code : `data:image/png;base64,${uid.qr_code}`}" 
                       class="qr-code" 
                       alt="QR Code for ${uid.uid}" />
                </div>
              ` : ''}
              
              <div class="product-info">
                ${selectedSKUData ? `<div class="sku-name">${selectedSKUData.name}</div>` : ''}
                
                <div class="details-grid">
                  <div class="detail-item">
                    <span class="detail-label">Type:</span><br/>
                    ${uid.type}${uid.copy_number ? ` (Copy ${uid.copy_number})` : ''}
                  </div>
                  ${uid.serial ? `
                    <div class="detail-item">
                      <span class="detail-label">Serial:</span><br/>
                      ${uid.serial}
                    </div>
                  ` : `
                    <div class="detail-item">
                      <span class="detail-label">Generated:</span><br/>
                      ${new Date().toLocaleDateString('en-MY')}
                    </div>
                  `}
                </div>
              </div>
            </div>
            
            <div class="footer">
              <div class="generated-date">
                Printed: ${new Date().toLocaleDateString('en-MY', { 
                  year: 'numeric', 
                  month: 'short', 
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </div>
            </div>
          </div>
        `).join('')}
        
        <script>
          window.onload = function() {
            setTimeout(() => {
              window.print();
              setTimeout(() => window.close(), 1000);
            }, 500);
          };
        </script>
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
            <div>
              <h3 className="text-lg font-semibold">Generated UIDs</h3>
              <p className="text-sm text-gray-600 mt-1">
                Professional labels formatted for A6 printing (105mm × 148mm)
              </p>
            </div>
            {generatedUIDs.length > 0 && (
              <button className="btn secondary text-sm" onClick={printUIDLabels}>
                🖨️ Print A6 Labels
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