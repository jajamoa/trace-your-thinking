import { useState } from 'react';
import { useStore } from '../../lib/store';

/**
 * 用于处理用户回答并获取因果图的hook
 */
export function useProcessAnswer() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 从store获取会话数据
  const sessionId = useStore(state => state.sessionId);
  const prolificId = useStore(state => state.prolificId);
  const addNewQuestion = useStore(state => state.addNewQuestion);
  const markQuestionAsAnswered = useStore(state => state.markQuestionAsAnswered);
  const moveToNextQuestion = useStore(state => state.moveToNextQuestion);
  
  /**
   * 提交回答并处理后端响应
   * @param qaPair 问答对
   * @returns 处理结果
   */
  const processAnswer = async (qaPair: { id: string; question: string; shortText?: string; answer: string }) => {
    if (!sessionId || !prolificId) {
      setError('缺少会话ID或用户ID');
      return null;
    }
    
    if (!qaPair || !qaPair.id || !qaPair.answer) {
      setError('问答数据不完整');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // 调用处理回答API
      const response = await fetch('/api/process-answer', {
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
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '处理回答时出错');
      }
      
      const data = await response.json();
      
      if (data.success) {
        // 如果有后续问题，添加到问题列表
        if (data.data.followUpQuestions && data.data.followUpQuestions.length > 0) {
          // 添加后续问题到store，一次添加一个问题
          data.data.followUpQuestions.forEach((question: any) => {
            addNewQuestion({
              question: question.question,
              shortText: question.shortText || '后续问题'
            });
          });
        }
        
        // 将当前问题标记为已回答
        markQuestionAsAnswered(qaPair.id);
        
        // 移动到下一个问题
        moveToNextQuestion();
        
        return data.data;
      } else {
        throw new Error(data.error || '未知错误');
      }
    } catch (err: any) {
      setError(err.message || '处理回答时出错');
      return null;
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * 获取因果图
   * @param options 查询选项
   * @returns 因果图列表
   */
  const getCausalGraphs = async (options?: { 
    sessionId?: string;
    qaPairId?: string;
  }) => {
    if (!prolificId && !options?.sessionId) {
      setError('缺少用户ID或会话ID');
      return [];
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // 构建查询参数
      const params = new URLSearchParams();
      
      if (prolificId) {
        params.append('prolificId', prolificId);
      }
      
      if (options?.sessionId) {
        params.append('sessionId', options.sessionId);
      } else if (sessionId) {
        params.append('sessionId', sessionId);
      }
      
      if (options?.qaPairId) {
        params.append('qaPairId', options.qaPairId);
      }
      
      // 获取因果图
      const response = await fetch(`/api/causal-graphs?${params.toString()}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '获取因果图时出错');
      }
      
      const data = await response.json();
      
      if (data.success) {
        return data.causalGraphs;
      } else {
        throw new Error(data.error || '未知错误');
      }
    } catch (err: any) {
      setError(err.message || '获取因果图时出错');
      return [];
    } finally {
      setLoading(false);
    }
  };
  
  return {
    processAnswer,
    getCausalGraphs,
    loading,
    error,
  };
} 