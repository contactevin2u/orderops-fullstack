import React from 'react';
import { useRouter } from 'next/router';
import PodViewer from '@/components/PodViewer';
import { resolvePodUrl } from '@/utils/pod';

export default function PodViewerPage() {
  const router = useRouter();
  const { url } = router.query;
  const src = typeof url === 'string' ? resolvePodUrl(decodeURIComponent(url)) : '';
  if (!src) return <p>No POD</p>;
  return <PodViewer url={src} />;
}
