"use client"

import { QAPair } from './store';

/**
 * Python backend API service for processing answers and generating causal graphs
 */
export class PythonAPIService {
  /**
   * Process an answer through the Python backend via our Next.js API proxy
   * Gets causal graph and follow-up questions
   */
  static async processAnswer(
    sessionId: string, 
    prolificId: string, 
    qaPair: QAPair,
    qaPairs: QAPair[] = [],
    currentQuestionIndex: number = 0,
    existingCausalGraph: any = null
  ): Promise<{
    success: boolean;
    followUpQuestions?: QAPair[];
    causalGraph?: any;
    error?: string;
  }> {
    try {
      // Log the request
      console.log(`Sending QA pair to process-answer API:`, { 
        sessionId, 
        prolificId, 
        questionId: qaPair.id,
        totalQaPairs: qaPairs.length,
        currentQuestionIndex
      });

      // Ensure the qaPair is well-formed
      const validQAPair = {
        id: qaPair.id,
        question: qaPair.question || '',
        shortText: qaPair.shortText || '',
        answer: qaPair.answer || '',
        category: qaPair.category || 'research'
      };

      // Ensure all qaPairs have the proper format
      const validQAPairs = qaPairs.map(qa => {
        return {
          id: qa.id || `qa_${Math.random().toString(36).substring(2, 9)}`,
          question: qa.question || '',
          shortText: qa.shortText || '',
          answer: qa.answer || '',
          category: qa.category || 'research'
        };
      });

      // Make API call to Next.js API route (not directly to Python backend)
      const response = await fetch('/api/process-answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          prolificId,
          qaPair: validQAPair,
          qaPairs: validQAPairs,
          currentQuestionIndex,
          existingCausalGraph
        }),
      });

      if (!response.ok) {
        // Handle HTTP error responses
        const errorText = await response.text();
        console.error(`Error from process-answer API: ${response.status} - ${errorText}`);
        return { 
          success: false, 
          error: `API error: ${response.status} - ${errorText}`
        };
      }

      // Parse response
      const data = await response.json();
      
      // Log response summary (without full content for brevity)
      console.log(`Received response from process-answer API:`, {
        success: data.success,
        hasFollowUpQuestions: Boolean(data.data?.followUpQuestions?.length),
        hasCausalGraph: Boolean(data.data?.causalGraph)
      });

      // Check response structure
      if (!data.success) {
        return { 
          success: false, 
          error: data.error || 'Unknown API error' 
        };
      }

      return {
        success: true,
        followUpQuestions: data.data.followUpQuestions || [],
        causalGraph: data.data.causalGraph
      };
    } catch (error) {
      console.error('Error processing answer:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error during API call'
      };
    }
  }

  /**
   * Get the most recent causal graph for a QA pair
   */
  static async getCausalGraph(
    sessionId: string, 
    qaPairId: string
  ): Promise<any | null> {
    try {
      const response = await fetch(`/api/causal-graphs?sessionId=${sessionId}&qaPairId=${qaPairId}`);
      
      if (!response.ok) {
        console.error(`Error fetching causal graph: ${response.status}`);
        return null;
      }
      
      const data = await response.json();
      
      // Return the first (most recent) causal graph if available
      if (data.success && data.causalGraphs && data.causalGraphs.length > 0) {
        return data.causalGraphs[0].graphData;
      }
      
      return null;
    } catch (error) {
      console.error('Error fetching causal graph:', error);
      return null;
    }
  }
} 