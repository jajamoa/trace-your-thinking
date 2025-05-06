import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

// Admin authentication verification function
// Returns null if authentication is successful, otherwise returns an error response
export async function verifyAdmin() {
  try {
    // Use a simpler cookie checking approach
    const cookieStr = cookies().toString();
    const isAuthenticated = cookieStr.includes('admin_authenticated=true');
  
    if (!isAuthenticated) {
      return NextResponse.json({ error: 'Unauthorized access' }, { status: 401 });
    }
    
    return null; // Authentication successful
  } catch (error) {
    console.error('Auth verification error:', error);
    return NextResponse.json({ error: 'Authentication error' }, { status: 500 });
  }
} 