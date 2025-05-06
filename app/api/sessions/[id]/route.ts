import { NextResponse } from "next/server"
import connectToDatabase from "../../../../lib/mongodb"
import Session from "../../../../models/Session"

export async function GET(
  request: Request, 
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()
    
    const params = await context.params
    const sessionId = params.id
    const session = await Session.findOne({ id: sessionId })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    return NextResponse.json(session)
  } catch (error) {
    console.error("Error retrieving session:", error)
    return NextResponse.json({ error: "Failed to retrieve session" }, { status: 500 })
  }
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()
    
    const params = await context.params
    const sessionId = params.id
    const body = await request.json()

    const session = await Session.findOne({ id: sessionId })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    // Update session
    const updateData = { ...body };
    
    // Update progress based on currentQuestionIndex if necessary
    if (body.currentQuestionIndex !== undefined && body.qaPairs) {
      const total = body.qaPairs.length;
      updateData.progress = {
        current: Math.min(body.currentQuestionIndex, total),
        total
      };
    }
    
    const updatedSession = await Session.findOneAndUpdate(
      { id: sessionId },
      { 
        ...updateData,
        updatedAt: new Date()
      },
      { new: true }
    )

    return NextResponse.json({
      success: true,
      session: updatedSession
    })
  } catch (error) {
    console.error("Error updating session:", error)
    return NextResponse.json({ error: "Failed to update session" }, { status: 500 })
  }
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()
    
    const params = await context.params
    const sessionId = params.id
    const body = await request.json()

    // Find the session first to verify it exists
    const session = await Session.findOne({ id: sessionId })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    const updateData = { ...body };
    
    // If completing the session, add completedAt timestamp
    if (updateData.status === 'completed') {
      updateData.completedAt = new Date();
    }
    
    // Update session with partial data
    const updatedSession = await Session.findOneAndUpdate(
      { id: sessionId },
      { 
        ...updateData,
        updatedAt: new Date()
      },
      { new: true }
    )

    return NextResponse.json({
      success: true,
      session: updatedSession
    })
  } catch (error) {
    console.error("Error patching session:", error)
    return NextResponse.json({ error: "Failed to patch session" }, { status: 500 })
  }
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    await connectToDatabase()
    
    const params = await context.params
    const sessionId = params.id
    const session = await Session.findOne({ id: sessionId })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    await Session.deleteOne({ id: sessionId })

    return NextResponse.json({
      success: true,
      message: "Session deleted"
    })
  } catch (error) {
    console.error("Error deleting session:", error)
    return NextResponse.json({ error: "Failed to delete session" }, { status: 500 })
  }
}
