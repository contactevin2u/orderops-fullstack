import React from 'react';
import { render, screen } from '@testing-library/react';
import PodViewer from '@/components/PodViewer';

describe('PodViewer', () => {
  it('renders image for image url', () => {
    render(<PodViewer url="https://example.com/pod.jpg" />);
    expect(screen.getByTestId('pod-image')).toBeInTheDocument();
  });

  it('renders pdf viewer for pdf url', () => {
    render(<PodViewer url="https://example.com/pod.pdf" />);
    expect(screen.getByTestId('pod-pdf')).toBeInTheDocument();
  });
});
