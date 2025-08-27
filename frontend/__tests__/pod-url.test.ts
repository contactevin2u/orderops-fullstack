import { resolvePodUrl } from '@/utils/pod';

describe('resolvePodUrl', () => {
  it('returns absolute url when env set', () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
    expect(resolvePodUrl('/static/uploads/a.jpg')).toBe('https://api.example.com/static/uploads/a.jpg');
  });

  it('returns as-is when already absolute', () => {
    expect(resolvePodUrl('https://x.com/a.jpg')).toBe('https://x.com/a.jpg');
  });
});
