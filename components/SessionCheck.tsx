"use client"

import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import { useStore } from "@/lib/store"

/**
 * Global session state checker component
 * Responsible for:
 * 1. Checking session status on each page load
 * 2. Redirecting users based on session state
 * 3. Ensuring session status is the primary determining factor for page routing
 */
export default function SessionCheck() {
  const router = useRouter()
  const pathname = usePathname()
  const { prolificId, sessionStatus, sessionId, checkSessionStatus } = useStore()

  useEffect(() => {
    // Skip for these paths which handle their own session logic
    const ignorePaths = ["/thank-you", "/about"]
    if (ignorePaths.includes(pathname)) {
      return
    }

    // If no prolificId, always redirect to landing page
    if (!prolificId) {
      console.log("No Prolific ID found, redirecting to landing page")
      router.push("/")
      return
    }

    // Session status based redirection
    if (sessionStatus === "completed") {
      // If session is completed but user is not on thank-you page, redirect there
      if (pathname !== "/thank-you") {
        console.log("Session completed, redirecting to thank you page")
        router.push("/thank-you")
      }
    } else if (sessionStatus === "in_progress") {
      // If session is in progress but user is on landing page, redirect to interview
      if (pathname === "/") {
        console.log("Session in progress, redirecting to interview page")
        router.push("/interview")
      }
    }

    // If we have a sessionId, periodically check the latest session status from the server
    if (sessionId) {
      // Check status immediately when the component mounts
      checkSessionStatus()
      
      // Set up interval for periodic checks (every 30 seconds)
      const intervalId = setInterval(() => {
        checkSessionStatus()
      }, 30000)
      
      // Clear interval on unmount
      return () => clearInterval(intervalId)
    }
  }, [pathname, prolificId, router, sessionStatus, sessionId, checkSessionStatus])

  // This component doesn't render anything visible
  return null
} 