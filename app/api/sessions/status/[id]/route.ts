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
    
    const session = await Session.findOne({ id: sessionId }).select('status')

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    return NextResponse.json({ status: session.status })
  } catch (error) {
    console.error("Error checking session status:", error)
    return NextResponse.json({ error: "Failed to check session status" }, { status: 500 })
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

    // Validate that the status is valid
    if (!body.status || !['in_progress', 'completed'].includes(body.status)) {
      return NextResponse.json({ 
        error: "Invalid status. Must be 'in_progress' or 'completed'" 
      }, { status: 400 })
    }

    const session = await Session.findOne({ id: sessionId })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    // Add completedAt timestamp if setting status to completed
    const updateData: any = { 
      status: body.status,
      updatedAt: new Date()
    }
    
    if (body.status === 'completed') {
      updateData.completedAt = new Date()
    }

    const updatedSession = await Session.findOneAndUpdate(
      { id: sessionId },
      updateData,
      { new: true }
    )

    return NextResponse.json({
      success: true,
      status: updatedSession.status
    })
  } catch (error) {
    console.error("Error updating session status:", error)
    return NextResponse.json({ error: "Failed to update session status" }, { status: 500 })
  }
} 