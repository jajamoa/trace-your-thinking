"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useRouter } from "next/navigation"
import { ArrowRight, AlertCircle, MessageCircle, Sparkles, Smile, Check, ShieldCheck, LoaderCircle } from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import DreamBrand from "@/components/DreamBrand"
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

  if (isMounted && isMobile) return <MobileRedirect />

  return (
    <main className="dream-page dream-home">
      <a href="#welcome" className="dream-skip">Skip to sign in</a>
      {process.env.NEXT_PUBLIC_DEBUG_UI === "true" && (
        <DebugPanel data={{ researchTopic, isMounted, status }} />
      )}
      <header className="dream-nav">
        <DreamBrand />
        <Link href="/about" className="dream-about">About the study <ArrowRight size={16} aria-hidden="true" /></Link>
      </header>

      <div className="dream-home-content">
        <section className="dream-intro" aria-labelledby="home-title">
          <div className="dream-eyebrow"><Sparkles size={15} aria-hidden="true" /> BIG IDEAS START WITH YOU</div>
          <h1 id="home-title">A little conversation.<br /><span>A world of perspectives.</span></h1>
          <p>Everyone sees the world a little differently.<br />Let’s discover what makes your thinking, yours.</p>
          {researchTopic && researchTopic !== "general" && (
            <span className="dream-topic">{researchTopic.charAt(0).toUpperCase() + researchTopic.slice(1)} Research</span>
          )}
        </section>

        <div className="dream-main-grid">
          <div className="dream-world">
            <div className="dream-photo">
              <Image src="/images/thinking-neighborhood.jpg" alt="Three cheerful neighbors sharing ideas in a colorful seaside town" width={1536} height={1024} priority sizes="(max-width: 900px) 90vw, 650px" />
              <div className="dream-photo-caption"><span className="dream-live-dot" /> A place for every perspective</div>
            </div>
            <div className="dream-sticker"><MessageCircle size={20} aria-hidden="true" /><span>Your voice belongs here.</span></div>
          </div>

          <section id="welcome" className="dream-welcome" aria-labelledby="welcome-title">
            <div className="dream-card-tab"><Smile size={17} aria-hidden="true" /> NICE TO MEET YOU!</div>
            <div className="dream-welcome-icon" aria-hidden="true"><MessageCircle size={30} strokeWidth={2.5} /><span>✦</span></div>
            <h2 id="welcome-title">Come on in.</h2>
            <p className="dream-card-description">Your perspective is the missing piece.<br />Ready to share a little of your world?</p>
            <form onSubmit={handleSubmit} className="dream-form" aria-busy={isLoading}>
              <label htmlFor="prolificId">Your Prolific ID</label>
              <Input id="prolificId" type="text" value={prolificId} onChange={(e) => validateInput(e.target.value)} placeholder="Enter your participant ID" className="dream-input" minLength={4} maxLength={24} required autoComplete="off" spellCheck={false} aria-invalid={!!error} aria-describedby={error ? "prolific-error" : "prolific-hint"} disabled={isLoading} />
              {error ? (
                <p id="prolific-error" role="alert" className="dream-error"><AlertCircle size={16} aria-hidden="true" />{error}</p>
              ) : <p id="prolific-hint" className="dream-input-hint">You’ll find this in your Prolific account.</p>}
              <Button type="submit" disabled={!isMounted || prolificId.length < 4 || isLoading} className="dream-button dream-begin">
                {!isMounted ? "Getting ready…" : isLoading ? "Creating your session…" : "Let’s get started"}
                {isLoading || !isMounted ? <LoaderCircle className="animate-spin" size={20} aria-hidden="true" /> : <ArrowRight size={20} aria-hidden="true" />}
              </Button>
            </form>
            <div className="dream-privacy"><ShieldCheck size={16} aria-hidden="true" /> Your responses are confidential.</div>
          </section>
        </div>

        <section className="dream-steps" aria-label="How the study works">
          <div><span className="dream-step-icon step-blue"><MessageCircle size={21} aria-hidden="true" /></span><div><h3>A friendly conversation</h3><p>Share your thoughts, in your own words.</p></div></div>
          <div><span className="dream-step-icon step-yellow"><Smile size={21} aria-hidden="true" /></span><div><h3>Simply be yourself</h3><p>We’re interested in your point of view.</p></div></div>
          <div><span className="dream-step-icon step-green"><Check size={21} aria-hidden="true" /></span><div><h3>Make it yours</h3><p>Review your answers before submitting.</p></div></div>
        </section>
      </div>
      <Footer />
    </main>
  )
}
