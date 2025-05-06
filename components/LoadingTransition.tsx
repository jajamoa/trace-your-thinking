"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"

interface LoadingTransitionProps {
  message?: string
}

export default function LoadingTransition({ message = "Preparing your data..." }: LoadingTransitionProps) {
  const [dots, setDots] = useState(".")
  
  // Animate the dots for a loading effect
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(currentDots => {
        if (currentDots.length >= 3) return "."
        return currentDots + "."
      })
    }, 500)
    
    return () => clearInterval(interval)
  }, [])
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#f5f2eb]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        className="text-center"
      >
        <div className="flex flex-col items-center justify-center space-y-6">
          {/* Loading spinner */}
          <div className="relative h-16 w-16">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
              className="absolute inset-0 rounded-full border-4 border-gray-200 border-t-gray-800"
            />
          </div>
          
          {/* Loading message */}
          <div className="text-xl font-light tracking-wide text-gray-700">
            {message}
            <span className="inline-block w-8 text-left">{dots}</span>
          </div>
        </div>
      </motion.div>
    </div>
  )
} 