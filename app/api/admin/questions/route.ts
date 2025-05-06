import { NextRequest, NextResponse } from 'next/server';
import connectToDatabase from '@/lib/mongodb';
import GuidingQuestionModel, { IGuidingQuestion } from '@/models/GuidingQuestion';

// GET - Fetch all guiding questions
export async function GET() {
  try {
    await connectToDatabase();
    
    const questions = await GuidingQuestionModel.find({})
      .sort({ order: 1 })
      .lean();
    
    return NextResponse.json({ questions });
  } catch (error) {
    console.error('Error fetching questions:', error);
    return NextResponse.json(
      { error: 'Failed to fetch questions' },
      { status: 500 }
    );
  }
}

// POST - Create a new guiding question
export async function POST(request: NextRequest) {
  try {
    await connectToDatabase();
    
    const body = await request.json();
    const { text, shortText, category, isActive } = body;
    
    if (!text || !shortText) {
      return NextResponse.json(
        { error: 'Text and shortText are required' },
        { status: 400 }
      );
    }
    
    // Find highest order to place new question at the end
    const highestOrder = await GuidingQuestionModel.findOne({})
      .sort({ order: -1 })
      .lean() as unknown as { order: number } | null;
    
    const newOrder = highestOrder ? highestOrder.order + 1 : 0;
    
    // Generate a new ID with 'gq' prefix
    // Find the highest existing ID number to ensure uniqueness
    const lastQuestion = await GuidingQuestionModel.findOne({})
      .sort({ id: -1 })
      .lean() as unknown as { id: string } | null;
    
    let newIdNumber = 1;
    if (lastQuestion && lastQuestion.id) {
      const match = lastQuestion.id.match(/^gq(\d+)$/);
      if (match && match[1]) {
        newIdNumber = parseInt(match[1], 10) + 1;
      }
    }
    
    const newQuestionId = `gq${newIdNumber}`;
    
    const newQuestion = new GuidingQuestionModel({
      id: newQuestionId,
      text,
      shortText,
      category,
      isActive: isActive !== undefined ? isActive : true,
      order: newOrder
    });
    
    await newQuestion.save();
    
    return NextResponse.json({ 
      success: true,
      question: newQuestion 
    });
  } catch (error) {
    console.error('Error creating question:', error);
    return NextResponse.json(
      { error: 'Failed to create question' },
      { status: 500 }
    );
  }
} 