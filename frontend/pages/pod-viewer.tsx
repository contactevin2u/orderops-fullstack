import React from 'react';
import { useRouter } from 'next/router';
import PodViewer from '@/components/PodViewer';

export default function PodViewerPage() {
  const router = useRouter();
  const { url } = router.query;
  const src = typeof url === 'string' ? decodeURIComponent(url) : '';
  if (!src) return <p>No POD</p>;
  return <PodViewer url={src} />;
}
