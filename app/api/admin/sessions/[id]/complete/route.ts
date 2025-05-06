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

// POST - Mark a session as completed
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
    
    // Find and update the session
    const session = await Session.findOne({ id });
    
    if (!session) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      );
    }
    
    // Update the session
    session.status = 'completed';
    session.completedAt = new Date();
    session.updatedAt = new Date();
    
    await session.save();
    
    return NextResponse.json({ 
      success: true,
      message: 'Session marked as completed',
      session
    });
  } catch (error: any) {
    console.error('Error marking session as completed:', error);
    return NextResponse.json(
      { error: `Failed to mark session as completed: ${error.message}` },
      { status: 500 }
    );
  }
} 