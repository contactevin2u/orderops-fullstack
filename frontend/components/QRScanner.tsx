import React, { useRef, useEffect, useState } from 'react';
import jsQR from 'jsqr';

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
  const [scanInterval, setScanInterval] = useState<NodeJS.Timeout | null>(null);
  const [lastScanTime, setLastScanTime] = useState(0);
  const [cameraLoading, setCameraLoading] = useState(true);
  const [cameraError, setCameraError] = useState<string | null>(null);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startCamera = async () => {
    try {
      console.log('Starting camera...');
      
      // Check if getUserMedia is supported
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera not supported by this browser');
      }

      // Try multiple camera configurations
      let mediaStream: MediaStream | null = null;
      
      // Try with back camera first
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { 
            facingMode: 'environment',
            width: { ideal: 640, max: 1280 },
            height: { ideal: 480, max: 720 }
          }
        });
        console.log('Back camera access successful');
      } catch (backCameraError) {
        console.log('Back camera failed, trying front camera...');
        // Fallback to front camera
        try {
          mediaStream = await navigator.mediaDevices.getUserMedia({
            video: { 
              facingMode: 'user',
              width: { ideal: 640, max: 1280 },
              height: { ideal: 480, max: 720 }
            }
          });
          console.log('Front camera access successful');
        } catch (frontCameraError) {
          console.log('Front camera failed, trying any camera...');
          // Last resort - any camera
          mediaStream = await navigator.mediaDevices.getUserMedia({
            video: {
              width: { ideal: 640, max: 1280 },
              height: { ideal: 480, max: 720 }
            }
          });
          console.log('Any camera access successful');
        }
      }
      
      if (!mediaStream) {
        throw new Error('No camera stream available');
      }
      
      setStream(mediaStream);
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        
        // Add event listeners
        videoRef.current.onloadedmetadata = () => {
          console.log('Video metadata loaded');
          setCameraLoading(false);
          setCameraError(null);
          setIsScanning(true);
          startScanning();
        };
        
        videoRef.current.onerror = (error) => {
          console.error('Video error:', error);
          onError('Video playback error. Please try again.');
        };
        
        // Start playing the video
        const playPromise = videoRef.current.play();
        if (playPromise !== undefined) {
          playPromise.catch(error => {
            console.error('Play error:', error);
            onError('Unable to start video. Please try again.');
          });
        }
        
        console.log('Video element configured');
      }
    } catch (error: any) {
      console.error('Camera access error:', error);
      let errorMessage = 'Unable to access camera. ';
      
      if (error.name === 'NotAllowedError') {
        errorMessage += 'Please allow camera permissions and try again.';
      } else if (error.name === 'NotFoundError') {
        errorMessage += 'No camera found on this device.';
      } else if (error.name === 'NotSupportedError') {
        errorMessage += 'Camera not supported by this browser.';
      } else if (error.name === 'OverconstrainedError') {
        errorMessage += 'Camera constraints not supported.';
      } else {
        errorMessage += `Error: ${error.message || 'Unknown camera error'}`;
      }
      
      setCameraLoading(false);
      setCameraError(errorMessage);
      onError(errorMessage);
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    if (scanInterval) {
      clearInterval(scanInterval);
      setScanInterval(null);
    }
    setIsScanning(false);
  };

  const startScanning = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const context = canvas.getContext('2d');

    if (!context) return;

    console.log('Starting QR code scanning...');

    const interval = setInterval(() => {
      if (video.readyState === video.HAVE_ENOUGH_DATA && video.videoWidth > 0 && video.videoHeight > 0) {
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw current video frame to canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Get image data for QR code detection
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        
        // Use jsQR to detect QR codes
        const qrCode = jsQR(imageData.data, imageData.width, imageData.height, {
          inversionAttempts: "dontInvert"
        });
        
        if (qrCode) {
          const currentTime = Date.now();
          // Prevent duplicate scans within 2 seconds
          if (currentTime - lastScanTime > 2000) {
            console.log('QR Code detected:', qrCode.data);
            setLastScanTime(currentTime);
            onScan(qrCode.data);
            // Stop scanning after successful detection
            if (interval) {
              clearInterval(interval);
              setScanInterval(null);
            }
          }
        }
      }
    }, 100); // Scan every 100ms

    setScanInterval(interval);
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
          
          {/* Loading overlay */}
          {cameraLoading && (
            <div className="absolute inset-0 bg-black bg-opacity-75 rounded-lg flex items-center justify-center">
              <div className="text-white text-center">
                <div className="animate-spin text-4xl mb-2">⏳</div>
                <div className="text-sm">Starting camera...</div>
                <div className="text-xs mt-1 opacity-75">Please allow camera access</div>
              </div>
            </div>
          )}

          {/* Error overlay */}
          {cameraError && !cameraLoading && (
            <div className="absolute inset-0 bg-red-900 bg-opacity-75 rounded-lg flex items-center justify-center">
              <div className="text-white text-center p-4">
                <div className="text-3xl mb-2">❌</div>
                <div className="text-sm font-medium mb-2">Camera Error</div>
                <div className="text-xs opacity-90">{cameraError}</div>
              </div>
            </div>
          )}
          
          {/* Scanning overlay */}
          {isScanning && !cameraLoading && !cameraError && (
            <div className="absolute inset-0 border-2 border-green-400 rounded-lg">
              <div className="absolute inset-4 border-2 border-dashed border-green-400 opacity-50 rounded-lg"></div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <div className="animate-pulse text-green-400 text-center">
                  <div className="text-2xl mb-2">🎯</div>
                  <div className="text-sm font-medium">Scanning for QR codes...</div>
                  <div className="text-xs mt-1 opacity-75">Position QR code in frame</div>
                </div>
              </div>
              
              {/* Corner indicators */}
              <div className="absolute top-2 left-2 w-6 h-6 border-l-3 border-t-3 border-green-400"></div>
              <div className="absolute top-2 right-2 w-6 h-6 border-r-3 border-t-3 border-green-400"></div>
              <div className="absolute bottom-2 left-2 w-6 h-6 border-l-3 border-b-3 border-green-400"></div>
              <div className="absolute bottom-2 right-2 w-6 h-6 border-r-3 border-b-3 border-green-400"></div>
            </div>
          )}

          {/* Test scan button for demo */}
          {!cameraLoading && (
            <button
              onClick={() => {
                const testUID = `SKU${String(Math.floor(Math.random() * 999) + 1).padStart(3, '0')}-SCAN-${new Date().toISOString().split('T')[0]}-${String(Math.floor(Math.random() * 99) + 1).padStart(3, '0')}`;
                onScan(testUID);
              }}
              className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded text-sm hover:bg-green-600 shadow-lg"
            >
              🧪 Test Scan
            </button>
          )}
        </div>

        <div className="mt-4 space-y-3">
          <div className="text-sm text-gray-600 text-center">
            {cameraLoading ? (
              <>📷 Initializing camera...</>
            ) : cameraError ? (
              <>❌ Camera unavailable - use manual entry below</>
            ) : isScanning ? (
              <>📦 Point your camera at a UID QR code to scan</>
            ) : (
              <>📷 Camera ready - waiting to start scanning</>
            )}
            <div className="text-xs text-gray-500 mt-1">
              {isScanning ? (
                <>Make sure the QR code is clearly visible and well-lit</>
              ) : (
                <>Use &quot;Test Scan&quot; button for testing or manual entry</>
              )}
            </div>
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={handleManualInput}
              className="flex-1 py-2 px-4 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm font-medium"
            >
              ⌨️ Enter Manually
            </button>
            {cameraError && (
              <button
                onClick={() => {
                  setCameraError(null);
                  setCameraLoading(true);
                  startCamera();
                }}
                className="flex-1 py-2 px-4 bg-orange-500 text-white rounded hover:bg-orange-600 text-sm font-medium"
              >
                🔄 Retry Camera
              </button>
            )}
            <button
              onClick={onClose}
              className="flex-1 py-2 px-4 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm font-medium"
            >
              Cancel
            </button>
          </div>
        </div>

        {cameraError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-center text-sm text-red-700">
            <div className="font-medium">Troubleshooting Tips:</div>
            <div className="text-xs mt-1 space-y-1">
              <div>• Check browser camera permissions</div>
              <div>• Close other apps using the camera</div>
              <div>• Try refreshing the page</div>
              <div>• Use manual entry as backup</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}