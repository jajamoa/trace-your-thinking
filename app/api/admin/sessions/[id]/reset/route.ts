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

// POST - Reset a session to initial state
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
    
    // Reset the session
    session.status = 'in_progress';
    session.progress = { current: 0, total: session.progress.total || 0 };
    session.currentQuestionIndex = 0;
    session.completedAt = undefined;
    session.updatedAt = new Date();
    
    // Clear answers but keep questions
    if (session.qaPairs && Array.isArray(session.qaPairs)) {
      session.qaPairs = session.qaPairs.map((pair: any) => ({
        ...pair,
        answer: ''
      }));
    }
    
    await session.save();
    
    return NextResponse.json({ 
      success: true,
      message: 'Session reset successfully',
      session
    });
  } catch (error: any) {
    console.error('Error resetting session:', error);
    return NextResponse.json(
      { error: `Failed to reset session: ${error.message}` },
      { status: 500 }
    );
  }
} 