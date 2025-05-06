// Example frontend integration code
// This file demonstrates how to integrate the backend API with the existing store.ts in a React/Next.js app

import { useStore } from '../lib/store';
import { MongoClient } from 'mongodb';

// MongoDB connection details - in a real app, use environment variables
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const DB_NAME = 'thinking_trace_db';

/**
 * Save causal graph to MongoDB
 * This function would be called from an API route in Next.js
 */
export async function saveToDB(data) {
  const client = new MongoClient(MONGODB_URI);
  
  try {
    await client.connect();
    const db = client.db(DB_NAME);
    
    // Extract data
    const { sessionId, prolificId, qaPair, causalGraph, timestamp } = data;
    
    // Save session info
    await db.collection('sessions').updateOne(
      { sessionId },
      { 
        $set: { 
          prolificId,
          lastUpdated: new Date(timestamp * 1000)
        }
      },
      { upsert: true }
    );
    
    // Save QA pair
    await db.collection('answers').updateOne(
      {
        sessionId,
        prolificId,
        qaPairId: qaPair.id
      },
      {
        $set: {
          question: qaPair.question,
          shortText: qaPair.shortText,
          answer: qaPair.answer,
          timestamp: new Date(timestamp * 1000)
        }
      },
      { upsert: true }
    );
    
    // Save causal graph
    await db.collection('causal_graphs').insertOne({
      sessionId,
      prolificId,
      qaPairId: qaPair.id,
      graphData: causalGraph,
      timestamp: new Date(timestamp * 1000)
    });
    
    return { success: true };
  } catch (error) {
    console.error('Database error:', error);
    return { success: false, error: error.message };
  } finally {
    await client.close();
  }
}

/**
 * Submit user answer and get follow-up questions
 * Call this function when a user submits an answer
 */
export async function submitAnswerAndGetFollowUps(qaPair) {
  try {
    // Get session ID and Prolific ID from store
    const sessionId = useStore.getState().sessionId;
    const prolificId = useStore.getState().prolificId;
    
    if (!sessionId || !prolificId) {
      console.error('Missing sessionId or prolificId');
      return;
    }
    
    // Call Python backend API for processing
    const response = await fetch('http://localhost:5000/api/process_answer', {
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
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.success) {
      // Save data to MongoDB via Next.js API
      const saveResponse = await fetch('/api/save-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!saveResponse.ok) {
        console.error('Error saving data to database');
      }
      
      // Process follow-up questions
      handleFollowUpQuestions(data.followUpQuestions);
      
      // Process causal graph - this is just an example, actual implementation depends on how the frontend displays graphs
      if (data.causalGraph) {
        console.log('Received causal graph:', data.causalGraph);
        // You can update state or store the causal graph in context here
      }
      
      // Mark current question as answered
      useStore.getState().markQuestionAsAnswered(qaPair.id);
      
      // Move to the next question
      useStore.getState().moveToNextQuestion();
      
      return true;
    }
    
    return false;
  } catch (error) {
    console.error('Error submitting answer:', error);
    return false;
  }
}

/**
 * Process follow-up questions received from the backend
 */
function handleFollowUpQuestions(followUpQuestions) {
  if (!followUpQuestions || !Array.isArray(followUpQuestions) || followUpQuestions.length === 0) {
    return;
  }
  
  console.log(`Adding ${followUpQuestions.length} follow-up questions`);
  
  // Use the addNewQuestion method from the store to add each follow-up question
  followUpQuestions.forEach(question => {
    const questionId = useStore.getState().addNewQuestion({
      question: question.question,
      shortText: question.shortText
    });
    
    console.log(`Added new question: ${questionId}`);
  });
  
  // Recalculate progress
  useStore.getState().recalculateProgress();
}

/**
 * Fetch all causal graphs for a user
 */
export async function fetchUserCausalGraphs(prolificId) {
  if (!prolificId) {
    const prolificId = useStore.getState().prolificId;
    if (!prolificId) {
      console.error('Missing prolificId');
      return [];
    }
  }
  
  try {
    // Fetch from our Next.js API instead of Python backend
    const response = await fetch(`/api/causal-graphs?prolificId=${prolificId}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    return data.causalGraphs || [];
  } catch (error) {
    console.error('Error fetching causal graphs:', error);
    return [];
  }
}

/**
 * Example component that can be triggered automatically after a question is answered
 */
export function AnswerSubmitHandler({ qaPair, onSuccess }) {
  const handleSubmit = async () => {
    const success = await submitAnswerAndGetFollowUps(qaPair);
    if (success && onSuccess) {
      onSuccess();
    }
  };
  
  return (
    <button onClick={handleSubmit}>
      Submit answer and get follow-up questions
    </button>
  );
} 