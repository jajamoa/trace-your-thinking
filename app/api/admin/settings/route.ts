import { NextResponse } from "next/server";
import connectToDatabase from "../../../../lib/mongodb";
import InterviewSettings from "../../../../models/InterviewSettings";

/**
 * Get interview settings
 */
export async function GET() {
  try {
    await connectToDatabase();
    
    // Find settings or create default if not exists
    let settings = await InterviewSettings.findOne();
    
    if (!settings) {
      settings = await InterviewSettings.create({
        defaultTopic: "policy",
        updatedAt: new Date()
      });
    }
    
    return NextResponse.json({
      success: true,
      settings
    });
  } catch (error) {
    console.error("Error fetching interview settings:", error);
    return NextResponse.json({ error: "Failed to fetch interview settings" }, { status: 500 });
  }
}

/**
 * Update interview settings
 */
export async function PUT(request: Request) {
  try {
    await connectToDatabase();
    
    const data = await request.json();
    const { defaultTopic } = data;
    
    if (!defaultTopic) {
      return NextResponse.json(
        { error: "Missing required field: defaultTopic" }, 
        { status: 400 }
      );
    }
    
    // Find settings or create if not exists
    let settings = await InterviewSettings.findOne();
    
    if (settings) {
      // Update existing settings
      settings.defaultTopic = defaultTopic;
      settings.updatedAt = new Date();
      await settings.save();
    } else {
      // Create new settings
      settings = await InterviewSettings.create({
        defaultTopic,
        updatedAt: new Date()
      });
    }
    
    return NextResponse.json({
      success: true,
      settings
    });
  } catch (error) {
    console.error("Error updating interview settings:", error);
    return NextResponse.json({ error: "Failed to update interview settings" }, { status: 500 });
  }
} 