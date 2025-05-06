import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import connectToDatabase from '@/lib/mongodb';
import Session from '@/models/Session';

// Admin authentication middleware function
const verifyAdmin = async () => {
  // Use a simpler cookie checking approach
  const cookieStr = cookies().toString();
  const isAuthenticated = cookieStr.includes('admin_authenticated=true');

  if (!isAuthenticated) {
    return NextResponse.json({ error: 'Unauthorized access' }, { status: 401 });
  }
  
  return null; // Verification successful
};

// Get single session details
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  // Verify admin authentication
  const authError = await verifyAdmin();
  if (authError) return authError;

  const { id } = params;

  try {
    // Connect to database
    await connectToDatabase();
    
    // Find session by ID
    const session = await Session.findOne({ id }).lean();
    
    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ session });
  } catch (error: any) {
    console.error('Error fetching session details:', error);
    return NextResponse.json(
      { error: `Failed to fetch session details: ${error.message}` },
      { status: 500 }
    );
  }
} 