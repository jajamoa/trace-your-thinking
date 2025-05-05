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

export function middleware(request: NextRequest) {
  const userAgent = request.headers.get('user-agent') || ''
  const isMobile = isMobileDevice(userAgent)
  const { pathname } = request.nextUrl

  // If it's a mobile device and not in the allowed paths, redirect to home page
  if (isMobile && !ALLOWED_MOBILE_PATHS.includes(pathname)) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

// Configure which paths the middleware applies to
export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - API routes
     * - Static files (images, JS, etc.)
     * - favicon.ico
     */
    '/((?!api|_next/static|_next/image|favicon.ico|mit-logo.svg|og-image.png).*)',
  ],
} 