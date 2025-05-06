"use client"

import { useStore } from './store'
import { v4 as uuidv4 } from 'uuid'

/**
 * Synchronization service for handling data sync between local state and database
 */
export class SyncService {
  /**
   * Synchronize the local store state with the remote database
   * This is a robust implementation that handles various edge cases
   */
  static async syncSession(retryCount = 0): Promise<{ success: boolean; error?: string; sessionId?: string }> {
    const state = useStore.getState()
    const maxRetries = 2 // Maximum number of retry attempts
    
    try {
      // If we have a session ID, try to update existing session
      if (state.sessionId) {
        // First check if the session exists
        console.log(`Checking if session exists: ${state.sessionId}`)
        const checkResponse = await fetch(`/api/sessions/${state.sessionId}`, {
          method: "GET",
        })
        
        // If session exists, update it
        if (checkResponse.ok) {
          // Check if session is completed - don't update completed sessions
          const sessionData = await checkResponse.json()
          if (sessionData.status === "completed") {
            return { success: true, sessionId: state.sessionId }
          }
          
          // Update existing session
          console.log(`Updating existing session: ${state.sessionId}`)
          const updateResponse = await fetch(`/api/sessions/${state.sessionId}`, {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              prolificId: state.prolificId,
              qaPairs: state.qaPairs,
              pendingQuestions: state.pendingQuestions,
              messages: state.messages,
              status: state.status,
              progress: state.progress
            }),
          })
          
          if (updateResponse.ok) {
            return { success: true, sessionId: state.sessionId }
          }
          
          console.log(`Failed to update session: ${state.sessionId}`)
        }
        
        // If session doesn't exist or update failed, clear sessionId and create a new one
        console.log("Session not found or update failed, will create a new one")
        useStore.setState({ sessionId: null })
      }
      
      // Only proceed if we have a prolificId
      if (!state.prolificId) {
        return { success: false, error: "No prolificId available for creating a session" }
      }
      
