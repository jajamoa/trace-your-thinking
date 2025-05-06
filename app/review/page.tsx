"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Send, ArrowLeft, Check, AlertCircle, AlertTriangle } from "lucide-react"
import TranscriptEditor from "@/components/TranscriptEditor"
import { useStore } from "@/lib/store"
import { toast } from "@/components/ui/use-toast"
import ProlificIdBadge from "@/components/ProlificIdBadge"
import { Input } from "@/components/ui/input"
import Footer from "@/components/Footer"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"

export default function ReviewPage() {
  const router = useRouter()
  const {
    messages,
    qaPairs,
    loadFromLocalStorage,
    prolificId,
    setProlificId,
    sessionId,
    saveSession,
    sessionStatus,
    setSessionStatus,
    isRecording, 
    setIsRecording
  } = useStore()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [confirmProlificId, setConfirmProlificId] = useState("")
  const [confirmError, setConfirmError] = useState("")
  const [showIdMismatchDialog, setShowIdMismatchDialog] = useState(false)
  const [emptyAnswers, setEmptyAnswers] = useState<string[]>([])

  // Function to forcefully cancel any active recording
  const cancelAllRecordings = useCallback(() => {
    // Set global recording state to false
    setIsRecording(false)

    // Dispatch a custom event that AnswerInput components can listen for
    const cancelEvent = new CustomEvent('force-cancel-recording')
    window.dispatchEvent(cancelEvent)
    
    console.log("Forcefully cancelled all recordings on Review page")
  }, [setIsRecording])

  // Stop any active recording immediately when entering the review page
  useEffect(() => {
    console.log("Review page mounted - checking for active recordings")
    
    // Call our cancel function immediately on mount
    cancelAllRecordings()
    
    // Also listen for visibility changes to cancel recordings when switching back to this tab
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        cancelAllRecordings()
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    // Cleanup
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [cancelAllRecordings])
  
  // Monitor and forcefully stop recording if it somehow gets activated
  useEffect(() => {
    if (isRecording) {
      console.log("Recording detected on Review page - forcefully stopping")
      cancelAllRecordings()
    }
  }, [isRecording, cancelAllRecordings])

  useEffect(() => {
    // Load from localStorage if available
    loadFromLocalStorage()

    // If no prolificId, redirect to login
    if (!prolificId) {
      router.push("/")
      return
    }

    // If session is already completed, redirect to thank-you page
    if (sessionStatus === "completed") {
      router.push("/thank-you")
      return
    }

    // If no messages, redirect to interview
    if (messages.length === 0) {
      router.push("/interview")
    }
  }, [loadFromLocalStorage, messages.length, router, prolificId, sessionStatus])

  // Save session when entering review page
  useEffect(() => {
    if (qaPairs.length > 0) {
      saveSession()
    }
  }, [qaPairs, saveSession])

  const checkEmptyAnswers = () => {
    const empty = qaPairs.filter((pair) => !pair.answer.trim()).map((pair) => pair.id)

    setEmptyAnswers(empty)
    return empty.length === 0
  }

  const handleSubmitClick = () => {
    // First check if all answers are filled
    if (!checkEmptyAnswers()) {
      toast({
        title: "Incomplete Answers",
        description: "Please answer all questions before submitting.",
        variant: "destructive",
      })

      // Scroll to the first empty answer
      if (emptyAnswers.length > 0) {
        const element = document.getElementById(`answer-${emptyAnswers[0]}`)
        if (element) {
          element.scrollIntoView({ behavior: "smooth" })
        }
      }

      return
    }

    setConfirmProlificId("")
    setConfirmError("")
    setShowConfirmDialog(true)
  }

  const validateConfirmProlificId = (value: string) => {
    setConfirmProlificId(value)
    
    if (value.length > 0 && value.length < 4) {
      setConfirmError("Prolific ID must be at least 4 characters")
      return false
    } else {
      setConfirmError("")
      return true
    }
  }

  const handleConfirmIdCheck = () => {
    // First validate the ID length
    if (confirmProlificId.length < 4) {
      setConfirmError("Prolific ID must be at least 4 characters")
      return
    }
    
    // Check if Prolific ID matches
    if (confirmProlificId !== prolificId) {
      // Instead of just showing an error, show a dialog to confirm
      setShowConfirmDialog(false)
      setShowIdMismatchDialog(true)
    } else {
      // IDs match, proceed with submission
      setShowConfirmDialog(false)
      submitInterview(prolificId)
    }
  }

  const handleUseDifferentId = () => {
    // Check if the ID is valid first
    if (confirmProlificId.length < 4) {
      setConfirmError("Prolific ID must be at least 4 characters")
      setShowIdMismatchDialog(false)
      setShowConfirmDialog(true)
      return
    }
    
    // User has confirmed they want to use a different ID
    setShowIdMismatchDialog(false)

    // Update the Prolific ID in the store
    setProlificId(confirmProlificId)

    // Proceed with submission using the new ID
    submitInterview(confirmProlificId)
  }

  const submitInterview = async (id: string) => {
    try {
      setIsSubmitting(true)

      // First save all QA pairs data
      if (sessionId) {
        // Update existing session data
        const dataResponse = await fetch(`/api/sessions/${sessionId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prolificId: id,
            qaPairs,
          }),
        })

        if (!dataResponse.ok) {
          throw new Error("Failed to save interview data")
        }

        // Update session status using the dedicated status API endpoint
        // This uses a separate API to ensure clean separation of concerns
        const statusResponse = await fetch(`/api/sessions/status/${sessionId}`, {
          method: "PATCH", 
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status: "completed"
          }),
        })

        if (!statusResponse.ok) {
          throw new Error("Failed to update session status")
        }
      } else {
        // Create a new session if one doesn't exist
        const response = await fetch("/api/sessions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prolificId: id,
            qaPairs,
            status: "completed",
          }),
        })

        if (!response.ok) {
          throw new Error("Failed to submit")
        }
      }

      // Update local session status
      setSessionStatus("completed")

      // Redirect to thank you page
      router.push("/thank-you")
    } catch (error) {
      console.error("Submission error:", error)
      toast({
        title: "Error",
        description: "Failed to submit your interview. Please try again.",
        variant: "destructive",
      })
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen relative bg-[#f5f2eb]">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.12, ease: [0.4, 0, 0.2, 1] }}
        className="container mx-auto px-4 py-16 max-w-3xl relative"
      >
        <div className="flex items-center justify-between mb-10">
          <h1 className="text-3xl font-light tracking-tight text-[#333333]">Review Your Thinking</h1>
          <ProlificIdBadge />
        </div>

        {emptyAnswers.length > 0 && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
            <div className="text-sm text-amber-800">
              Please complete all answers before submitting. You have {emptyAnswers.length} unanswered question(s).
            </div>
          </div>
        )}

        <TranscriptEditor highlightEmptyAnswers={emptyAnswers} />

        <div className="mt-10 flex justify-center">
          <motion.div whileTap={{ scale: 0.96 }}>
            <Button
              onClick={handleSubmitClick}
              size="lg"
              disabled={isSubmitting}
              className="bg-[#333333] hover:bg-[#222222] text-white rounded-full shadow-subtle"
            >
              {isSubmitting ? "Submitting..." : "Submit Interview"}
              <Send className="ml-2 h-4 w-4" />
            </Button>
          </motion.div>
        </div>
      </motion.div>

      {/* Prolific ID Confirmation Dialog */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Confirm Submission</DialogTitle>
            <DialogDescription>Please confirm your Prolific ID to complete your submission.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="confirmProlificId" className="text-sm font-medium">
                Enter your Prolific ID
              </label>
              <Input
                id="confirmProlificId"
                value={confirmProlificId}
                onChange={(e) => validateConfirmProlificId(e.target.value)}
                placeholder="e.g. 5f8d7e6c9b2a1c3d4e5f6g7h"
                className={`bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400 ${
                  confirmError ? "border-red-300 focus:ring-red-400" : ""
                }`}
                minLength={4}
              />
              {confirmError && (
                <div className="flex items-center gap-2 text-red-500 text-sm mt-1">
                  <AlertCircle className="h-4 w-4" />
                  <span>{confirmError}</span>
                </div>
              )}
            </div>
            <div className="bg-[#f5f2eb] p-3 rounded-md">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Check className="h-4 w-4 text-green-500" />
                <span>By submitting, you confirm that your responses are complete and ready for analysis.</span>
              </div>
            </div>
          </div>
          <DialogFooter className="flex justify-between sm:justify-between">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowConfirmDialog(false)}
              className="border-[#e0ddd5]"
            >
              Cancel
            </Button>
            <Button 
              type="button" 
              onClick={handleConfirmIdCheck} 
              disabled={confirmProlificId.length < 4 || Boolean(confirmError)}
              className="bg-[#333333] hover:bg-[#222222] text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Confirm & Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ID Mismatch Confirmation Dialog */}
      <Dialog open={showIdMismatchDialog} onOpenChange={setShowIdMismatchDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Prolific ID Mismatch</DialogTitle>
            <DialogDescription>
              The Prolific ID you entered doesn't match the one you provided at the beginning.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <div className="flex items-start gap-3 p-3 bg-[#f5f2eb] rounded-md">
                <AlertCircle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium mb-1">Original ID:</p>
                  <p className="font-mono">{prolificId}</p>
                  <p className="font-medium mb-1 mt-3">New ID:</p>
                  <p className="font-mono">{confirmProlificId}</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mt-2">
                Please double-check both IDs. Which one would you like to use for your submission?
              </p>
            </div>
          </div>
          <DialogFooter className="flex flex-col sm:flex-row gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowIdMismatchDialog(false)
                setShowConfirmDialog(true)
              }}
              className="border-[#e0ddd5] w-full sm:w-auto"
            >
              Use Original ID
            </Button>
            <Button
              type="button"
              onClick={handleUseDifferentId}
              className="bg-[#333333] hover:bg-[#222222] text-white w-full sm:w-auto"
            >
              Use New ID
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      <Footer />
    </div>
  )
}
