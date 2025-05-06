import { NextResponse } from "next/server"
import connectToDatabase from "../../../lib/mongodb"
import Session from "../../../models/Session"
import GuidingQuestion from "../../../models/GuidingQuestion"

// Legacy initial questions as fallback (will be removed once all clients use GuidingQuestion)
const initialQuestions = [
  {
    id: "q1",
    text: "Could you describe your current research focus and how it relates to the broader field?",
    shortText: "Research focus",
  },
  {
    id: "q2",
    text: "Could you elaborate on the methodologies you're using in your current project?",
    shortText: "Methodologies",
  },
  {
    id: "q3",
    text: "What challenges have you encountered in your research, and how have you addressed them?",
    shortText: "Challenges",
  },
];

// Helper function to load active guiding questions
async function getActiveGuidingQuestions() {
  try {
    // Get active guiding questions ordered by the order field
    const guidingQuestions = await GuidingQuestion.find({ isActive: true }).sort({ order: 1 })
    
    if (guidingQuestions && guidingQuestions.length > 0) {
      return guidingQuestions.map(q => ({
        id: q.id,
        text: q.text,
        shortText: q.shortText
      }))
    }
    
    // Fallback to initial questions if no guiding questions found
    return initialQuestions
  } catch (error) {
    console.error("Error loading guiding questions:", error)
    return initialQuestions
  }
}

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

    // Load guiding questions if not provided in the request
    let questions
    if (body.questions && body.questions.length > 0) {
      questions = body.questions
    } else {
      questions = await getActiveGuidingQuestions()
    }
    
    // For a new session, pendingQuestions is initially all questions
    const pendingQuestions = body.pendingQuestions || [...questions]
    
    // For a new session, qaPairs might be empty or just have questions with no answers
    let qaPairs = body.qaPairs || []
    
    // If qaPairs is empty but we have questions, we should initialize qaPairs
    // with empty answers for each question (this ensures DB structure is consistent)
    if (qaPairs.length === 0 && questions.length > 0) {
      qaPairs = questions.map((q: { id: string; text: string; shortText: string }) => ({
        id: q.id,
        question: q.text,
        answer: ""
      }))
    }
    
    // Set progress based on how many questions are pending vs. total
    const progress = {
      current: questions.length - pendingQuestions.length,
      total: questions.length
    }

    // Create a new session with all fields from store.ts
    const newSession = new Session({
      id: sessionId,
      prolificId: body.prolificId,
      messages: body.messages || [],
      qaPairs: qaPairs,
      pendingQuestions: pendingQuestions,
      questions: questions,
      progress: progress,
      sessionStatus: body.sessionStatus || "in_progress",
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
