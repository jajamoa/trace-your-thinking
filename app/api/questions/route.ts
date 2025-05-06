import { NextResponse } from "next/server"
import connectToDatabase from "../../../lib/mongodb"
import Session from "../../../models/Session"
import { Question } from "@/lib/store"

/**
 * API endpoint to add a new question to a session
 * POST /api/questions
 */
export async function POST(request: Request) {
  try {
    await connectToDatabase()
    
    // Parse request body
    const body = await request.json()
    const { sessionId, question } = body
    
    if (!sessionId) {
      return NextResponse.json({ error: "Session ID is required" }, { status: 400 })
    }
    
    if (!question || !question.text || !question.shortText) {
      return NextResponse.json({ 
        error: "Question must include text and shortText fields" 
      }, { status: 400 })
    }
    
    // Generate an ID for the new question
    const newQuestion: Question = {
      id: `q${Date.now()}`,
      text: question.text,
      shortText: question.shortText
    }
    
    // Find the session
    const session = await Session.findOne({ id: sessionId })
    
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }
    
    // Add the new question to the questions and pendingQuestions arrays
    const updatedSession = await Session.findOneAndUpdate(
      { id: sessionId },
      { 
        $push: { 
          questions: newQuestion,
          pendingQuestions: newQuestion
        },
        $set: {
          updatedAt: new Date()
        }
      },
      { new: true }
    )
    
    return NextResponse.json({
      success: true,
      question: newQuestion,
      session: updatedSession
    })
    
  } catch (error) {
    console.error("Error adding question:", error)
    return NextResponse.json({ error: "Failed to add question" }, { status: 500 })
  }
}

/**
 * API endpoint to get all questions for a session
 * GET /api/questions?sessionId=xxx
 */
export async function GET(request: Request) {
  try {
    await connectToDatabase()
    
    // Get session ID from query params
    const { searchParams } = new URL(request.url)
    const sessionId = searchParams.get("sessionId")
    
    if (!sessionId) {
      return NextResponse.json({ error: "Session ID is required" }, { status: 400 })
    }
    
    // Find the session
    const session = await Session.findOne({ id: sessionId })
    
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }
    
    return NextResponse.json({
      questions: session.questions || [],
      pendingQuestions: session.pendingQuestions || []
    })
    
  } catch (error) {
    console.error("Error retrieving questions:", error)
    return NextResponse.json({ error: "Failed to retrieve questions" }, { status: 500 })
  }
} 