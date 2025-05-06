import { NextRequest, NextResponse } from 'next/server';
import connectToDatabase from '@/lib/mongodb';
import SessionModel from '@/models/Session';

export async function POST(request: NextRequest) {
  try {
    await connectToDatabase();
    
    const body = await request.json();
    const { sessions } = body;
    
    if (!sessions || !Array.isArray(sessions)) {
      return NextResponse.json(
        { error: 'Sessions array is required' },
        { status: 400 }
      );
    }
    
    // Update each session with its new order
    const updatePromises = sessions.map(session => 
      SessionModel.findByIdAndUpdate(
        session.id,
        { $set: { order: session.order } }
      )
    );
    
    await Promise.all(updatePromises);
    
    return NextResponse.json({ 
      success: true,
      message: 'Session order updated successfully' 
    });
  } catch (error) {
    console.error('Error reordering sessions:', error);
    return NextResponse.json(
      { error: 'Failed to reorder sessions' },
      { status: 500 }
    );
  }
} 