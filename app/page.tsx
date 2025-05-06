"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowRight, AlertCircle } from "lucide-react"
import GridBackground from "@/components/GridBackground"
import { z } from "zod"
import { useStore } from "@/lib/store"
import Footer from "@/components/Footer"
import MobileRedirect from "@/components/MobileRedirect"
import useDeviceDetect from "@/hooks/useDeviceDetect"
import { SyncService } from "@/lib/sync-service"

// Schema for Prolific ID validation
const prolificSchema = z.object({
  id: z.string().min(4, "Prolific ID must be at least 4 characters").max(24),
})

export default function Home() {
  const router = useRouter()
  const [prolificId, setProlificId] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const { setProlificId: setStoreProlificId, prolificId: existingProlificId, status } = useStore()
  const { isMobile } = useDeviceDetect()

  useEffect(() => {
    // Skip redirects on mobile devices
    if (isMobile) return
    
    // If user already has a Prolific ID and session is completed, go to thank you page
    if (existingProlificId && status === "completed") {
      router.push("/thank-you")
      return
    }

    // If user already has a Prolific ID and session is in progress, go to interview page
    if (existingProlificId && status === "in_progress") {
      router.push("/interview")
      return
    }

    // If there's an existing Prolific ID, pre-fill the input
    if (existingProlificId) {
      setProlificId(existingProlificId)
    }
  }, [existingProlificId, router, status, isMobile])

  const validateInput = (value: string) => {
    setProlificId(value)
    
    if (value.length > 0 && value.length < 4) {
      setError("Prolific ID must be at least 4 characters")
    } else {
      setError("")
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (isLoading) return

    try {
      // Validate input
      const validationResult = prolificSchema.safeParse({ id: prolificId })
      
      if (!validationResult.success) {
        setError(validationResult.error.errors[0].message)
        return
      }
      
      setIsLoading(true)
      
      // IMPORTANT: First set the Prolific ID in the store
      // This ensures SessionCheck won't redirect back to home
      setStoreProlificId(prolificId)
      
      // Use SyncService to create a new session with the prolific ID
      const result = await SyncService.createNewSession(prolificId)
      
      if (result.success && result.sessionId) {
        console.log("Session created successfully with ID:", result.sessionId)
        
        // Ensure the sessionId is properly set in the store
        const currentSessionId = useStore.getState().sessionId
        if (!currentSessionId) {
          console.log("Setting session ID in store:", result.sessionId)
          useStore.getState().setSessionId(result.sessionId)
          
          // Give a moment for the state to update
          await new Promise(resolve => setTimeout(resolve, 200))
        }
        
        // Double-check that pendingQuestions are loaded
        const state = useStore.getState()
        if (state.pendingQuestions.length === 0 || state.qaPairs.length === 0) {
          console.log("Waiting for questions to load...")
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
        
        // Only redirect after we confirm we have a valid session ID and data
        console.log("All checks passed, redirecting to interview page")
        router.push("/interview")
      } else {
        console.error("Failed to create session properly")
        setError("Failed to create session. Please try again.")
        setIsLoading(false)
      }
    } catch (err) {
      console.error("Error in form submission:", err)
      setError("An unexpected error occurred")
      setIsLoading(false)
    }
  }

  // If on mobile, show the mobile-specific content
  if (isMobile) {
    return <MobileRedirect />
  }

  // Desktop view
  return (
    <main className="relative min-h-screen overflow-hidden">
      {/* Grid Background */}
      <div className="absolute inset-0 z-0 bg-[#f5f2eb]">
        <GridBackground />
      </div>

      {/* Content */}
      <div className="container relative z-10 mx-auto px-4 py-24 flex flex-col items-center justify-center min-h-screen">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="text-center max-w-3xl mx-auto"
        >
          <h1 className="text-5xl md:text-6xl font-light mb-4 tracking-tight">
            Trace Your <span className="font-normal text-blue-600">Thinking</span>
          </h1>

          <p className="text-lg md:text-xl text-gray-600 mb-12 max-w-xl mx-auto leading-relaxed">
            We're building a map of public reasoning — your perspective matters.
          </p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="bg-white p-8 rounded-3xl shadow-subtle max-w-md mx-auto border border-[#e0ddd5]"
          >
            <h2 className="text-2xl font-light mb-6">Welcome</h2>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <label htmlFor="prolificId" className="block text-sm font-medium text-gray-700">
                  Please enter your Prolific ID
                </label>
                <Input
                  id="prolificId"
                  type="text"
                  value={prolificId}
                  onChange={(e) => validateInput(e.target.value)}
                  placeholder="e.g. 5f8d7e6c9b2a1c3d4e5f6g7h"
                  className={`bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400 ${
                    error ? "border-red-300 focus:ring-red-400" : ""
                  }`}
                  minLength={4}
                />
                {error && (
                  <div className="flex items-center gap-2 text-red-500 text-sm mt-1">
                    <AlertCircle className="h-4 w-4" />
                    <span>{error}</span>
                  </div>
                )}
              </div>

              <motion.div whileTap={{ scale: 0.96 }} transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}>
                <Button
                  type="submit"
                  size="lg"
                  disabled={!prolificId || prolificId.length < 4 || isLoading}
                  className="bg-[#333333] hover:bg-[#222222] text-white px-8 py-6 text-base rounded-full shadow-subtle transition-all duration-300 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? "Creating session..." : "Begin"}
                  {!isLoading && <ArrowRight className="ml-2 h-5 w-5" />}
                </Button>
              </motion.div>
            </form>
          </motion.div>
        </motion.div>
      </div>

      <Footer showAboutLink={true} />
    </main>
  )
}
