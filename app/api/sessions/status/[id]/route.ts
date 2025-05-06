import { NextResponse } from "next/server"
import connectToDatabase from "../../../../../lib/mongodb"
import Session from "../../../../../models/Session"

/**
 * API endpoint to get the current status of a session
 * GET /api/sessions/status/:id
 */
export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()

    const params = await context.params
    const sessionId = params.id
    
    // Add a small delay to help with potential replication lag
    // This is especially important for newly created sessions
    await new Promise(resolve => setTimeout(resolve, 200))
    
    console.log(`[API] Getting status for session: ${sessionId}`)
    
    // First attempt to find the session
    let session = await Session.findOne({ id: sessionId })
    
    // If not found on first try and it looks like a new session (contains current timestamp)
    if (!session && sessionId.includes(`_${Date.now().toString().substring(0, 8)}`)) {
      console.log(`[API] New session not found, retrying after delay: ${sessionId}`)
      // For new sessions, add extra delay and retry
      await new Promise(resolve => setTimeout(resolve, 500))
      session = await Session.findOne({ id: sessionId })
    }

    if (!session) {
      console.log(`[API] Session not found: ${sessionId}`)
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    console.log(`[API] Session found with status: ${session.status}`)
    return NextResponse.json({
      sessionId: session.id,
      status: session.status,
      updatedAt: session.updatedAt
    })
  } catch (error) {
    console.error("Error retrieving session status:", error)
    return NextResponse.json({ error: "Failed to retrieve session status" }, { status: 500 })
  }
}

/**
 * API endpoint to update only the status of a session
 * PATCH /api/sessions/status/:id
 */
export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()

    const params = await context.params
    const sessionId = params.id
    const body = await request.json()

    // Only allow status updates through this endpoint
    if (!body.status || !["in_progress", "completed"].includes(body.status)) {
      return NextResponse.json({ 
        error: "Invalid status. Must be either 'in_progress' or 'completed'" 
      }, { status: 400 })
    }

    const session = await Session.findOne({ id: sessionId })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    // Prepare update object
    const updateData: {
      status: string;
      updatedAt: Date;
      completedAt?: Date;
    } = {
      status: body.status,
      updatedAt: new Date()
    };
    
    // If completing the session, add completedAt timestamp
    if (body.status === 'completed') {
      updateData.completedAt = new Date();
    }

    // Update only the session status
    const updatedSession = await Session.findOneAndUpdate(
      { id: sessionId },
      updateData,
      { new: true }
    )

    return NextResponse.json({
      success: true,
      sessionId: updatedSession.id,
      status: updatedSession.status,
      updatedAt: updatedSession.updatedAt
    })
  } catch (error) {
    console.error("Error updating session status:", error)
    return NextResponse.json({ error: "Failed to update session status" }, { status: 500 })
  }
} 