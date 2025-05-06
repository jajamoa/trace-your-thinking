import { NextResponse } from "next/server";
import connectToDatabase from "../../../lib/mongodb";
import Session from "../../../models/Session";
import CausalGraph from "../../../models/CausalGraph";

// 获取Python后端URL
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:5000';

/**
 * 处理答案接口
 * 将用户回答发送至Python后端进行处理，获取因果图和后续问题
 */
export async function POST(request: Request) {
  try {
    await connectToDatabase();
    
    const body = await request.json();
    const { sessionId, prolificId, qaPair } = body;

    if (!sessionId || !prolificId || !qaPair) {
      return NextResponse.json({ error: "缺少必要参数" }, { status: 400 });
    }

    // 查找会话以确保存在
    const session = await Session.findOne({ id: sessionId });
    
    if (!session) {
      return NextResponse.json({ error: "会话不存在" }, { status: 404 });
    }

    // 调用Python后端API进行处理
    const pythonResponse = await fetch(`${PYTHON_BACKEND_URL}/api/process_answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sessionId,
        prolificId,
        qaPair,
      }),
    });

    if (!pythonResponse.ok) {
      const errorData = await pythonResponse.json();
      console.error("Python后端处理失败:", errorData);
      return NextResponse.json(
        { error: "处理回答时出错", details: errorData },
        { status: pythonResponse.status }
      );
    }

    const data = await pythonResponse.json();

    // 保存因果图到数据库
    if (data.causalGraph) {
      const newCausalGraph = new CausalGraph({
        sessionId,
        prolificId,
        qaPairId: qaPair.id,
        graphData: data.causalGraph,
        timestamp: new Date(data.timestamp * 1000 || Date.now())
      });

      await newCausalGraph.save();
    }

    // 更新会话中的QA对
    if (qaPair.id) {
      // 在会话中找到并更新当前QA对的答案
      const updatedSession = await Session.findOneAndUpdate(
        { id: sessionId, "qaPairs.id": qaPair.id },
        { 
          $set: { 
            "qaPairs.$.answer": qaPair.answer,
            updatedAt: new Date()
          } 
        },
        { new: true }
      );

      // 如果返回了后续问题，将它们添加到会话中
      if (data.followUpQuestions && data.followUpQuestions.length > 0) {
        // 找出当前问题的索引
        const currentQuestionIndex = updatedSession.qaPairs.findIndex(
          (q: any) => q.id === qaPair.id
        );
        
        // 确定后续问题的插入位置
        const insertPosition = currentQuestionIndex + 1;
        
        // 准备后续问题，确保它们不会与现有问题ID冲突
        const followUpQuestions = data.followUpQuestions.map((q: any, index: number) => ({
          ...q,
          id: q.id || `followup_${qaPair.id}_${index + 1}`
        }));
        
        // 将后续问题插入到会话中
        const newQaPairs = [
          ...updatedSession.qaPairs.slice(0, insertPosition),
          ...followUpQuestions,
          ...updatedSession.qaPairs.slice(insertPosition)
        ];
        
        // 更新会话中的问题列表和进度
        await Session.findOneAndUpdate(
          { id: sessionId },
          { 
            $set: { 
              qaPairs: newQaPairs,
              progress: {
                current: updatedSession.progress.current,
                total: newQaPairs.length
              },
              updatedAt: new Date()
            } 
          },
          { new: true }
        );
      }
    }

    return NextResponse.json({
      success: true,
      data: data
    });
  } catch (error) {
    console.error("处理回答时出错:", error);
    return NextResponse.json({ error: "处理回答失败" }, { status: 500 });
  }
} 