import { NextResponse } from "next/server"

// Access the in-memory storage (in a real app, this would be a database)
// This is just for demonstration - in a real app, you'd use a proper database
declare global {
  var sessions: Record<string, any>
}

if (!global.sessions) {
  global.sessions = {}
}

export async function GET(request: Request, { params }: { params: { id: string } }) {
  const sessionId = params.id

  if (!global.sessions[sessionId]) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 })
  }

  return NextResponse.json(global.sessions[sessionId])
}

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const sessionId = params.id
    const body = await request.json()

    if (!global.sessions[sessionId]) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    // Update the session
    global.sessions[sessionId] = {
      ...global.sessions[sessionId],
      ...body,
      updatedAt: new Date().toISOString(),
    }

    return NextResponse.json({
      success: true,
      session: global.sessions[sessionId],
    })
  } catch (error) {
    console.error("Error updating session:", error)
    return NextResponse.json({ error: "Failed to update session" }, { status: 500 })
  }
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  try {
    const sessionId = params.id
    const body = await request.json()

    if (!global.sessions[sessionId]) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    // Update specific fields
    global.sessions[sessionId] = {
      ...global.sessions[sessionId],
      ...body,
      updatedAt: new Date().toISOString(),
    }

    return NextResponse.json({
      success: true,
      session: global.sessions[sessionId],
    })
  } catch (error) {
    console.error("Error updating session:", error)
    return NextResponse.json({ error: "Failed to update session" }, { status: 500 })
  }
}
