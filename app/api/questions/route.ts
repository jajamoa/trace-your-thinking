import { NextResponse } from "next/server"
import connectToDatabase from "../../../lib/mongodb"
import Session from "../../../models/Session"
import { QAPair } from "@/lib/store"

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
    
    if (!question || !question.question || !question.shortText) {
      return NextResponse.json({ 
        error: "Question must include question text and shortText fields" 
      }, { status: 400 })
    }
    
    // Generate an ID for the new question
    const newQAPair: QAPair = {
      id: `q${Date.now()}`,
      question: question.question,
      shortText: question.shortText,
      answer: ""
    }
    
    // Find the session
    const session = await Session.findOne({ id: sessionId })
    
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }
    
    // Add the new question to the qaPairs array
    const updatedSession = await Session.findOneAndUpdate(
      { id: sessionId },
      { 
        $push: { 
          qaPairs: newQAPair
        },
        $set: {
          updatedAt: new Date()
        }
      },
      { new: true }
    )
    
    // Also update the progress.total value to include the new question
    await Session.findOneAndUpdate(
      { id: sessionId },
      {
        $set: {
          "progress.total": (session.qaPairs || []).length + 1
        }
      }
    )
    
    return NextResponse.json({
      success: true,
      qaPair: newQAPair,
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
    
    // Return all QA pairs and current question index
    return NextResponse.json({
      qaPairs: session.qaPairs || [],
      currentQuestionIndex: session.currentQuestionIndex || 0
    })
    
  } catch (error) {
    console.error("Error retrieving questions:", error)
    return NextResponse.json({ error: "Failed to retrieve questions" }, { status: 500 })
  }
} 