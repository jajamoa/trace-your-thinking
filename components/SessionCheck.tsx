"use client"

import { useEffect, useRef } from "react"
import { usePathname, useRouter } from "next/navigation"
import { useStore } from "@/lib/store"

/**
 * Global session state checker component
 * Responsible for:
 * 1. Checking session status on each page load
 * 2. Redirecting users based on session state
 * 3. Ensuring session status is the primary determining factor for page routing
 * 4. Resetting state and redirecting to home if session not found on server (404)
 */
export default function SessionCheck() {
  const router = useRouter()
  const pathname = usePathname()
  const { prolificId, sessionStatus, sessionId, checkSessionStatus } = useStore()
  
  // Add a pending check reference to avoid checking too frequently
  const isCheckPendingRef = useRef(false)
  // Add last checked time to throttle check frequency
  const lastCheckedTimeRef = useRef(0)
  // Track if we've already redirected to avoid double redirects
  const hasRedirectedRef = useRef(false)
  // Track last session ID to detect changes
  const lastSessionIdRef = useRef(sessionId)
  
  // Only redirect if we haven't already redirected in this render cycle
  const safeRedirect = (path: string) => {
    if (!hasRedirectedRef.current && pathname !== path) {
      console.log(`Redirecting from ${pathname} to ${path}`)
      hasRedirectedRef.current = true
      router.push(path)
    }
  }

  useEffect(() => {
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
      if (prolificId && sessionStatus === "in_progress" && sessionId) {
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
        // Delay status check for new sessions to avoid race conditions
        const isNewSession = sessionId.includes(`_${Date.now().toString().substring(0, 7)}`)
        
        if (isNewSession) {
          console.log("New session detected, delaying status check")
          setTimeout(safeCheckSessionStatus, 5000)
        } else {
          safeCheckSessionStatus()
        }
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
    if (sessionStatus === "completed") {
      // If session is completed but user is not on thank-you page, redirect there
      if (pathname !== "/thank-you") {
        console.log("Session completed, redirecting to thank you page")
        safeRedirect("/thank-you")
      }
    }

    // Only set up periodic checks for paths that need them
    if (!isCheckPendingRef.current && sessionId) {
      const checkDelay = Math.random() * 5000 + 15000 // Random delay between 15-20s
      const timeoutId = setTimeout(() => {
        safeCheckSessionStatus()
      }, checkDelay)
      
      // Clear timeout on unmount
      return () => clearTimeout(timeoutId)
    }
  }, [pathname, prolificId, router, sessionStatus, sessionId, checkSessionStatus])

  // This component doesn't render anything visible
  return null
} 