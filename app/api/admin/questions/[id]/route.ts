import { NextRequest, NextResponse } from 'next/server';
import connectToDatabase from '@/lib/mongodb';
import GuidingQuestionModel from '@/models/GuidingQuestion';

// GET - Fetch a single question by ID
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await connectToDatabase();
    const questionId = params.id;
    
    const question = await GuidingQuestionModel.findOne({ id: questionId }).lean();
    
    if (!question) {
      return NextResponse.json(
        { error: 'Question not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ question });
  } catch (error) {
    console.error('Error fetching question:', error);
    return NextResponse.json(
      { error: 'Failed to fetch question' },
      { status: 500 }
    );
  }
}

// PUT - Update a question by ID
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await connectToDatabase();
    const questionId = params.id;
    
    const body = await request.json();
    const { text, shortText, category, isActive } = body;
    
    if (!text || !shortText) {
      return NextResponse.json(
        { error: 'Text and shortText are required' },
        { status: 400 }
      );
    }
    
    const updatedQuestion = await GuidingQuestionModel.findOneAndUpdate(
      { id: questionId },
      {
        text,
        shortText,
        category,
        isActive: isActive !== undefined ? isActive : true,
        updatedAt: new Date()
      },
      { new: true }
    ).lean();
    
    if (!updatedQuestion) {
      return NextResponse.json(
        { error: 'Question not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json({ 
      success: true,
      question: updatedQuestion 
    });
  } catch (error) {
    console.error('Error updating question:', error);
    return NextResponse.json(
      { error: 'Failed to update question' },
      { status: 500 }
    );
  }
}

// DELETE - Remove a question by ID
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await connectToDatabase();
    const questionId = params.id;
    
    const deletedQuestion = await GuidingQuestionModel.findOneAndDelete({ id: questionId });
    
    if (!deletedQuestion) {
      return NextResponse.json(
        { error: 'Question not found' },
        { status: 404 }
      );
    }
    
    // Reorder remaining questions to ensure no gaps in order
    const remainingQuestions = await GuidingQuestionModel.find({})
      .sort({ order: 1 })
      .lean();
    
    // Update order for all remaining questions
    for (let i = 0; i < remainingQuestions.length; i++) {
      await GuidingQuestionModel.findOneAndUpdate(
        { _id: remainingQuestions[i]._id },
        { order: i }
      );
    }
    
    return NextResponse.json({ 
      success: true,
      message: 'Question deleted successfully' 
    });
  } catch (error) {
    console.error('Error deleting question:', error);
    return NextResponse.json(
      { error: 'Failed to delete question' },
      { status: 500 }
    );
  }
} 