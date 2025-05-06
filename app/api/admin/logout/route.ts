import { NextResponse } from 'next/server';

export async function GET() {
  const response = NextResponse.redirect(new URL('/admin/login', process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'));
  
  response.cookies.set('admin_authenticated', '', {
    httpOnly: true,
    expires: new Date(0),
    path: '/',
  });
  
  return response;
} 