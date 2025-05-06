import { NextResponse } from "next/server"
import connectToDatabase from "../../../../lib/mongodb"
import GuidingQuestion from "../../../../models/GuidingQuestion"

/**
 * Get a specific guiding question by ID
 * GET /api/guiding-questions/:id
 */
export async function GET(
  request: Request, 
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()
    
    const params = await context.params
    const questionId = params.id
    
    const question = await GuidingQuestion.findOne({ id: questionId })
    
    if (!question) {
      return NextResponse.json({ error: "Guiding question not found" }, { status: 404 })
    }
    
    return NextResponse.json(question)
  } catch (error) {
    console.error("Error retrieving guiding question:", error)
    return NextResponse.json({ error: "Failed to retrieve guiding question" }, { status: 500 })
  }
}

/**
 * Update a guiding question
 * PUT /api/guiding-questions/:id
 */
export async function PUT(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()
    
    const params = await context.params
    const questionId = params.id
    const body = await request.json()
    
    // Find the question first
    const question = await GuidingQuestion.findOne({ id: questionId })
    
    if (!question) {
      return NextResponse.json({ error: "Guiding question not found" }, { status: 404 })
    }
    
    // Update allowed fields
    const updatedQuestion = await GuidingQuestion.findOneAndUpdate(
      { id: questionId },
      { 
        $set: {
          text: body.text !== undefined ? body.text : question.text,
          shortText: body.shortText !== undefined ? body.shortText : question.shortText,
          category: body.category !== undefined ? body.category : question.category,
          isActive: body.isActive !== undefined ? body.isActive : question.isActive,
          order: body.order !== undefined ? body.order : question.order,
          updatedAt: new Date()
        }
      },
      { new: true }
    )
    
    return NextResponse.json({
      success: true,
      question: updatedQuestion
    })
  } catch (error) {
    console.error("Error updating guiding question:", error)
    return NextResponse.json({ error: "Failed to update guiding question" }, { status: 500 })
  }
}

/**
 * Delete a guiding question
 * DELETE /api/guiding-questions/:id
 */
export async function DELETE(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()
    
    const params = await context.params
    const questionId = params.id
    
    const result = await GuidingQuestion.deleteOne({ id: questionId })
    
    if (result.deletedCount === 0) {
      return NextResponse.json({ error: "Guiding question not found" }, { status: 404 })
    }
    
    return NextResponse.json({
      success: true,
      message: "Guiding question deleted successfully"
    })
  } catch (error) {
    console.error("Error deleting guiding question:", error)
    return NextResponse.json({ error: "Failed to delete guiding question" }, { status: 500 })
  }
} 