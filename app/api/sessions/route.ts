import { NextResponse } from "next/server"
import connectToDatabase from "../../../lib/mongodb"
import Session from "../../../models/Session"
import GuidingQuestion from "../../../models/GuidingQuestion"

// Legacy initial questions as fallback (will be removed once all clients use GuidingQuestion)
const initialQuestions = [
  {
    id: "q1",
    question: "Could you describe your current research focus and how it relates to the broader field?",
    shortText: "Research focus",
    answer: ""
  },
  {
    id: "q2",
    question: "Could you elaborate on the methodologies you're using in your current project?",
    shortText: "Methodologies",
    answer: ""
  },
  {
    id: "q3",
    question: "What challenges have you encountered in your research, and how have you addressed them?",
    shortText: "Challenges",
    answer: ""
  },
];

// Helper function to load active guiding questions
async function getActiveGuidingQuestions() {
  try {
    // Get active guiding questions ordered by the order field
    const guidingQuestions = await GuidingQuestion.find({ isActive: true }).sort({ order: 1 })
    
    if (guidingQuestions && guidingQuestions.length > 0) {
      // Return guiding questions directly as QAPairs
      return guidingQuestions.map(q => ({
        id: q.id,
        question: q.text,
        shortText: q.shortText,
        answer: ""
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
    const prolificId = searchParams.get("prolificId")

    if (!prolificId) {
      return NextResponse.json({ error: "Missing prolificId parameter" }, { status: 400 })
      }
    
    // Find all sessions for this prolificId
    const sessions = await Session.find({ prolificId }).sort({ createdAt: -1 })
    
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

    if (!body.prolificId) {
      return NextResponse.json({ error: "Missing prolificId" }, { status: 400 })
    }

    // Generate a timestamp-based ID
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`

    // Create initial QA pairs from guiding questions or defaults
    let qaPairs = body.qaPairs || []
    
    // If no QA pairs provided, load from guiding questions
    if (qaPairs.length === 0) {
      qaPairs = await getActiveGuidingQuestions()
    }
    
    // Calculate initial progress
    const progress = body.progress || {
      current: 0,
      total: qaPairs.length
    }

    // Create the new session
    const newSession = new Session({
      id: sessionId,
      prolificId: body.prolificId,
      status: body.status || "in_progress",
      qaPairs: qaPairs,
      messages: body.messages || [],
      progress: progress,
      currentQuestionIndex: body.currentQuestionIndex || 0,
      createdAt: new Date(),
      updatedAt: new Date()
    })

    await newSession.save()

    return NextResponse.json({
      success: true,
      sessionId: newSession.id
    })
  } catch (error) {
    console.error("Error creating session:", error)
    return NextResponse.json({ error: "Failed to create session" }, { status: 500 })
  }
}
