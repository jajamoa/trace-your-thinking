import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import connectToDatabase from '@/lib/mongodb';
import Session from '@/models/Session';

// Admin authentication middleware function
const verifyAdmin = async () => {
  // Use a simpler cookie checking approach
  const cookieStore = await cookies();
  const adminCookie = cookieStore.get('admin_authenticated');
  const isAuthenticated = adminCookie?.value === 'true';

  if (!isAuthenticated) {
    return NextResponse.json({ error: 'Unauthorized access' }, { status: 401 });
  }
  
  return null; // Verification successful
};

// POST - Delete a session
export async function POST(
  req: NextRequest,
  context: { params: { id: string } }
) {
  // Verify admin authentication
  const authError = await verifyAdmin();
  if (authError) return authError;

  const params = await context.params;
  const { id } = params;

  try {
    // Connect to database
    await connectToDatabase();
    
    // Find and delete the session
    const session = await Session.findOneAndDelete({ id });
    
    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ 
      success: true,
      message: 'Session deleted successfully',
      sessionId: id
    });
  } catch (error: any) {
    console.error('Error deleting session:', error);
    return NextResponse.json(
      { error: `Failed to delete session: ${error.message}` },
      { status: 500 }
    );
  }
} 