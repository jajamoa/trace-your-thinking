"use client"

import { useState, useEffect, useRef, useMemo } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import ChatPanel from "@/components/ChatPanel"
import AnswerInput from "@/components/AnswerInput"
import { useStore } from "@/lib/store"
import { mockWebSocketConnection } from "@/lib/ws"
import ElegantProgressBar from "@/components/ElegantProgressBar"
import ProlificIdBadge from "@/components/ProlificIdBadge"
import Footer from "@/components/Footer"
import { logStoreState, setupStoreLogger } from "@/lib/debug-store"
import { SyncService } from "@/lib/sync-service"
import { PythonAPIService } from "@/lib/python-api-service"
import { v4 as uuidv4 } from "uuid"
import LoadingTransition from "@/components/LoadingTransition"
import React from "react"

// Create a memoized AnswerInput component to prevent unnecessary re-renders
const MemoizedAnswerInput = React.memo(
  AnswerInput,
  (prevProps, nextProps) => {
    // Only re-render if isProcessing changes or if onSendMessage function changes
    // This prevents re-renders when current question changes
    return prevProps.isProcessing === nextProps.isProcessing &&
           prevProps.onSendMessage === nextProps.onSendMessage;
  }
);

// Debounce function to prevent too frequent calls
const debounce = (fn: Function, ms = 1000) => {
  let timeoutId: ReturnType<typeof setTimeout>
  return function(...args: any[]) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), ms)
  }
}

