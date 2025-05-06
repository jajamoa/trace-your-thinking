import { NextRequest, NextResponse } from 'next/server';
import connectToDatabase from '@/lib/mongodb';
import GuidingQuestionModel from '@/models/GuidingQuestion';

// POST - Reorder a question (move up or down)
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await connectToDatabase();
    
    const body = await request.json();
    const { newOrder } = body;
    const questionId = params.id;
    
    if (newOrder === undefined || typeof newOrder !== 'number') {
      return NextResponse.json(
        { error: 'New order is required and must be a number' },
        { status: 400 }
      );
    }
    
    // Find the current question using the custom id field, not _id
    const currentQuestion = await GuidingQuestionModel.findOne({ id: questionId });
    
    if (!currentQuestion) {
      return NextResponse.json(
        { error: 'Question not found' },
        { status: 404 }
      );
    }
    
    const currentOrder = currentQuestion.order;
    
    // Find the question at the target position
    const targetQuestion = await GuidingQuestionModel.findOne({ order: newOrder });
    
    if (!targetQuestion) {
      return NextResponse.json(
        { error: 'Target position not found' },
        { status: 404 }
      );
    }
    
    // Swap the order of the two questions
    targetQuestion.order = currentOrder;
    currentQuestion.order = newOrder;
    
    await Promise.all([
      targetQuestion.save(),
      currentQuestion.save()
    ]);
    
    return NextResponse.json({ 
      success: true,
      message: 'Question reordered successfully' 
    });
  } catch (error) {
    console.error('Error reordering question:', error);
    return NextResponse.json(
      { error: 'Failed to reorder question' },
      { status: 500 }
    );
  }
} 