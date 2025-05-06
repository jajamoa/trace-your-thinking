import { NextResponse } from "next/server";
import connectToDatabase from "../../../lib/mongodb";
import CausalGraph from "../../../models/CausalGraph";

/**
 * 获取因果图API
 * 根据会话ID或用户ID获取相关的因果图
 */
export async function GET(request: Request) {
  try {
    await connectToDatabase();
    
    const { searchParams } = new URL(request.url);
    const sessionId = searchParams.get("sessionId");
    const prolificId = searchParams.get("prolificId");
    const qaPairId = searchParams.get("qaPairId");

    // 至少需要提供sessionId或prolificId之一
    if (!sessionId && !prolificId) {
      return NextResponse.json({ error: "必须提供sessionId或prolificId参数" }, { status: 400 });
    }
    
    // 构建查询条件
    const query: any = {};
    
    if (sessionId) {
      query.sessionId = sessionId;
    }
    
    if (prolificId) {
      query.prolificId = prolificId;
    }
    
    if (qaPairId) {
      query.qaPairId = qaPairId;
    }
    
    // 查询数据库获取因果图
    const causalGraphs = await CausalGraph.find(query).sort({ timestamp: -1 });
    
    return NextResponse.json({
      success: true,
      causalGraphs
    });
  } catch (error) {
    console.error("获取因果图时出错:", error);
    return NextResponse.json({ error: "获取因果图失败" }, { status: 500 });
  }
} 