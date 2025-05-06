import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

/**
 * Admin authentication password from environment variables
 * Set ADMIN_PASSWORD in your .env.local file for security
 * Example: ADMIN_PASSWORD=your_secure_password
 */
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123'; // Default fallback for development only

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { password } = body;
    console.log('Received password:', password);
    console.log('Expected password:', ADMIN_PASSWORD);
    console.log('Password correct:', password === ADMIN_PASSWORD);
    // Verify that the submitted password matches the configured admin password
    if (password !== ADMIN_PASSWORD) {
      return NextResponse.json({ error: 'Incorrect password' }, { status: 401 });
    }

    // Set authentication cookie with security options
    const response = NextResponse.json({ success: true });
    response.cookies.set('admin_authenticated', 'true', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24, // 1 day
      path: '/',
    });

    return response;
  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
} 