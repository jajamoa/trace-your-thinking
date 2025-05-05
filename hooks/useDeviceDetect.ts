"use client"

import { useState, useEffect } from 'react'

export default function useDeviceDetect() {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkDevice = () => {
      const userAgent = 
        typeof window.navigator === "undefined" ? "" : navigator.userAgent
      const mobile = Boolean(
        userAgent.match(
          /Android|BlackBerry|iPhone|iPad|iPod|Opera Mini|IEMobile|WPDesktop/i
        )
      )
      setIsMobile(mobile)
    }

    checkDevice()
    window.addEventListener("resize", checkDevice)
    
    return () => window.removeEventListener("resize", checkDevice)
  }, [])

  return { isMobile }
} 