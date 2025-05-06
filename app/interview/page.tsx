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
    addMessage,
    updateMessage,
    isRecording,
    setIsRecording,
    progress,
    setProgress,
    prolificId,
    saveSession,
    sessionStatus,
    questions,
    qaPairs,
    updateQAPair,
    pendingQuestions,
    getNextQuestion,
    markQuestionAsAnswered
  } = useStore()

  // 在组件挂载时输出调试信息
  useEffect(() => {
    console.log("==== Component mounted, outputting Store state ====")
    logStoreState()
    setupStoreLogger()  // Setup automatic logging of state changes
  }, [])

  // Reference to track the last saved state
  const lastSavedQAPairsRef = useRef<string>("")
  
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

  // Current question being asked
  const currentQuestion = getNextQuestion()

  // Redirect if no ProlificID or if session is completed
  useEffect(() => {
    // Check if user has a valid Prolific ID
    if (!prolificId) {
      console.log("No Prolific ID found, redirecting to landing page")
      router.push("/")
      return
    }
    
    // If session is marked as completed, redirect to thank you page
    if (sessionStatus === "completed") {
      console.log("Session already completed, redirecting to thank you page")
      router.push("/thank-you")
      return
    }
  }, [prolificId, router, sessionStatus])

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
      // Populate messages from qaPairs for any answered questions
      qaPairs.forEach((pair) => {
        if (pair.answer) {
          // Add the question message (bot)
          addMessage({
            id: `bot-${pair.id}`,
            role: "bot",
            text: pair.question,
            loading: false,
          })
          
          // Add the answer message (user)
          addMessage({
            id: `user-${pair.id}`,
            role: "user",
            text: pair.answer,
            loading: false,
          })
        }
      })
    }
  }, [messages.length, qaPairs, addMessage]);

  const handleSendMessage = (text: string) => {
    // If there's no current question, don't proceed
    if (!currentQuestion) {
      return;
    }

    // Add user message
    const userMessageId = `user-${Date.now()}`
    addMessage({
      id: userMessageId,
      role: "user",
      text,
      loading: false,
    })

    // Update the QA pair with the user's answer
    updateQAPair(currentQuestion.id, { answer: text })

    // Get current question ID before marking it as answered
    const answeredQuestionId = currentQuestion.id

    // Mark current question as answered, which removes it from the pending queue
    markQuestionAsAnswered(answeredQuestionId)

    // Start real-time progress animation
    const startProgress = progress.current
    const targetProgress = Math.min(progress.current + 1, questions.length)
    const duration = 2000 // 2 seconds for the animation
    const startTime = Date.now()

    const animateProgress = () => {
      const elapsed = Date.now() - startTime
      const progressFraction = Math.min(1, elapsed / duration)
      const currentProgress = startProgress + progressFraction

      setRealTimeProgress(currentProgress)

      if (progressFraction < 1) {
        requestAnimationFrame(animateProgress)
      }
    }

    requestAnimationFrame(animateProgress)

    // Get the next question (will be null if no more questions)
    const nextQuestion = getNextQuestion()
    const isLastQuestion = !nextQuestion

    // Simulate bot typing response
    const botMessageId = `bot-${Date.now()}`
    addMessage({
      id: botMessageId,
      role: "bot",
      text: "",
      loading: true,
    })

    // First response is a thank you, second is the next question
    const botResponse = isLastQuestion
      ? "Thank you for sharing your thoughts. That's all the questions we have for you today. Please proceed to the review page to check your answers before submitting."
      : `Thank you for your response. ${nextQuestion?.text}`

    mockWebSocketConnection(
      botResponse,
      (chunk) => {
        updateMessage(botMessageId, (prev) => ({
          ...prev,
          text: prev.text + chunk,
        }))
      },
      () => {
        updateMessage(botMessageId, (prev) => ({
          ...prev,
          loading: false,
        }))

        // Manually trigger conditional save after response is complete
        conditionalSave()

        // If we've reached the end of the interview, redirect to review page
        if (isLastQuestion) {
          setTimeout(() => {
            router.push("/review")
          }, 3000)
        }
      },
    )
  }

  // Use real-time progress for the progress bar
  const displayProgress = {
    current: Math.floor(realTimeProgress),
    total: questions.length,
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
              <div className="text-lg font-light">{currentQuestion.text}</div>
            </div>
          )}
          <ElegantProgressBar progress={displayProgress} />
        </div>
        <div className="flex-1 overflow-y-auto pt-6">
          <ChatPanel />
        </div>
        <AnswerInput onSendMessage={handleSendMessage} />
      </div>
      
      <Footer showLogo={false} />
    </motion.div>
  )
}
