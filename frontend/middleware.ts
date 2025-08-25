export { default } from 'next-auth/middleware';

export const config = {
  matcher: ['/orders', '/export', '/cashier', '/adjustments', '/reports/:path*'],
};

