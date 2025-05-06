import { NextResponse } from "next/server";
import connectToDatabase from "../../../../lib/mongodb";
import Session, { IQAPair } from "../../../../models/Session";

export async function GET(request: Request) {
  try {
    await connectToDatabase();
    
    const { searchParams } = new URL(request.url);
    const sessionId = searchParams.get("id");
    const format = searchParams.get("format") || "json";

    if (!sessionId) {
      return NextResponse.json({ error: "Session ID is required" }, { status: 400 });
    }

    const session = await Session.findOne({ id: sessionId });
    
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 });
    }
    
    if (format === "csv") {
      // Export as CSV format
      let csv = "Question,Answer\n";
      session.qaPairs.forEach((qa: IQAPair) => {
        csv += `"${qa.question.replace(/"/g, '""')}","${qa.answer.replace(/"/g, '""')}"\n`;
      });
      
      return new NextResponse(csv, {
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': `attachment; filename="session-${sessionId}.csv"`
        }
      });
    }
    
    // Default export as JSON
    return NextResponse.json(session);
  } catch (error) {
    console.error("Error exporting session:", error);
    return NextResponse.json({ error: "Failed to export session" }, { status: 500 });
  }
} 