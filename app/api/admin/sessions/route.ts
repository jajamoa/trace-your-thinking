import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import connectToDatabase from '@/lib/mongodb';
import Session from '@/models/Session';

// Admin authentication middleware function
const verifyAdmin = async (req: NextRequest) => {
  // Use a simpler cookie checking approach
  const cookieStore = await cookies();
  const adminCookie = cookieStore.get('admin_authenticated');
  const isAuthenticated = adminCookie?.value === 'true';

  if (!isAuthenticated) {
    return NextResponse.json({ error: 'Unauthorized access' }, { status: 401 });
  }
  
  return null; // Verification successful
};

// Get all sessions with pagination
export async function GET(req: NextRequest) {
  // Verify admin authentication
  const authError = await verifyAdmin(req);
  if (authError) return authError;

  try {
    // Connect to database
    await connectToDatabase();
    
    // Parse pagination parameters from query
    const url = new URL(req.url);
    const pageParam = url.searchParams.get('page');
    const limitParam = url.searchParams.get('limit');
    
    const page = pageParam ? parseInt(pageParam) : 1;
    const limit = limitParam ? parseInt(limitParam) : 30;
    const skip = (page - 1) * limit;
    
    // Get total count for pagination
    const total = await Session.countDocuments({});
    const totalPages = Math.ceil(total / limit);
    
    // Get paginated sessions, sorted by creation date in descending order
    const sessions = await Session.find({})
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit)
      .lean();
    
    // Return sessions with pagination metadata
    return NextResponse.json({
      sessions,
      pagination: {
        currentPage: page,
        totalPages,
        totalItems: total,
        itemsPerPage: limit
      }
    });
  } catch (error: any) {
    console.error('Error fetching sessions:', error);
    return NextResponse.json(
      { error: `Failed to fetch sessions: ${error.message}` },
      { status: 500 }
    );
  }
} 