export default function InterviewPage() {
  const router = useRouter()
  const [isNavigating, setIsNavigating] = useState(false)
  const [navigatingMessage, setNavigatingMessage] = useState("")
  
  // Add state for Python backend processing
  const [isProcessing, setIsProcessing] = useState(false)
  
  const {
    messages,
    qaPairs,
    addMessage,
    updateMessage,
    progress,
    setProgress,
    prolificId,
    status,
    getNextQuestion,
    markQuestionAsAnswered,
    updateQAPair,
    saveSession,
    initializeWithGuidingQuestions,
    recalculateProgress,
    sessionId,
    currentQuestionIndex,
    addNewQuestion,
    pendingRequests
  } = useStore()

  // Output debug information when component mounts
  useEffect(() => {
    console.log("==== Component mounted, outputting Store state ====")
    logStoreState()
    setupStoreLogger()  // Setup automatic logging of state changes
    
    // Ensure progress is correctly calculated on page load
    console.log("Ensuring progress accuracy on interview page load")
    recalculateProgress()
    
    // Sync processing queue with QA pairs
    console.log("Syncing processing queue with QA pairs")
    useStore.getState().syncProcessingQueue()
  }, [recalculateProgress])

  // Reference to track the last saved state
  const lastSavedQAPairsRef = useRef<string>("")
  
  // Track current question ID for AnswerInput key
  const [currentQuestionId, setCurrentQuestionId] = useState<string>("")

  // Create a debounced version of saveSession function
  const debouncedSaveSession = useRef(
    debounce(() => {
      console.log("Executing debouncedSaveSession")
      saveSession()
    }, 2000)
  ).current

  // Create conditional save function
  const conditionalSave = () => {
    // Serialize current QAPairs for comparison
    const currentQAPairsString = JSON.stringify(qaPairs)
    
    console.log("conditionalSave - Current qaPairs:", currentQAPairsString)
    console.log("conditionalSave - Previously saved qaPairs:", lastSavedQAPairsRef.current)
    
    // Only save when QAPairs have changed
    if (currentQAPairsString !== lastSavedQAPairsRef.current) {
      console.log("qaPairs change detected, preparing to save")
      lastSavedQAPairsRef.current = currentQAPairsString
      debouncedSaveSession()
    } else {
      console.log("qaPairs unchanged, skipping save")
    }
  }

  // State to track real-time progress animation
  const [realTimeProgress, setRealTimeProgress] = useState(progress.current)

  // Sync realTimeProgress with store progress whenever it changes
  useEffect(() => {
    setRealTimeProgress(progress.current)
  }, [progress.current])

  // Current question being asked
  const currentQuestion = getNextQuestion()
  
  // Update currentQuestionId when question changes
  useEffect(() => {
    if (currentQuestion && currentQuestion.id !== currentQuestionId) {
      setCurrentQuestionId(currentQuestion.id)
    }
  }, [currentQuestion])

  // Custom navigation function that shows loading state
  const navigateTo = (path: string, loadingMessage = "Navigating...") => {
    // Start loading animation
    setNavigatingMessage(loadingMessage)
    setIsNavigating(true)
    
    // Add a small delay for the animation to be visible
    setTimeout(() => {
      router.push(path)
    }, 800)
  }
  
  // Redirect if no ProlificID or if session is completed or if no sessionId
  useEffect(() => {
    // Skip if we're already navigating
    if (isNavigating) return
    
    // Check if user has a valid Prolific ID
    if (!prolificId) {
      console.log("No Prolific ID found, redirecting to landing page")
      navigateTo("/", "Redirecting to login...")
      return
    }
    
    // If no sessionId, redirect to home page instead of creating one
    if (!sessionId) {
      console.log("No Session ID found, redirecting to landing page")
      navigateTo("/", "Redirecting to login...")
      return
    }
    
    // If session is marked as completed, redirect to thank you page
    if (status === "completed") {
      console.log("Session already completed, redirecting to thank you page")
      navigateTo("/thank-you", "Session completed, preparing thank you page...")
      return
    }

    // Check if all questions have been answered (progress is 100%) AND all questions are processed
    // Only redirect to review page when both conditions are met
    const areAllQuestionsAnswered = progress.current === progress.total && progress.total > 0;
    const hasPendingProcessing = useStore.getState().hasPendingRequests();
    
    if (areAllQuestionsAnswered) {
      if (!hasPendingProcessing) {
        console.log("All questions answered and processed, redirecting to review page")
        navigateTo("/review", "Preparing your answers for review...")
        return
      } else {
        console.log("All questions answered but some are still being processed, waiting for completion...")
      }
    }

    // If there are no messages but QA pairs exist, rebuild messages from QA pairs
    if (messages.length === 0 && qaPairs.length > 0) {
      console.log("Rebuilding messages from QA pairs")
      SyncService.displayQAPairsAsMessages()
      
      // After rebuilding messages, recalculate progress
      console.log("Recalculating progress after rebuilding messages")
      recalculateProgress()
    }
    
    // If no questions but we have a valid sessionId, try to get questions
    if (qaPairs.length === 0 && sessionId) {
      console.log("No questions found but have sessionId, initializing with guiding questions")
      setIsNavigating(true)
      setNavigatingMessage("Loading questions...")
      
      initializeWithGuidingQuestions().then(() => {
        console.log("Guiding questions loaded")
        // Use debounced save to avoid multiple calls
        debouncedSaveSession()
        setIsNavigating(false)
      })
    }
  }, [prolificId, router, status, progress, qaPairs.length, messages.length, initializeWithGuidingQuestions, saveSession, recalculateProgress, isNavigating, sessionId])

  // Save session when QA pairs change
  useEffect(() => {
    if (qaPairs.length > 0) {
      // Initialize lastSavedQAPairsRef
      if (lastSavedQAPairsRef.current === "") {
        lastSavedQAPairsRef.current = JSON.stringify(qaPairs)
      }
      conditionalSave()
    }
  }, [qaPairs])

  // Update the function that handles submitting an answer
  const handleAnswerSubmit = async (text: string) => {
    if (text.trim() === "") return
    
    // Get current question
    const currentQuestion = getNextQuestion()
    if (!currentQuestion) {
      console.log("No current question found!")
      return
    }

    console.log(`Submitting answer for question ${currentQuestion.id}: "${currentQuestion.shortText}"`)
    console.log(`Current progress before answering: ${progress.current}/${progress.total}`)

    try {
      const timestamp = Date.now();
      const messageId = `msg_a_${currentQuestion.id}_${timestamp}`
      addMessage({
        id: messageId,
        role: "user",
        text,
        loading: false,
      })

      // Update QA pair with answer
      console.log(`Updating QA pair for question: ${currentQuestion.id}`)
      updateQAPair(currentQuestion.id, { answer: text })

      // Get current progress before marking question as answered
      const startProgress = progress.current
      console.log(`Progress before marking question as answered: ${startProgress}/${progress.total}`)
      
      // Important: Use a flag to prevent double-adding the next question 
      // markQuestionAsAnswered will trigger moveToNextQuestion, which already adds the next question
      const currentIndex = currentQuestionIndex;
      
      // Check if this is a tutorial question - if so, skip Python backend processing
      const isTutorialQuestion = currentQuestion.category === "tutorial";
      
      if (!isTutorialQuestion) {
        // Add QA processing to async queue instead of synchronous waiting
        try {
          // Get the updated QA Pair with answer for sending to Python backend
          const updatedQAPair = {
            ...currentQuestion,
            answer: text
          };
          
          // Ensure the QA pair has the correct format
          const validQAPair = {
            id: updatedQAPair.id,
            question: updatedQAPair.question || '',
            shortText: updatedQAPair.shortText || '',
            answer: updatedQAPair.answer || '',
            category: updatedQAPair.category || 'research'
          };
          
          // Add to pending request queue
          console.log("Adding to async processing queue...");
          const requestId = useStore.getState().addPendingRequest(validQAPair.id);
          console.log(`Added to pending requests with ID: ${requestId}`);
          
          // Start processing the first request in the queue (if no request is currently being processed)
          useStore.getState().processNextPendingRequest();
        } catch (queueError) {
          console.error("Error queueing request for async processing:", queueError);
        }
      } else {
        // For tutorial questions, log that we're skipping Python backend
        console.log("Tutorial question detected, skipping Python backend processing");
      }
      
      // Mark this question as answered - this updates the store progress state
      // This will also trigger moveToNextQuestion which will add the next question message
      markQuestionAsAnswered(currentQuestion.id)
      
      // Log updated progress after marking question as answered
      console.log(`Progress after marking question as answered: ${progress.current}/${progress.total}`)
      
      // Calculate target progress
      const targetProgress = Math.min(progress.current + 1, qaPairs.length)
      console.log(`Target progress for animation: ${targetProgress}/${qaPairs.length}`)
      
      // Start real-time progress animation - using a shorter duration for more responsive feeling
      const duration = 800 // Reduced from 2000ms to 800ms for more responsive feeling
      const startTime = Date.now()
      
      // Immediately update progress slightly to give instant feedback
      setRealTimeProgress(startProgress + 0.2) 
      
      const animateProgress = () => {
        const elapsed = Date.now() - startTime
        const progressFraction = Math.min(1, elapsed / duration)
        
        // Calculate current progress using easing function
        const easedProgress = startProgress + 
          (targetProgress - startProgress) * 
          easeOutQuad(progressFraction)
        
        setRealTimeProgress(easedProgress)
        
        if (progressFraction < 1) {
          requestAnimationFrame(animateProgress)
        } else {
          // Ensure we reach exact target at the end
          setRealTimeProgress(targetProgress)
          console.log(`Progress animation completed: ${targetProgress}/${qaPairs.length}`)
          
          // Check if progress is 100% after animation
          if (targetProgress === qaPairs.length && qaPairs.length > 0) {
            // Also check if there are any pending processing requests
            const hasPendingProcessing = useStore.getState().hasPendingRequests();
            
            if (!hasPendingProcessing) {
              console.log("Animation finished, progress is 100%, and all questions processed - navigating to review")
              navigateTo("/review", "Preparing your answers for review...")
              return
            } else {
              console.log("Progress is 100% but some questions are still being processed, waiting for completion...")
            }
          }
        }
      }
      
      // Start animation
      requestAnimationFrame(animateProgress)

      // Save session to database - don't await this to avoid delaying UI updates
      console.log("Saving session to database...")
      saveSession()

      // Get next question after markQuestionAsAnswered has been called
      const nextQuestion = getNextQuestion()
      
      // MODIFIED: Remove the code that adds bot messages, since moveToNextQuestion already does this
      // Just update the currentQuestionId if we have a next question
      if (nextQuestion) {
        console.log(`Next question ready: ${nextQuestion.id} - "${nextQuestion.shortText}"`)
        setCurrentQuestionId(nextQuestion.id)
      } else {
        // All questions answered, redirect to review
        console.log("All questions answered, redirecting to review page")
        navigateTo("/review", "Preparing your answers for review...")
      }
    } catch (error) {
      console.error("Error submitting answer:", error)
      setIsProcessing(false)
    }
  }
  
  // Easing function for smoother progress animation - more pronounced curve for better feedback
  const easeOutQuad = (t: number): number => t * (2 - t)

  // Use real-time progress for the progress bar
  const displayProgress = {
    current: Math.floor(realTimeProgress),
    total: qaPairs.length,
  }

  // Get processing count for the status indicator
  const processingCount = pendingRequests.filter(req => 
    req.status === 'pending' || req.status === 'processing'
  ).length;

  // Add special handling for returning from other pages like Review
  useEffect(() => {
    const syncWithServer = async () => {
      if (sessionId) {
        // This will ensure our local data matches the server
        console.log("Interview page: Syncing with server data");
        try {
          // First try to get full session data
          const syncResult = await SyncService.fetchFullSessionData(sessionId);
          if (syncResult) {
            console.log("Successfully synced with server data");
            // Force recalculation after sync
            recalculateProgress();
            
            // Sync processing queue with QA pairs
            useStore.getState().syncProcessingQueue();
          } else {
            console.warn("Failed to sync with server, falling back to local recalculation");
            recalculateProgress();
          }
        } catch (error) {
          console.error("Error syncing with server:", error);
          // Still try to recalculate locally in case of error
          recalculateProgress();
        }
      }
    };

    // Run the sync when component mounts
    syncWithServer();
  }, [sessionId, recalculateProgress]); // Only run when sessionId changes or on first mount

  // Monitor pending requests to auto-navigate to review when all processing is complete
  useEffect(() => {
    // Skip if already navigating
    if (isNavigating) return;
    
    // If we have no pending requests and all questions are answered, navigate to review
    const hasPendingProcessing = pendingRequests.some(req => 
      req.status === 'pending' || req.status === 'processing'
    );
    
    const areAllQuestionsAnswered = progress.current === progress.total && progress.total > 0;
    
    if (!hasPendingProcessing && areAllQuestionsAnswered && qaPairs.length > 0) {
      console.log("All questions answered and processing completed, navigating to review page");
      navigateTo("/review", "Preparing your answers for review...");
    }
  }, [pendingRequests, progress, qaPairs.length, isNavigating]);

  // Show loading transition when navigating
  if (isNavigating) {
    return <LoadingTransition message={navigatingMessage} />
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.12, ease: [0.4, 0, 0.2, 1] }}
      className="flex h-screen overflow-hidden bg-[#f5f2eb] relative"
    >
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full">
        <div className="sticky top-0 z-10 bg-[#f5f2eb]/80 backdrop-blur-lg pt-6 px-4">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-xl font-light">Trace Your Thinking</h1>
            <ProlificIdBadge />
          </div>
          {currentQuestion && (
            <div className="mb-4">
              <div className="text-sm text-gray-500 mb-1">Current Question</div>
              <div className="text-lg font-light">{currentQuestion.question}</div>
            </div>
          )}
          <ElegantProgressBar progress={displayProgress} processingCount={processingCount} />
        </div>
        <div className="flex-1 overflow-y-auto pt-6">
          <ChatPanel />
        </div>
        <MemoizedAnswerInput onSendMessage={handleAnswerSubmit} isProcessing={isProcessing} />
      </div>
      
      <Footer showLogo={false} />
    </motion.div>
  )
}
