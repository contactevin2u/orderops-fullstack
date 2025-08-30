import React from 'react';
import Image from 'next/image';

export default function PodViewer({ url }: { url: string }) {
  const isPdf = /\.pdf($|\?)/i.test(url);
  if (isPdf) {
    return (
      <object data={url} type="application/pdf" style={{ width: '100%', height: '80vh' }} data-testid="pod-pdf">
        <iframe src={url} style={{ width: '100%', height: '80vh' }} />
        <a href={url} target="_blank" rel="noreferrer">Open POD</a>
      </object>
    );
  }
  return (
    <Image 
      src={url} 
      alt="POD" 
      width={800} 
      height={600}
      style={{ maxWidth: '100%', height: 'auto' }} 
      data-testid="pod-image" 
      unoptimized={true}
    />
  );
}
