"use client"

import { useEffect, useRef, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { useStore } from "@/lib/store"
import { QAPair } from "@/lib/store"

/**
 * Global session state checker component
 * Responsible for:
 * 1. Checking session status on each page load
 * 2. Redirecting users based on session state
 * 3. Ensuring session status is the primary determining factor for page routing
 * 4. Resetting state and redirecting to home if session not found on server (404)
 * 5. Detecting if session was reset on the server and syncing local state accordingly
 */
export default function SessionCheck() {
  const router = useRouter()
  const pathname = usePathname()
  const { prolificId, status, sessionId, checkSessionStatus, qaPairs, messages } = useStore()
  
  // Add a pending check reference to avoid checking too frequently
  const isCheckPendingRef = useRef(false)
  // Add last checked time to throttle check frequency
  const lastCheckedTimeRef = useRef(0)
  // Track if we've already redirected to avoid double redirects
  const hasRedirectedRef = useRef(false)
  // Track last session ID to detect changes
  const lastSessionIdRef = useRef(sessionId)
  // Track lastUpdated timestamp to detect session resets
  const [lastKnownUpdated, setLastKnownUpdated] = useState<number>(0)
  
  // Only redirect if we haven't already redirected in this render cycle
  const safeRedirect = (path: string) => {
    if (!hasRedirectedRef.current && pathname !== path) {
      console.log(`Redirecting from ${pathname} to ${path}`)
      hasRedirectedRef.current = true
      router.push(path)
    }
  }
  
  // Track the latest QA timestamps on first load and when they change
  useEffect(() => {
    if (qaPairs && qaPairs.length > 0) {
      // Find the latest timestamp among all QA pairs
      const latestTimestamp = qaPairs.reduce((latest, qa) => {
        const qaTimestamp = qa.lastUpdated || 0
        return qaTimestamp > latest ? qaTimestamp : latest
      }, 0)
      
      // Only update if we have a newer timestamp
      if (latestTimestamp > lastKnownUpdated) {
        setLastKnownUpdated(latestTimestamp)
        console.log(`Updated lastKnownUpdated to ${new Date(latestTimestamp).toISOString()}`)
      }
    }
  }, [qaPairs, lastKnownUpdated])

  // Function to detect server resets
  const checkForServerReset = async () => {
    if (!sessionId) return false
    
    try {
      // Fetch the latest session data directly from the server
      const response = await fetch(`/api/sessions/${sessionId}`)
      if (!response.ok) return false
      
      const data = await response.json()
      if (!data.success || !data.session) return false
      
      // Verify sessionId matches and session belongs to this user
      if (data.session.id !== sessionId || (prolificId && data.session.prolificId !== prolificId)) {
        console.warn('Session data mismatch - possible security issue', {
          expectedSessionId: sessionId,
          actualSessionId: data.session.id,
          expectedProlificId: prolificId,
          actualProlificId: data.session.prolificId
        })
        return false
      }
      
      const serverQAPairs = data.session.qaPairs || [] as QAPair[]
      
      // Case 1: Session was reset - all answers are now empty
      const allAnswersEmpty = serverQAPairs.every((qa: QAPair) => !qa.answer || qa.answer.trim() === '')
      
      // Case 2: Messages were cleared - fewer messages on server
      const serverMessages = data.session.messages || []
      const localMessages = messages || []
      
      // Case 3: If any QA on server has a newer timestamp than our "lastKnownUpdated"
      let hasNewerTimestamp = false
      let latestServerTimestamp = 0
      
      for (const qa of serverQAPairs as QAPair[]) {
        const serverTimestamp = qa.lastUpdated || 0
        latestServerTimestamp = Math.max(latestServerTimestamp, serverTimestamp)
        
        // If server has a newer timestamp but empty answer, this likely indicates a reset
        if (serverTimestamp > lastKnownUpdated && (!qa.answer || qa.answer.trim() === '')) {
          hasNewerTimestamp = true
        }
      }
      
      const wasReset = allAnswersEmpty || (hasNewerTimestamp && latestServerTimestamp > lastKnownUpdated)
      
      if (wasReset) {
        console.log('Detected session reset on server:', {
          allAnswersEmpty,
          hasNewerTimestamp,
          latestServerTimestamp,
          lastKnownUpdated
        })
        
        // Use the server state to replace local state
        window.location.reload()
        return true
      }
      
      return false
    } catch (error) {
      console.error('Error checking for server reset:', error)
      return false
    }
  }

  useEffect(() => {
    // Skip all session checks for admin paths
    if (pathname.startsWith('/admin') || pathname.startsWith('/api/admin')) {
      return
    }
    
    console.log(`SessionCheck running for path: ${pathname}, sessionId: ${sessionId}, prolificId: ${prolificId}`)
    
    // Reset the redirect flag when dependencies change
    hasRedirectedRef.current = false
    
    // Reset throttle if session ID changes
    if (lastSessionIdRef.current !== sessionId) {
      console.log(`Session ID changed from ${lastSessionIdRef.current} to ${sessionId}`)
      lastSessionIdRef.current = sessionId
      lastCheckedTimeRef.current = 0
    }
    
    // Define function to check session status safely
    const safeCheckSessionStatus = async () => {
      // Avoid multiple concurrent checks
      if (isCheckPendingRef.current) {
        console.log("Status check already in progress, skipping")
        return
      }
      
      // Only check once every 10 seconds at most
      const now = Date.now()
      if (now - lastCheckedTimeRef.current < 10000) {
        console.log("Status check throttled, too soon since last check")
        return
      }
      
      try {
        console.log("Starting safe session status check")
        isCheckPendingRef.current = true
        lastCheckedTimeRef.current = now
        
        // First check if the session was reset on the server
        const wasReset = await checkForServerReset()
        if (wasReset) {
          console.log("Session was reset on server, local state will be refreshed")
          return // The page will reload, so no need to continue
        }
        
        // Only check if we have a sessionId
        if (sessionId) {
          await checkSessionStatus()
        }
      } finally {
        isCheckPendingRef.current = false
      }
    }

    // Skip for these paths which handle their own session logic
    const ignorePaths = ["/thank-you", "/about"]
    if (ignorePaths.includes(pathname)) {
      return
    }
    
    // Special handling for home/landing page - we never redirect FROM the home page,
    // but we do redirect TO it when needed
    if (pathname === "/") {
      // If user has prolificId AND session is in progress AND there's a valid sessionId,
      // only then redirect to interview
      if (prolificId && status === "in_progress" && sessionId) {
        console.log("Home page: session in progress, redirecting to interview")
        safeRedirect("/interview")
      }
      // Otherwise, let the landing page handle its logic
      return
    }
    
    // For the interview page specifically, we need special handling:
    // 1. Allow the page to create a session if one doesn't exist yet
    // 2. Only check status of existing sessions
    if (pathname === "/interview") {
      // If we have a session ID, just check its status without redirecting
      if (sessionId) {
        // We'll no longer rely on detecting new sessions based on current timestamp
        // which causes hydration mismatches
        
        // Instead we'll use a more reliable approach: new sessions always get an immediate check
        console.log("On interview page with session, performing immediate status check")
        safeCheckSessionStatus()
      }
      
      // If we don't have a prolificId but we're on the interview page, something's wrong
      if (!prolificId) {
        console.log("Interview page: no prolificId, redirecting to landing")
        safeRedirect("/")
      }
      
      // Otherwise, let the interview page handle its business
      return
    }
    
    // For other pages, check if prolificId exists
    if (!prolificId) {
      console.log("No Prolific ID found, redirecting to landing page")
      safeRedirect("/")
      return
    }

    // Session status based redirection for other pages
    if (status === "completed") {
      // If session is completed but user is not on thank-you page, redirect there
      if (pathname !== "/thank-you") {
        console.log("Session completed, redirecting to thank you page")
        safeRedirect("/thank-you")
      }
    }

    // Only set up periodic checks for paths that need them
    if (!isCheckPendingRef.current && sessionId) {
      // Use a fixed delay instead of random to avoid hydration mismatches
      const checkDelay = 15000 // Fixed delay of 15 seconds
      const timeoutId = setTimeout(() => {
        safeCheckSessionStatus()
      }, checkDelay)
      
      // Clear timeout on unmount
      return () => clearTimeout(timeoutId)
    }
  }, [pathname, prolificId, router, status, sessionId, checkSessionStatus, messages, lastKnownUpdated])

  // This component doesn't render anything visible
  return null
} 