      // Create new session if no session ID or previous session not found
      console.log("Creating new session...")
      const createResponse = await fetch("/api/sessions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prolificId: state.prolificId,
          qaPairs: state.qaPairs,
          pendingQuestions: state.pendingQuestions,
          messages: state.messages,
          questions: state.questions,
          status: state.status,
          progress: state.progress
        }),
      })
      
      if (createResponse.ok) {
        const data = await createResponse.json()
        if (data.sessionId) {
          // Update sessionId in store
          console.log(`New session created successfully: ${data.sessionId}`)
          useStore.setState({ sessionId: data.sessionId })
          return { success: true, sessionId: data.sessionId }
        }
      }
      
      // If we reach here, session creation failed
      const errorStatus = createResponse.status
      const errorBody = await createResponse.text().catch(() => "Could not read response body");
      const errorMessage = `Failed to create session. Status: ${errorStatus}, Body: ${errorBody}`;
      console.error(errorMessage);
      
      // Implement retry logic for failed creation
      if (retryCount < maxRetries) {
        console.log(`Retrying session creation (attempt ${retryCount + 1} of ${maxRetries})...`);
        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 1000));
        return this.syncSession(retryCount + 1);
      }
      
      throw new Error(errorMessage);
    } catch (error) {
      console.error("Sync error:", error)
      // Implement retry logic for exceptions
      if (retryCount < maxRetries) {
        console.log(`Retrying after error (attempt ${retryCount + 1} of ${maxRetries})...`);
        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 1000));
        return this.syncSession(retryCount + 1);
      }
      
      return { 
        success: false, 
        error: error instanceof Error ? error.message : "Unknown sync error" 
      }
    }
  }

  /**
   * Initialize a new session with guiding questions from the database
   * and display the first question message
   */
  static async initializeSessionWithGuidingQuestions(): Promise<boolean> {
    try {
      // Fetch active guiding questions
      const response = await fetch("/api/guiding-questions?active=true")
      
      if (!response.ok) {
        console.error("Failed to fetch guiding questions:", response.statusText)
        throw new Error("Failed to fetch guiding questions")
      }
      
      const data = await response.json()
      const guidingQuestions = data.questions || []
      
      // Get store state and functions
      const store = useStore.getState()
      const addMessage = store.addMessage
      
      if (guidingQuestions.length === 0) {
        console.warn("No active guiding questions found, using fallback question")
        
        // Use a fallback question if no guiding questions are available
        const fallbackQuestion = {
          id: `gq_fallback_${Date.now()}`,
          text: "Could you describe your current research focus and how it relates to the broader field?",
          shortText: "Research focus"
        }
        
        const questions = [fallbackQuestion]
        const qaPairs = [{
          id: fallbackQuestion.id,
          question: fallbackQuestion.text,
          answer: ""
        }]
        
        // Update store with the fallback question
        useStore.setState({
          questions,
          pendingQuestions: [...questions],
          qaPairs,
          progress: {
            current: 0,
            total: 1
          }
        })
        
        // Display the fallback question
        if (addMessage) {
          addMessage({
            id: uuidv4(),
            role: "bot",
            text: fallbackQuestion.text,
            loading: false
          })
        }
        
        return true
      }
      
      // Transform guiding questions into the Question format and QAPair format
      const questions = guidingQuestions.map((gq: any) => ({
        id: gq.id,
        text: gq.text,
        shortText: gq.shortText
      }))
      
      const qaPairs = questions.map((q: any) => ({
        id: q.id,
        question: q.text,
        answer: ""
      }))
      
      // Update store with the guiding questions data
      useStore.setState({
        questions,
        pendingQuestions: [...questions], // Create a copy
        qaPairs,
        progress: {
          current: 0,
          total: questions.length
        }
      })
      
      // Display the first question as a message
      if (questions.length > 0 && addMessage) {
        console.log("Adding first question message:", questions[0].text)
        addMessage({
          id: uuidv4(), // Use UUID rather than timestamp-based ID
          role: "bot",
          text: questions[0].text,
          loading: false
        })
      }
      
      return true
    } catch (error) {
      console.error("Error initializing session with guiding questions:", error)
      
      // Use fallback questions on error
      const store = useStore.getState()
      const firstQuestion = {
        id: "q1",
        text: "Could you describe your current research focus and how it relates to the broader field?",
        shortText: "Research focus",
      }
      
      useStore.setState({
        questions: [firstQuestion],
        pendingQuestions: [firstQuestion],
        qaPairs: [{
          id: firstQuestion.id,
          question: firstQuestion.text,
          answer: ""
        }],
        progress: { current: 0, total: 1 }
      })
      
      // Display fallback question
      if (store.addMessage) {
        store.addMessage({
          id: uuidv4(),
          role: "bot",
          text: firstQuestion.text,
          loading: false
        })
      }
      
      return true
    }
  }

  /**
   * Create a new session with prolific ID and load the first question
   * Returns the session ID if successful
   */
  static async createNewSession(prolificId: string): Promise<{success: boolean; sessionId?: string}> {
    try {
      if (!prolificId) {
        throw new Error("Prolific ID is required")
      }
      
      const state = useStore.getState()
      
      // Clear previous session data but keep prolificId if it's already set
      useStore.setState({
        messages: [],
        qaPairs: [],
        pendingQuestions: [],
        questions: [],
        sessionId: null
      })
      
      // Only set the prolificId if it's not already set
      // This avoids race conditions with SessionCheck component
      if (!state.prolificId) {
        console.log("Setting prolificID in SyncService:", prolificId)
        useStore.setState({ prolificId })
      }
      
      // Initialize with guiding questions
      const questionsLoaded = await this.initializeSessionWithGuidingQuestions()
      
      if (!questionsLoaded) {
        console.error("Failed to load guiding questions")
        return { success: false }
      }
      
      // Create session in database and wait for it to complete
      const syncResult = await this.syncSession()
      
      // Only return success if we got a valid sessionId
      if (syncResult.success && syncResult.sessionId) {
        console.log("Session successfully created with ID:", syncResult.sessionId)
        
        // Double-check that QA pairs are loaded
        const updatedState = useStore.getState()
        if (updatedState.qaPairs.length === 0) {
          console.error("QA pairs not loaded properly")
          return { success: false }
        }
        
        // Verify the session actually exists in the database by trying to fetch it
        console.log("Verifying session exists in database...")
        try {
          const verifyResponse = await fetch(`/api/sessions/${syncResult.sessionId}`, {
            method: "GET",
          })
          
          if (!verifyResponse.ok) {
            console.error(`Session verification failed: ${verifyResponse.status}`)
            return { success: false }
          }
          
          // Wait a moment to ensure any replication delay has passed
          await new Promise(resolve => setTimeout(resolve, 500))
          
          console.log("Session verified and exists in database")
        } catch (error) {
          console.error("Error verifying session:", error)
          return { success: false }
        }
        
        return { 
          success: true, 
          sessionId: syncResult.sessionId 
        }
      }
      
      console.error("Failed to get valid session ID after creation")
      return { success: false }
    } catch (error) {
      console.error("Error creating new session:", error)
      return { success: false }
    }
  }

  /**
   * Display current QA pairs as messages
   * This ensures UI state is derived from data state
   */
  static displayQAPairsAsMessages(): void {
    try {
      const state = useStore.getState()
      const { qaPairs, messages, addMessage } = state
      
      // Clear existing messages
      useStore.setState({ messages: [] })
      
      // Re-populate messages from QA pairs
      qaPairs.forEach((pair) => {
        // Add question message
        addMessage({
          id: uuidv4(),
          role: "bot",
          text: pair.question,
          loading: false
        })
        
        // Add answer message if it exists
        if (pair.answer) {
          addMessage({
            id: uuidv4(),
            role: "user",
            text: pair.answer,
            loading: false
          })
        }
      })
      
      // Recalculate progress after rebuilding messages
      console.log("Recalculating progress after rebuilding messages in SyncService")
      if (typeof state.recalculateProgress === 'function') {
        state.recalculateProgress()
      }
    } catch (error) {
      console.error("Error displaying QA pairs as messages:", error)
    }
  }

  /**
   * Get session status from the server
   */
  static async checkSessionStatus(sessionId: string): Promise<string | null> {
    try {
      if (!sessionId) return null
      
      const response = await fetch(`/api/sessions/status/${sessionId}`, {
        method: "GET",
      })
      
      if (response.ok) {
        const data = await response.json()
        return data.status || null
      }
      
      return null
    } catch (error) {
      console.error("Failed to check session status:", error)
      return null
    }
  }

  /**
   * Fetch full session data from the server to sync local state
   * This is important to ensure local pendingQuestions and total questions 
   * are aligned with server data
   */
  static async fetchFullSessionData(sessionId: string): Promise<boolean> {
    try {
      if (!sessionId) {
        console.error("Cannot fetch session data: No sessionId provided")
        return false
      }
      
      console.log(`Fetching full session data for: ${sessionId}`)
      
      const response = await fetch(`/api/sessions/${sessionId}`, {
        method: "GET",
      })
      
      if (!response.ok) {
        console.error(`Failed to fetch session data: ${response.status}`)
        return false
      }
      
      const sessionData = await response.json()
      
      // Log the retrieved data for debugging
      console.log("Retrieved session data from server:", {
        questionsCount: sessionData.questions?.length || 0,
        pendingQuestionsCount: sessionData.pendingQuestions?.length || 0,
        qaPairsCount: sessionData.qaPairs?.length || 0,
        status: sessionData.status
      })
      
      // Update local state with server data
      const state = useStore.getState()
      
      // Only update if we have valid data
      if (sessionData.questions && sessionData.questions.length > 0) {
        // Compare server and local data
        console.log("Comparing server and local data:")
        console.log(`- Server questions: ${sessionData.questions.length}, Local: ${state.questions.length}`)
        console.log(`- Server pending: ${sessionData.pendingQuestions.length}, Local: ${state.pendingQuestions.length}`)
        console.log(`- Server QA pairs: ${sessionData.qaPairs.length}, Local: ${state.qaPairs.length}`)
        
        // If there's a mismatch, update local state
        const shouldUpdate = 
          sessionData.questions.length !== state.questions.length ||
          sessionData.pendingQuestions.length !== state.pendingQuestions.length;
          
        if (shouldUpdate) {
          console.log("Updating local state with server data due to mismatch")
          
          // Prepare server data for local update
          const newState: any = {}
          
          // Only update questions if there's a mismatch
          if (sessionData.questions.length !== state.questions.length) {
            newState.questions = sessionData.questions
          }
          
          // Only update pendingQuestions if there's a mismatch
          if (sessionData.pendingQuestions.length !== state.pendingQuestions.length) {
            newState.pendingQuestions = sessionData.pendingQuestions
          }
          
          // Update QA pairs if needed while preserving local answers
          if (sessionData.qaPairs.length !== state.qaPairs.length) {
            // Create a map of local answers to preserve them
            const localAnswers = new Map<string, string>()
            state.qaPairs.forEach(qa => {
              if (qa.answer && qa.answer.trim()) {
                localAnswers.set(qa.id, qa.answer)
              }
            })
            
            // Apply local answers to server QA pairs
            const updatedQAPairs = sessionData.qaPairs.map((qa: { id: string, question: string, answer: string }) => {
              if (localAnswers.has(qa.id)) {
                return { ...qa, answer: localAnswers.get(qa.id) || "" }
              }
              return qa
            })
            
            newState.qaPairs = updatedQAPairs
          }
          
          // Calculate correct progress
          newState.progress = {
            current: sessionData.questions.length - sessionData.pendingQuestions.length,
            total: sessionData.questions.length
          }
          
          // Update local state
          useStore.setState(newState)
          
          // Force progress recalculation to ensure consistency
          if (typeof state.recalculateProgress === 'function') {
            console.log("Recalculating progress after sync")
            state.recalculateProgress();
          }
        }
      }
      
      return true
    } catch (error) {
      console.error("Error fetching full session data:", error)
      return false
    }
  }
} 