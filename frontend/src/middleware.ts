import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// This function can be marked `async` if using `await` inside
export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  
  // Only protect /admin and its subpaths
  if (path.startsWith('/admin') && path !== '/admin/login') {
    const adminSession = request.cookies.get('admin_session');
    
    if (!adminSession) {
      // Redirect to login if no session cookie exists
      return NextResponse.redirect(new URL('/admin/login', request.url));
    }
  }
  
  // If navigating to login page but already logged in, redirect to dashboard
  if (path === '/admin/login') {
    const adminSession = request.cookies.get('admin_session');
    if (adminSession) {
      return NextResponse.redirect(new URL('/admin', request.url));
    }
  }

  return NextResponse.next();
}

// See "Matching Paths" below to learn more
export const config = {
  matcher: '/admin/:path*',
};
