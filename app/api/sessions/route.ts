import { NextResponse } from "next/server"

// In-memory storage for sessions (would be replaced by MongoDB in production)
const sessions: Record<string, any> = {}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const sessionId = searchParams.get("id")

  if (!sessionId) {
    return NextResponse.json({ sessions: Object.values(sessions) })
  }

  const session = sessions[sessionId]
  if (!session) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 })
  }

  return NextResponse.json(session)
}

export async function POST(request: Request) {
  try {
    const body = await request.json()

    if (!body.prolificId) {
      return NextResponse.json({ error: "Prolific ID is required" }, { status: 400 })
    }

    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`

    const newSession = {
      id: sessionId,
      prolificId: body.prolificId,
      qaPairs: body.qaPairs || [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: "in_progress",
    }

    sessions[sessionId] = newSession

    return NextResponse.json({
      success: true,
      sessionId,
      session: newSession,
    })
  } catch (error) {
    console.error("Error creating session:", error)
    return NextResponse.json({ error: "Failed to create session" }, { status: 500 })
  }
}
