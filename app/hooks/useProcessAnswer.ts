import { useState } from 'react';
import { useStore } from '../../lib/store';

/**
 * Hook for processing user answers and retrieving causal graphs
 */
export function useProcessAnswer() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Get session data from store
  const sessionId = useStore(state => state.sessionId);
  const prolificId = useStore(state => state.prolificId);
  const addNewQuestion = useStore(state => state.addNewQuestion);
  const markQuestionAsAnswered = useStore(state => state.markQuestionAsAnswered);
  const moveToNextQuestion = useStore(state => state.moveToNextQuestion);
  
  /**
   * Submit answer and process backend response
   * @param qaPair Question-answer pair
   * @returns Processing result
   */
  const processAnswer = async (qaPair: { id: string; question: string; shortText?: string; answer: string }) => {
    if (!sessionId || !prolificId) {
      setError('Missing session ID or user ID');
      return null;
    }
    
    if (!qaPair || !qaPair.id || !qaPair.answer) {
      setError('Incomplete QA data');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Call process answer API
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
        throw new Error(errorData.error || 'Error processing answer');
      }
      
      const data = await response.json();
      
      if (data.success) {
        // If there are follow-up questions, add them to the question list
        if (data.data.followUpQuestions && data.data.followUpQuestions.length > 0) {
          // Add follow-up questions to store, one question at a time
          data.data.followUpQuestions.forEach((question: any) => {
            addNewQuestion({
              question: question.question,
              shortText: question.shortText || 'Follow-up question'
            });
          });
        }
        
        // Mark current question as answered
        markQuestionAsAnswered(qaPair.id);
        
        // Move to the next question
        moveToNextQuestion();
        
        return data.data;
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    } catch (err: any) {
      setError(err.message || 'Error processing answer');
      return null;
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Get causal graphs
   * @param options Query options
   * @returns List of causal graphs
   */
  const getCausalGraphs = async (options?: { 
    sessionId?: string;
    qaPairId?: string;
  }) => {
    if (!prolificId && !options?.sessionId) {
      setError('Missing user ID or session ID');
      return [];
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Build query parameters
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
      
      // Get causal graphs
      const response = await fetch(`/api/causal-graphs?${params.toString()}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Error fetching causal graphs');
      }
      
      const data = await response.json();
      
      if (data.success) {
        return data.causalGraphs;
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    } catch (err: any) {
      setError(err.message || 'Error fetching causal graphs');
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