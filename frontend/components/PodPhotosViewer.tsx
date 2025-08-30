import React, { useState } from 'react';
import Link from 'next/link';

interface PodPhotosViewerProps {
  podPhotoUrls: string[];
  legacyPodUrl?: string | null;
}

export default function PodPhotosViewer({ podPhotoUrls = [], legacyPodUrl }: PodPhotosViewerProps) {
  const [showModal, setShowModal] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  
  // Combine new photo URLs with legacy URL for backward compatibility
  const allPhotos = [...podPhotoUrls];
  if (legacyPodUrl && !podPhotoUrls.includes(legacyPodUrl)) {
    allPhotos.unshift(legacyPodUrl);
  }
  
  // Ensure URLs are absolute
  const photos = allPhotos.map(url => {
    if (!url) return null;
    return url.startsWith('http') ? url : `${apiBase}${url}`;
  }).filter(Boolean);

  if (photos.length === 0) {
    return (
      <div className="text-gray-400 text-sm italic">
        No photos
      </div>
    );
  }

  const isPdf = (url: string) => /\.pdf($|\?)/i.test(url);
  
  return (
    <div className="pod-photos-viewer">
      {/* Thumbnail row */}
      <div className="flex gap-1">
        {photos.map((photo, index) => (
          <div key={index} className="relative group">
            {isPdf(photo) ? (
              <Link
                href={`/pod-viewer?url=${encodeURIComponent(photo)}`}
                className="flex items-center justify-center w-12 h-12 bg-red-100 text-red-600 text-xs rounded border hover:bg-red-200 transition-colors"
                target="_blank"
              >
                PDF
              </Link>
            ) : (
              <button
                onClick={() => {
                  setCurrentImageIndex(index);
                  setShowModal(true);
                }}
                className="w-12 h-12 bg-gray-100 rounded border overflow-hidden hover:opacity-80 transition-opacity"
              >
                <img
                  src={photo}
                  alt={`PoD photo ${index + 1}`}
                  className="w-full h-full object-cover"
                />
              </button>
            )}
            {/* Photo number indicator */}
            <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
              {index + 1}
            </span>
          </div>
        ))}
      </div>
      
      {/* Count indicator */}
      <div className="text-xs text-gray-500 mt-1">
        {photos.length} photo{photos.length !== 1 ? 's' : ''}
      </div>

      {/* Modal for full-size image viewing */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="relative max-w-4xl max-h-full p-4">
            {/* Close button */}
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-2 right-2 bg-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-gray-100 z-10"
            >
              ×
            </button>
            
            {/* Navigation arrows */}
            {photos.length > 1 && (
              <>
                <button
                  onClick={() => setCurrentImageIndex((prev) => (prev - 1 + photos.length) % photos.length)}
                  className="absolute left-2 top-1/2 transform -translate-y-1/2 bg-white rounded-full w-10 h-10 flex items-center justify-center hover:bg-gray-100"
                >
                  ←
                </button>
                <button
                  onClick={() => setCurrentImageIndex((prev) => (prev + 1) % photos.length)}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-white rounded-full w-10 h-10 flex items-center justify-center hover:bg-gray-100"
                >
                  →
                </button>
              </>
            )}
            
            {/* Current image */}
            <div className="bg-white rounded-lg p-2">
              <img
                src={photos[currentImageIndex]}
                alt={`PoD photo ${currentImageIndex + 1}`}
                className="max-w-full max-h-[80vh] object-contain mx-auto block"
              />
              <div className="text-center text-gray-600 text-sm mt-2">
                Photo {currentImageIndex + 1} of {photos.length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}