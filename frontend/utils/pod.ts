export function resolvePodUrl(url: string | undefined): string {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  const base = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  if (!base) {
    if (typeof console !== 'undefined') {
      console.warn('NEXT_PUBLIC_API_URL not set; relying on rewrite for /static/uploads');
    }
    return url;
  }
  return `${base}${url}`;
}
