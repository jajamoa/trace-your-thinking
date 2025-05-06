import { NextResponse } from "next/server"
import connectToDatabase from "../../../lib/mongodb"
import GuidingQuestion from "../../../models/GuidingQuestion"

/**
 * Get all guiding questions
 * GET /api/guiding-questions
 * Optional query params:
 * - active: boolean - filter by active status
 * - category: string - filter by category
 */
export async function GET(request: Request) {
  try {
    await connectToDatabase()
    
    const { searchParams } = new URL(request.url)
    const activeParam = searchParams.get("active")
    const category = searchParams.get("category")
    
    // Build query filters
    const filter: any = {}
    
    if (activeParam !== null) {
      filter.isActive = activeParam === "true"
    }
    
    if (category) {
      filter.category = category
    }
    
    // Get questions ordered by the order field
    const questions = await GuidingQuestion.find(filter).sort({ order: 1 })
    
    return NextResponse.json({ questions })
  } catch (error) {
    console.error("Error retrieving guiding questions:", error)
    return NextResponse.json({ error: "Failed to retrieve guiding questions" }, { status: 500 })
  }
}

/**
 * Create a new guiding question
 * POST /api/guiding-questions
 */
export async function POST(request: Request) {
  try {
    await connectToDatabase()
    
    const body = await request.json()
    
    // Validate required fields
    if (!body.text || !body.shortText) {
      return NextResponse.json({ 
        error: "Text and shortText are required fields" 
      }, { status: 400 })
    }
    
    // Generate a unique ID
    const id = `gq_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
    
    // Get current max order value
    const maxOrderQuestion = await GuidingQuestion.findOne().sort({ order: -1 })
    const nextOrder = maxOrderQuestion ? maxOrderQuestion.order + 1 : 0
    
    // Create the new guiding question
    const newQuestion = new GuidingQuestion({
      id,
      text: body.text,
      shortText: body.shortText,
      category: body.category || "general",
      isActive: body.isActive !== undefined ? body.isActive : true,
      order: body.order !== undefined ? body.order : nextOrder
    })
    
    await newQuestion.save()
    
    return NextResponse.json({
      success: true,
      question: newQuestion
    })
  } catch (error) {
    console.error("Error creating guiding question:", error)
    return NextResponse.json({ error: "Failed to create guiding question" }, { status: 500 })
  }
} 