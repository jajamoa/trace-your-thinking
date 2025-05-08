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

// Debug component to troubleshoot rendering issues
const DebugPanel = ({ data }: { data: Record<string, any> }) => {
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      zIndex: 9999,
      background: 'rgba(255,255,255,0.9)',
      padding: '10px',
      border: '1px solid red',
      maxWidth: '300px',
      fontSize: '12px',
      fontFamily: 'monospace',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>Debug Info:</div>
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>{key}: {String(value)}</div>
      ))}
      <div style={{ marginTop: '5px' }}>Rendered at: {new Date().toISOString()}</div>
    </div>
  )
}

export default function Home() {
  const router = useRouter()
  const [prolificId, setProlificId] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const { setProlificId: setStoreProlificId, prolificId: existingProlificId, status, sessionId } = useStore()
  const { isMobile } = useDeviceDetect()
  // Use state to safely handle research topic in client component 
  const [researchTopic, setResearchTopic] = useState<string | null>(null)
  // Add a mounted state to track if component is mounted
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    // Set research topic after component mounts to ensure client-server consistency
    setResearchTopic(process.env.NEXT_PUBLIC_RESEARCH_TOPIC || "general")
    
    // Mark as mounted to ensure hydration is complete
    setIsMounted(true)
  }, [])

  useEffect(() => {
    // Skip redirects on mobile devices
    if (isMobile) return
    
    // If user already has a Prolific ID and session is completed, go to thank you page
    if (existingProlificId && status === "completed") {
      router.push("/thank-you")
      return
    }
    
    // If user already has a Prolific ID and session is in progress AND has a valid sessionId, go to interview page
    if (existingProlificId && status === "in_progress" && sessionId) {
      router.push("/interview")
      return
    }

    // If there's an existing Prolific ID, pre-fill the input
    if (existingProlificId) {
      setProlificId(existingProlificId)
    }
  }, [existingProlificId, router, status, isMobile, sessionId])

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
      // Clear any previous errors
      setError("")
      
      // Validate input
      const validationResult = prolificSchema.safeParse({ id: prolificId })
      
      if (!validationResult.success) {
        setError(validationResult.error.errors[0].message)
        return
      }
      
      setIsLoading(true)
      console.log("Starting form submission...")
      
      // IMPORTANT: First set the Prolific ID in the store
      // This ensures SessionCheck won't redirect back to home
      setStoreProlificId(prolificId)
      console.log("Set Prolific ID in store:", prolificId)
      
      // Ensure store is updated before proceeding
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Use SyncService to create a new session with the prolific ID
      console.log("Creating new session...")
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
        console.log("Current store state:", {
          sessionId: state.sessionId,
          qaPairsLength: state.qaPairs.length,
          status: state.status
        })
        
        if (state.qaPairs.length === 0) {
          console.log("Waiting for questions to load...")
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
        
        // Only redirect after we confirm we have a valid session ID and data
        console.log("All checks passed, redirecting to interview page")
        router.push("/interview")
      } else {
        console.error("Failed to create session properly", result)
        setError("Failed to create session. Please try again.")
        setIsLoading(false)
      }
    } catch (err) {
      console.error("Error in form submission:", err)
      setError(err instanceof Error ? err.message : "An unexpected error occurred")
      setIsLoading(false)
    }
  }

  // If not mounted or on mobile, show appropriate content
  if (!isMounted) {
    return (
      <main className="relative min-h-screen overflow-hidden">
        <div className="absolute inset-0 z-0 bg-[#f5f2eb]">
          <GridBackground />
        </div>
        
        <div className="container relative z-10 mx-auto px-4 py-24 flex flex-col items-center justify-center min-h-screen">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-5xl md:text-6xl font-light mb-4 tracking-tight">
              Trace Your <span className="font-normal text-blue-600">Thinking</span>
            </h1>
            
            <p className="text-lg md:text-xl text-gray-600 mb-12 max-w-xl mx-auto leading-relaxed">
              We're building a map of public reasoning — your perspective matters.
            </p>
            
            <div className="bg-white p-8 rounded-3xl shadow-subtle max-w-md mx-auto border border-[#e0ddd5] flex items-center justify-center">
              <div className="flex flex-col items-center justify-center py-8">
                <div className="w-8 h-8 border-t-2 border-b-2 border-[#333333] rounded-full animate-spin mb-4"></div>
                <p className="text-[#333333] text-lg font-light">Loading application...</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    )
  }
  
  if (isMobile) {
    return <MobileRedirect />
  }

  // Desktop view
  return (
    <main className="relative min-h-screen overflow-hidden">
      {/* Debug Panel - Only shown when debug UI is enabled via environment variable */}
      {process.env.NEXT_PUBLIC_DEBUG_UI === 'true' && (
        <DebugPanel data={{
          researchTopic,
          isMounted,
          existingProlificId: existingProlificId || 'none',
          status: status || 'none',
        }} />
      )}
      
      {/* Grid Background */}
      <div className="absolute inset-0 z-0 bg-[#f5f2eb]">
        <GridBackground />
      </div>

      {/* Content */}
      <div 
        className="container relative z-10 mx-auto px-4 py-24 flex flex-col items-center justify-center min-h-screen"
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="text-center max-w-3xl mx-auto"
        >
          <h1 className="text-5xl md:text-6xl font-light mb-4 tracking-tight">
            Trace Your <span className="font-normal text-blue-600">Thinking</span>
            {researchTopic && researchTopic !== "general" && (
              <span className="font-light block text-2xl md:text-3xl mt-2 text-gray-700">
                {researchTopic.charAt(0).toUpperCase() + researchTopic.slice(1)} Research
              </span>
            )}
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

              <motion.div 
                whileTap={{ scale: 0.96 }} 
                transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
              >
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

      {/* Footer */}
      <Footer showAboutLink={true} />
    </main>
  )
}
