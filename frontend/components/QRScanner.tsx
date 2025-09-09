import React, { useRef, useEffect, useState } from 'react';

interface QRScannerProps {
  onScan: (text: string) => void;
  onError: (error: string) => void;
  onClose: () => void;
}

export default function QRScanner({ onScan, onError, onClose }: QRScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { 
          facingMode: 'environment', // Use back camera if available
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      });
      
      setStream(mediaStream);
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play();
        setIsScanning(true);
        
        // Start scanning after video loads
        videoRef.current.onloadedmetadata = () => {
          startScanning();
        };
      }
    } catch (error) {
      console.error('Camera access error:', error);
      onError('Unable to access camera. Please check permissions and try again.');
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setIsScanning(false);
  };

  const startScanning = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const context = canvas.getContext('2d');

    if (!context) return;

    const scanInterval = setInterval(() => {
      if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Here we would normally use a QR code library to decode
        // For now, we'll simulate scanning with a manual input fallback
        // In a real implementation, you'd use jsQR or similar library
      }
    }, 100);

    // Cleanup interval on unmount
    return () => clearInterval(scanInterval);
  };

  const handleManualInput = () => {
    const manualUID = prompt('Enter UID manually (e.g., SKU001-ADMIN-20240906-001):');
    if (manualUID && manualUID.trim()) {
      onScan(manualUID.trim());
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">📷 Scan QR Code</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-xl"
          >
            ×
          </button>
        </div>

        <div className="relative">
          <video
            ref={videoRef}
            className="w-full h-64 bg-black rounded-lg object-cover"
            playsInline
            muted
          />
          <canvas
            ref={canvasRef}
            className="hidden"
          />
          
          {/* Scanning overlay */}
          <div className="absolute inset-0 border-2 border-white rounded-lg">
            <div className="absolute inset-4 border-2 border-dashed border-white opacity-50 rounded-lg"></div>
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <div className="animate-pulse text-white text-center">
                <div className="text-2xl mb-2">🎯</div>
                <div className="text-sm">Position QR code in frame</div>
              </div>
            </div>
          </div>

          {/* Test scan button for demo */}
          <button
            onClick={() => {
              const testUID = `SKU${String(Math.floor(Math.random() * 999) + 1).padStart(3, '0')}-SCAN-${new Date().toISOString().split('T')[0]}-${String(Math.floor(Math.random() * 99) + 1).padStart(3, '0')}`;
              onScan(testUID);
            }}
            className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded text-sm hover:bg-green-600"
          >
            🧪 Test Scan
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <div className="text-sm text-gray-600 text-center">
            📦 Point your camera at a UID QR code to scan
            <div className="text-xs text-gray-500 mt-1">
              Make sure the QR code is clearly visible and well-lit
            </div>
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={handleManualInput}
              className="flex-1 py-2 px-4 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm font-medium"
            >
              ⌨️ Enter Manually
            </button>
            <button
              onClick={onClose}
              className="flex-1 py-2 px-4 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm font-medium"
            >
              Cancel
            </button>
          </div>
        </div>

        {!isScanning && (
          <div className="mt-4 text-center text-sm text-red-600">
            Camera not available. Please check permissions or enter UID manually.
          </div>
        )}
      </div>
    </div>
  );
}