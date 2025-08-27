import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

const PROTECTED_PATHS = ['/orders', '/export', '/cashier', '/adjustments', '/reports'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (
    pathname === '/login' ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/static') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next();
  }
  const needsAuth = PROTECTED_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  );
  if (needsAuth && !request.cookies.get('token')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)'],
};

