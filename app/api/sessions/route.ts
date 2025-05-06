import { NextResponse } from "next/server"
import connectToDatabase from "../../../lib/mongodb"
import Session from "../../../models/Session"

export async function GET(request: Request) {
  try {
    await connectToDatabase()
    
    const { searchParams } = new URL(request.url)
    const sessionId = searchParams.get("id")
    const prolificId = searchParams.get("prolificId")

    if (sessionId) {
      const session = await Session.findOne({ id: sessionId })
      if (!session) {
        return NextResponse.json({ error: "Session not found" }, { status: 404 })
      }
      return NextResponse.json(session)
    }
    
    if (prolificId) {
      const sessions = await Session.find({ prolificId })
      return NextResponse.json({ sessions })
    }
    
    // Limit returned sessions to avoid performance issues
    const sessions = await Session.find().limit(100)
    return NextResponse.json({ sessions })
  } catch (error) {
    console.error("Error retrieving sessions:", error)
    return NextResponse.json({ error: "Failed to retrieve sessions" }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    await connectToDatabase()
    
    const body = await request.json()

    // Validate required fields
    if (!body.prolificId) {
      return NextResponse.json({ error: "Prolific ID is required" }, { status: 400 })
    }

    // Generate a unique session ID with timestamp and random string
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`

    // Create a new session with all fields from store.ts
    const newSession = new Session({
      id: sessionId,
      prolificId: body.prolificId,
      qaPairs: body.qaPairs || [],
      // Add the new data structure fields
      pendingQuestions: body.pendingQuestions || [],
      questions: body.questions || [],
      status: body.status || "in_progress",
      // Keep this for backward compatibility
      currentQuestionIndex: body.currentQuestionIndex || 0,
      metadata: body.metadata || {}
    })

    await newSession.save()

    return NextResponse.json({
      success: true,
      sessionId,
      session: newSession
    })
  } catch (error) {
    console.error("Error creating session:", error)
    return NextResponse.json({ error: "Failed to create session" }, { status: 500 })
  }
}
