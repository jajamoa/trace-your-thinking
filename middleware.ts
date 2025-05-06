import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Detect mobile devices using user agent
function isMobileDevice(userAgent: string) {
  return Boolean(
    userAgent.match(
      /Android|BlackBerry|iPhone|iPad|iPod|Opera Mini|IEMobile|WPDesktop/i
    )
  )
}

// Paths that mobile devices are allowed to access
const ALLOWED_MOBILE_PATHS = ['/', '/about', '/mit-logo.svg', '/og-image.png']

// Paths that should be excluded from session checks and other middleware processing
// But still subject to mobile device restrictions
const EXCLUDED_PATHS = ['/admin', '/admin/login', '/admin/logout', '/api/admin']

export function middleware(request: NextRequest) {
  const userAgent = request.headers.get('user-agent') || ''
  const isMobile = isMobileDevice(userAgent)
  const { pathname } = request.nextUrl

  // First check: If it's a mobile device and not in the allowed paths, redirect to home page
  // This applies to all paths including admin and excluded paths
  if (isMobile && !ALLOWED_MOBILE_PATHS.includes(pathname)) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  // Second check: Skip additional middleware processing for excluded paths
  // This only applies if we've passed the mobile device check
  if (EXCLUDED_PATHS.some(path => pathname.startsWith(path))) {
    return NextResponse.next()
  }

  return NextResponse.next()
}

// Configure which paths the middleware applies to
export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - API routes (except admin API routes, which need mobile checks)
     * - Static files (images, JS, etc.)
     * - favicon.ico
     */
    '/((?!api/(?!admin)|_next/static|_next/image|favicon.ico|mit-logo.svg|og-image.png).*)',
  ],
} 