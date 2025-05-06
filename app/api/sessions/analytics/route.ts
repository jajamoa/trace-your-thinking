import { NextResponse } from "next/server";
import connectToDatabase from "../../../../lib/mongodb";
import Session, { ISession } from "../../../../models/Session";

export async function GET(request: Request) {
  try {
    await connectToDatabase();
    
    // Get basic statistics
    const totalSessions = await Session.countDocuments();
    const completedSessions = await Session.countDocuments({ status: 'completed' });
    const inProgressSessions = await Session.countDocuments({ status: 'in_progress' });
    const reviewedSessions = await Session.countDocuments({ status: 'reviewed' });
    
    // Get average number of Q&A pairs
    const allSessions = await Session.find();
    const averageQAPairs = allSessions.reduce((sum: number, session: ISession) => sum + session.qaPairs.length, 0) / (allSessions.length || 1);
    
    // Get recent sessions
    const recentSessions = await Session.find()
      .sort({ createdAt: -1 })
      .limit(10)
      .select('id prolificId createdAt status');
    
    // Get top prolific IDs by session count
    const prolificStats = await Session.aggregate([
      { $group: { _id: "$prolificId", count: { $sum: 1 } } },
      { $sort: { count: -1 } },
      { $limit: 5 }
    ]);
    
    return NextResponse.json({
      totalSessions,
      completedSessions,
      inProgressSessions,
      reviewedSessions,
      completionRate: totalSessions ? (completedSessions / totalSessions) * 100 : 0,
      averageQAPairs,
      recentSessions,
      prolificStats
    });
  } catch (error) {
    console.error("Error getting analytics data:", error);
    return NextResponse.json({ error: "Failed to get analytics data" }, { status: 500 });
  }
} 