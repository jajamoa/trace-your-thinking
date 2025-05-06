"use client"

import { useState, useEffect, useRef } from "react"
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
import { v4 as uuidv4 } from "uuid"

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
  const {
    messages,
    qaPairs,
    addMessage,
    updateMessage,
    progress,
    setProgress,
    prolificId,
    status,
    questions,
    pendingQuestions,
    getNextQuestion,
    markQuestionAsAnswered,
    updateQAPair,
    saveSession,
    initializeWithGuidingQuestions,
    recalculateProgress,
    sessionId
  } = useStore()

  // 在组件挂载时输出调试信息
  useEffect(() => {
    console.log("==== Component mounted, outputting Store state ====")
    logStoreState()
    setupStoreLogger()  // Setup automatic logging of state changes
    
    // Ensure progress is correctly calculated on page load
    console.log("Ensuring progress accuracy on interview page load")
    recalculateProgress()
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

  // Redirect if no ProlificID or if session is completed
  useEffect(() => {
    // Check if user has a valid Prolific ID
    if (!prolificId) {
      console.log("No Prolific ID found, redirecting to landing page")
      router.push("/")
      return
    }
    
    // If session is marked as completed, redirect to thank you page
    if (status === "completed") {
      console.log("Session already completed, redirecting to thank you page")
      router.push("/thank-you")
      return
    }

    // Check if all questions have been answered (progress is 100%)
    if (progress.current === questions.length && questions.length > 0) {
      console.log("All questions answered, redirecting to review page")
      router.push("/review")
      return
    }

    // If there are no messages but QA pairs exist, rebuild messages from QA pairs
    if (messages.length === 0 && qaPairs.length > 0) {
      console.log("Rebuilding messages from QA pairs")
      SyncService.displayQAPairsAsMessages()
      
      // After rebuilding messages, recalculate progress
      console.log("Recalculating progress after rebuilding messages")
      recalculateProgress()
    }
    
    // If no questions, initialize with guiding questions
    if (questions.length === 0) {
      console.log("No questions found, initializing with guiding questions")
      initializeWithGuidingQuestions().then(() => {
        console.log("Guiding questions loaded")
        saveSession()
      })
    }
  }, [prolificId, router, status, progress, questions.length, messages.length, qaPairs, initializeWithGuidingQuestions, saveSession, recalculateProgress])

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

  // Update the message UI based on QA pairs when component mounts
  useEffect(() => {
    // This ensures that when returning to the interview page,
    // the conversation reflects the current QA pairs
    if (messages.length === 0 && qaPairs.some(qa => qa.answer)) {
      // Use the SyncService to display QA pairs as messages instead of manually creating them
      SyncService.displayQAPairsAsMessages()
    }
  }, [messages.length, qaPairs]);

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

    // Get the QA pair for this question
    const qaPair = qaPairs.find(qa => qa.id === currentQuestion.id)
    if (!qaPair) {
      console.log(`No QA pair found for question ID: ${currentQuestion.id}`)
      return
    }

    try {
      // Add user's answer to messages with a UUID
      const messageId = uuidv4()
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
      
      // Mark this question as answered - this updates the store progress state
      markQuestionAsAnswered(currentQuestion.id)
      
      // Log updated progress after marking question as answered
      console.log(`Progress after marking question as answered: ${progress.current}/${progress.total}`)
      
      // Calculate target progress
      const targetProgress = Math.min(progress.current + 1, questions.length)
      console.log(`Target progress for animation: ${targetProgress}/${questions.length}`)
      
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
          console.log(`Progress animation completed: ${targetProgress}/${questions.length}`)
        }
      }
      
      // Start animation
      requestAnimationFrame(animateProgress)

      // Save session to database - don't await this to avoid delaying UI updates
      console.log("Saving session to database...")
      saveSession()

      // Get next question
      const nextQuestion = getNextQuestion()
      if (nextQuestion) {
        console.log(`Next question: ${nextQuestion.id} - "${nextQuestion.shortText}"`)
        
        // First add bot message with loading state - uses a completely empty message
        const nextMessageId = uuidv4()
        addMessage({
          id: nextMessageId,
          role: "bot",
          text: "",
          loading: true,
        })
        
        // Update immediately with almost no delay
        // Important: Must pass a new object reference to trigger proper re-render
        setTimeout(() => {
          updateMessage(nextMessageId, (message) => ({
            ...message,
            text: nextQuestion.text,
            loading: false
          }))
        }, 10) // Nearly immediate update
        
        // Update current question ID
        setCurrentQuestionId(nextQuestion.id)
      } else {
        // All questions answered, redirect to review
        console.log("All questions answered, redirecting to review page")
        router.push("/review")
      }
    } catch (error) {
      console.error("Error submitting answer:", error)
    }
  }
  
  // Easing function for smoother progress animation - more pronounced curve for better feedback
  const easeOutQuad = (t: number): number => t * (2 - t)

  // Use real-time progress for the progress bar
  const displayProgress = {
    current: Math.floor(realTimeProgress),
    total: questions.length,
  }

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
              <div className="text-lg font-light">{currentQuestion.text}</div>
            </div>
          )}
          <ElegantProgressBar progress={displayProgress} />
        </div>
        <div className="flex-1 overflow-y-auto pt-6">
          <ChatPanel />
        </div>
        <AnswerInput key={currentQuestionId} onSendMessage={handleAnswerSubmit} />
      </div>
      
      <Footer showLogo={false} />
    </motion.div>
  )
}
