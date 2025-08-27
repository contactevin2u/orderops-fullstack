import React from 'react';

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
    <div>
      <img src={url} alt="POD" style={{ maxWidth: '100%', height: 'auto' }} data-testid="pod-image" />
      <p>
        <button
          type="button"
          onClick={() => window.open(url, '_blank', 'noopener,noreferrer')}
        >
          Open POD
        </button>
      </p>
    </div>
  );
}
