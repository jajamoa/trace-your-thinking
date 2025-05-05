"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import ChatPanel from "@/components/ChatPanel"
import AnswerInput from "@/components/AnswerInput"
import { useStore } from "@/lib/store"
import { mockWebSocketConnection } from "@/lib/ws"
import ElegantProgressBar from "@/components/ElegantProgressBar"
import ProlificIdBadge from "@/components/ProlificIdBadge"

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
    currentQuestionIndex,
    setCurrentQuestionIndex,
  } = useStore()

  // State to track real-time progress
  const [realTimeProgress, setRealTimeProgress] = useState(0)

  useEffect(() => {
    // Check if user has a Prolific ID
    const storedProlificId = localStorage.getItem("prolificId")

    if (!prolificId && storedProlificId) {
      // If we have it in localStorage but not in state, set it
      useStore.getState().setProlificId(storedProlificId)
    } else if (!prolificId && !storedProlificId) {
      // If we don't have it anywhere, redirect to home
      router.push("/")
      return
    }

    // If the session is already completed, redirect to thank-you page
    if (sessionStatus === "completed") {
      router.push("/thank-you")
      return
    }

    // Initialize with a bot message if there are no messages
    if (messages.length === 0) {
      addMessage({
        id: "welcome",
        role: "bot",
        text: "Welcome to the interview. I'll be asking you a series of questions about your thinking process.",
        loading: false,
      })

      // Add the first question after a delay
      setTimeout(() => {
        addMessage({
          id: questions[0].id,
          role: "bot",
          text: questions[0].text,
          loading: false,
        })
      }, 1000)

      // Initialize progress
      setProgress({ current: 0, total: questions.length })
      setRealTimeProgress(0)
    }

    // Setup keyboard shortcut for redo (R key)
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "r" || e.key === "R") {
        if (messages.length > 0 && messages[messages.length - 1].role === "user") {
          // Remove the last user message
          const newMessages = [...messages]
          newMessages.pop()
          useStore.setState({ messages: newMessages })

          // Start recording again
          setIsRecording(true)
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [addMessage, messages, setIsRecording, setProgress, prolificId, router, sessionStatus, questions])

  // Save session periodically
  useEffect(() => {
    if (messages.length > 0) {
      saveSession()
    }
  }, [messages, saveSession])

  const handleSendMessage = (text: string) => {
    // Add user message
    addMessage({
      id: `user-${Date.now()}`,
      role: "user",
      text,
      loading: false,
    })

    // Start real-time progress animation
    const startProgress = currentQuestionIndex
    const targetProgress = Math.min(currentQuestionIndex + 1, questions.length - 1)
    const duration = 2000 // 2 seconds for the animation
    const startTime = Date.now()

    const animateProgress = () => {
      const elapsed = Date.now() - startTime
      const progressFraction = Math.min(1, elapsed / duration)
      const currentProgress = startProgress + progressFraction

      setRealTimeProgress(currentProgress)

      if (progressFraction < 1) {
        requestAnimationFrame(animateProgress)
      } else {
        // Update the actual progress when animation completes
        setCurrentQuestionIndex(targetProgress)
      }
    }

    requestAnimationFrame(animateProgress)

    // Simulate bot typing response
    const botMessageId = `bot-${Date.now()}`
    addMessage({
      id: botMessageId,
      role: "bot",
      text: "",
      loading: true,
    })

    // Use mock WebSocket to stream response
    const nextQuestionIndex = Math.min(currentQuestionIndex + 1, questions.length - 1)
    const isLastQuestion = nextQuestionIndex === questions.length - 1

    // First response is a thank you, second is the next question
    const botResponse = isLastQuestion
      ? "Thank you for sharing your thoughts. That's all the questions we have for you today. Please proceed to the review page to check your answers before submitting."
      : `Thank you for your response. ${questions[nextQuestionIndex].text}`

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

        // Save session after each response
        saveSession()

        // If we've reached the end of the interview, redirect to review page
        if (nextQuestionIndex === questions.length - 1) {
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
      className="flex h-screen overflow-hidden bg-[#f5f2eb]"
    >
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full">
        <div className="sticky top-0 z-10 bg-[#f5f2eb]/80 backdrop-blur-lg pt-6 px-4">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-xl font-light">Trace Your Thinking</h1>
            <ProlificIdBadge />
          </div>
          {currentQuestionIndex < questions.length && (
            <div className="mb-4">
              <div className="text-sm text-gray-500 mb-1">Current Question</div>
              <div className="text-lg font-light">{questions[currentQuestionIndex].text}</div>
            </div>
          )}
          <ElegantProgressBar progress={displayProgress} />
        </div>
        <div className="flex-1 overflow-y-auto pt-6">
          <ChatPanel />
        </div>
        <AnswerInput onSendMessage={handleSendMessage} />
      </div>
    </motion.div>
  )
}
