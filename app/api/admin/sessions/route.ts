import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import connectToDatabase from '@/lib/mongodb';
import Session from '@/models/Session';

// Admin authentication middleware function
const verifyAdmin = async (req: NextRequest) => {
  // Use a simpler cookie checking approach
  const cookieStr = cookies().toString();
  const isAuthenticated = cookieStr.includes('admin_authenticated=true');

  if (!isAuthenticated) {
    return NextResponse.json({ error: 'Unauthorized access' }, { status: 401 });
  }
  
  return null; // Verification successful
};

// Get all sessions
export async function GET(req: NextRequest) {
  // Verify admin authentication
  const authError = await verifyAdmin(req);
  if (authError) return authError;

  try {
    // Connect to database
    await connectToDatabase();
    
    // Get all sessions, sorted by creation date in descending order
    const sessions = await Session.find({})
      .sort({ createdAt: -1 })
      .lean();
    
    return NextResponse.json({ sessions });
  } catch (error: any) {
    console.error('Error fetching sessions:', error);
    return NextResponse.json(
      { error: `Failed to fetch sessions: ${error.message}` },
      { status: 500 }
    );
  }
} 