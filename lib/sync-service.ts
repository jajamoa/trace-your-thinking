"use client"

import { useStore } from './store'
import { v4 as uuidv4 } from 'uuid'
import { QAPair } from './store'

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
              messages: state.messages,
              status: state.status,
              progress: state.progress,
              currentQuestionIndex: state.currentQuestionIndex
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
          messages: state.messages,
          status: state.status,
          progress: state.progress,
          currentQuestionIndex: state.currentQuestionIndex
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
        const fallbackQAPair = {
          id: `gq_fallback_${Date.now()}`,
          question: "Could you describe your current research focus and how it relates to the broader field?",
          shortText: "Research focus",
          answer: ""
        }
        
        // Update store with the fallback question
        useStore.setState({
          qaPairs: [fallbackQAPair],
          progress: {
            current: 0,
            total: 1
          },
          currentQuestionIndex: 0
        })
        
        // Display the fallback question
        if (addMessage) {
          addMessage({
            id: uuidv4(),
            role: "bot",
            text: fallbackQAPair.question,
            loading: false
          })
        }
        
        return true
      }
      
      // Transform guiding questions directly into QAPair format
      const qaPairs = guidingQuestions.map((gq: any) => ({
        id: gq.id,
        question: gq.text,
        shortText: gq.shortText,
        answer: ""
      }))
      
      // Update store with the guiding questions data
      useStore.setState({
        qaPairs,
        progress: {
          current: 0,
          total: qaPairs.length
        },
        currentQuestionIndex: 0
      })
      
      // Display the first question as a message
      if (qaPairs.length > 0 && addMessage) {
        console.log("Adding first question message:", qaPairs[0].question)
        addMessage({
          id: uuidv4(),
          role: "bot",
          text: qaPairs[0].question,
          loading: false
        })
      }
      
      return true
    } catch (error) {
      console.error("Error initializing session with guiding questions:", error)
      
      // Use fallback question on error
      const store = useStore.getState()
      const fallbackQAPair = {
        id: "q1",
        question: "Could you describe your current research focus and how it relates to the broader field?",
        shortText: "Research focus",
        answer: ""
      }
      
      useStore.setState({
        qaPairs: [fallbackQAPair],
        progress: { current: 0, total: 1 },
        currentQuestionIndex: 0
      })
      
      // Display fallback question
      if (store.addMessage) {
        store.addMessage({
          id: uuidv4(),
          role: "bot",
          text: fallbackQAPair.question,
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
      const { qaPairs, messages, addMessage, currentQuestionIndex } = state
      
      // Check if we have already rebuilt messages in this session
      // Using sessionStorage instead of localStorage ensures this is reset on page refresh
      const hasRebuiltMessages = sessionStorage.getItem('hasRebuiltMessages') === 'true'
      
      // Skip rebuilding messages if:
      // 1. We have already rebuilt messages in this session
      // 2. Messages already exist
      // 3. No QA pairs exist with answers (nothing to rebuild)
      if (hasRebuiltMessages || messages.length > 0 || !qaPairs.some(qa => qa.answer)) {
        console.log("Skipping message rebuild:", { 
          hasRebuiltMessages, 
          existingMessages: messages.length, 
          qaPairsWithAnswers: qaPairs.filter(qa => qa.answer).length 
        })
        return
      }
      
      console.log("Rebuilding messages from QA pairs:", qaPairs.length)
      
      // Clear existing messages
      useStore.setState({ messages: [] })
      
      // Process QA pairs in order, but only up to currentQuestionIndex
      // This ensures we only show messages for answered questions and the current question
      const qaPairsToShow = qaPairs.slice(0, currentQuestionIndex + 1)
      
      console.log(`Showing messages for ${qaPairsToShow.length} questions up to index ${currentQuestionIndex}`)
      
      qaPairsToShow.forEach((qaPair) => {
        // Add question message
        addMessage({
          id: uuidv4(),
          role: "bot",
          text: qaPair.question,
          loading: false
        })
        
        // Add answer message if it exists
        if (qaPair.answer && qaPair.answer.trim() !== '') {
          addMessage({
            id: uuidv4(),
            role: "user",
            text: qaPair.answer,
            loading: false
          })
        }
      })
      
      // Mark that we have rebuilt messages in this session
      sessionStorage.setItem('hasRebuiltMessages', 'true')
      
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
   * This is important to ensure local state is aligned with server data
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
        qaPairsCount: sessionData.qaPairs?.length || 0,
        status: sessionData.status,
        currentQuestionIndex: sessionData.currentQuestionIndex || 0
      })
      
      // Update local state with server data
      const state = useStore.getState()
      
      // Only update if we have valid data
      if (sessionData.qaPairs && sessionData.qaPairs.length > 0) {
        // Compare server and local data
        console.log("Comparing server and local data:")
        console.log(`- Server QA pairs: ${sessionData.qaPairs?.length || 0}, Local: ${state.qaPairs.length}`)
        console.log(`- Server current index: ${sessionData.currentQuestionIndex || 0}, Local: ${state.currentQuestionIndex}`)
        
        // If there's a mismatch, update local state
        const shouldUpdate = 
          (sessionData.qaPairs?.length || 0) !== state.qaPairs.length ||
          (sessionData.currentQuestionIndex || 0) !== state.currentQuestionIndex;
          
        if (shouldUpdate) {
          console.log("Updating local state with server data due to mismatch")
          
          // Prepare server data for local update
          const newState: any = {}
          
          // Update QA pairs if needed while preserving local answers
          if ((sessionData.qaPairs?.length || 0) !== state.qaPairs.length) {
            // Create a map of local answers to preserve them
            const localAnswers = new Map<string, string>()
            state.qaPairs.forEach(qa => {
              if (qa.answer && qa.answer.trim()) {
                localAnswers.set(qa.id, qa.answer)
              }
            })
            
            // Apply local answers to server QA pairs
            const updatedQAPairs = (sessionData.qaPairs || []).map((qa: { id: string, question: string, shortText: string, answer: string }) => {
              if (localAnswers.has(qa.id)) {
                return { ...qa, answer: localAnswers.get(qa.id) || "" }
              }
              return qa
            })
            
            newState.qaPairs = updatedQAPairs
          }
          
          // Update currentQuestionIndex if needed
          if (sessionData.currentQuestionIndex !== undefined && 
              sessionData.currentQuestionIndex !== state.currentQuestionIndex) {
            newState.currentQuestionIndex = sessionData.currentQuestionIndex;
          } else {
            // Calculate correct currentQuestionIndex based on answered questions
            // Find the index of the first unanswered question
            const qaPairs = newState.qaPairs || state.qaPairs;
            let newCurrentQuestionIndex = 0;
            
            // Get all answered questions
            const answeredCount = qaPairs.filter((qa: QAPair) => qa.answer && qa.answer.trim() !== '').length;
            
            // Set index to the first unanswered question
            newCurrentQuestionIndex = Math.min(answeredCount, qaPairs.length - 1);
            if (newCurrentQuestionIndex < 0 && qaPairs.length > 0) newCurrentQuestionIndex = 0;
            
            newState.currentQuestionIndex = newCurrentQuestionIndex;
          }
          
          // Calculate correct progress based on currentQuestionIndex and answered QA pairs
          const qaPairs = newState.qaPairs || state.qaPairs;
          const currentQuestionIndex = newState.currentQuestionIndex !== undefined 
            ? newState.currentQuestionIndex 
            : state.currentQuestionIndex;
          
          newState.progress = {
            current: currentQuestionIndex,
            total: qaPairs.length
          }
          
          console.log(`Calculated new question index: ${newState.currentQuestionIndex}, Progress: ${newState.progress.current}/${newState.progress.total}`);
          
          // Update local state
          useStore.setState(newState)
          
          // Force progress recalculation to ensure consistency
          if (typeof state.recalculateProgress === 'function') {
            console.log("Recalculating progress after sync")
            state.recalculateProgress();
          }
          
          // Check if we need to rebuild messages from QA pairs
          // Only rebuild if we have no messages and there are QA pairs with answers
          if (state.messages.length === 0 && (sessionData.qaPairs || []).some((qa: any) => qa.answer)) {
            console.log("Messages empty but QA pairs exist - rebuilding messages after server sync")
            // Call displayQAPairsAsMessages to rebuild messages from QA pairs
            // The function has its own safeguards to prevent multiple rebuilds
            this.displayQAPairsAsMessages();
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