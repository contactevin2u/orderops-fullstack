import React from 'react';

interface A6LabelPreviewProps {
  uid: string;
  qrCode?: string;
  skuName?: string;
  type: string;
  copyNumber?: number;
  serial?: string;
}

export default function A6LabelPreview({ 
  uid, 
  qrCode, 
  skuName, 
  type, 
  copyNumber, 
  serial 
}: A6LabelPreviewProps) {
  return (
    <div className="border-2 border-gray-300 bg-white" 
         style={{ 
           width: '105mm', 
           height: '148mm', 
           margin: '10px',
           display: 'inline-block',
           fontSize: '12px',
           fontFamily: 'Segoe UI, Arial, sans-serif'
         }}>
      {/* Header */}
      <div className="text-center border-b border-gray-300 p-2">
        <div className="font-bold text-blue-800" style={{ fontSize: '14px' }}>
          OrderOps
        </div>
        <div className="text-gray-600 uppercase text-xs">
          Product Identification Label
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col items-center justify-center p-3 h-full">
        {/* UID Section */}
        <div className="text-center mb-4">
          <div className="text-gray-600 uppercase text-xs mb-1">Unique ID</div>
          <div className="font-mono font-bold bg-gray-100 p-2 rounded border" 
               style={{ fontSize: '16px', wordBreak: 'break-all' }}>
            {uid}
          </div>
        </div>

        {/* QR Code */}
        {qrCode && (
          <div className="mb-4">
            <img 
              src={qrCode.startsWith('data:') ? qrCode : `data:image/png;base64,${qrCode}`}
              alt={`QR Code for ${uid}`}
              className="border border-gray-300 bg-white"
              style={{ width: '35mm', height: '35mm' }}
            />
          </div>
        )}

        {/* Product Info */}
        <div className="w-full border-t border-gray-200 pt-3">
          {skuName && (
            <div className="font-bold text-gray-800 text-center mb-2" style={{ fontSize: '12px' }}>
              {skuName}
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
            <div>
              <span className="font-bold text-gray-800">Type:</span><br/>
              {type}{copyNumber ? ` (Copy ${copyNumber})` : ''}
            </div>
            <div>
              <span className="font-bold text-gray-800">
                {serial ? 'Serial:' : 'Generated:'}
              </span><br/>
              {serial || new Date().toLocaleDateString('en-MY')}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-auto pt-2 border-t border-gray-200 w-full">
          <div className="text-center text-xs text-gray-500 italic">
            Printed: {new Date().toLocaleDateString('en-MY', { 
              year: 'numeric', 
              month: 'short', 
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </div>
        </div>
      </div>
    </div>
  );
}