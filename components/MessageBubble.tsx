"use client"

import { useEffect, useState, useRef } from "react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface MessageBubbleProps {
  role: "user" | "bot"
  text: string
  loading?: boolean
  isLatestMessage?: boolean
}

export default function MessageBubble({ 
  role, 
  text, 
  loading = false,
  isLatestMessage = false 
}: MessageBubbleProps) {
  const [displayText, setDisplayText] = useState("")
  const [showCursor, setShowCursor] = useState(loading && isLatestMessage)
  const [isTyping, setIsTyping] = useState(false)
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const typingIndexRef = useRef(0)
  
  // Clear any existing typing animation
  const clearTypingAnimation = () => {
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
      typingTimeoutRef.current = null
    }
  }
  
  // Implement typewriter effect
  const typeText = (fullText: string, startIndex = 0) => {
    // Initialize
    typingIndexRef.current = startIndex
    setIsTyping(true)
    setShowCursor(true)
    
    const typeNextChar = () => {
      if (typingIndexRef.current < fullText.length) {
        setDisplayText(fullText.substring(0, typingIndexRef.current + 1))
        typingIndexRef.current++
        // Faster typing: between 5-20ms for quicker animation
        const typingSpeed = Math.floor(Math.random() * 0.5) + 2
        typingTimeoutRef.current = setTimeout(typeNextChar, typingSpeed)
      } else {
        setIsTyping(false)
        // Keep cursor visible after typing finishes
        setShowCursor(true)
      }
    }
    
    // Start typing
    typeNextChar()
  }

  // Handle typing animation for bot messages
  useEffect(() => {
    // If message is not the latest bot message, always show full text
    if (!isLatestMessage) {
      clearTypingAnimation()
      setDisplayText(text)
      setShowCursor(false)
      setIsTyping(false)
      return;
    }
    
    // Only proceed with typewriter logic for the latest bot message
    if (role === "bot") {
      if (loading) {
        // When loading, show cursor with minimal or empty text
        clearTypingAnimation()
        setShowCursor(true)
        setIsTyping(false)
        setDisplayText("")
      } else if (text && text !== displayText) {
        // When text changes and is not loading, start typing animation
        clearTypingAnimation()
        setShowCursor(true) // Ensure cursor is showing during typing prep
        
        // Small delay before starting typing animation
        setTimeout(() => {
          // If we already have some text showing, only type the new part
          if (displayText && text.startsWith(displayText)) {
            typeText(text, displayText.length)
          } else {
            // Otherwise start from beginning
            setDisplayText("")
            typeText(text)
          }
        }, 20) // Reduced from 100ms to 50ms for faster start
      }
    } else {
      // For user messages, no animation
      setDisplayText(text)
    }
    
    // Clean up on unmount
    return () => {
      clearTypingAnimation()
    }
  }, [role, text, loading, displayText, isLatestMessage])

  return (
    <div className={cn("flex", role === "user" ? "justify-end" : "justify-start")}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
        className={cn(
          "max-w-[80%] rounded-2xl px-5 py-4 shadow-subtle font-light",
          role === "user" ? "bg-[#333333] text-white" : "bg-white border border-[#e0ddd5] text-[#333333]",
        )}
      >
        <p className="whitespace-pre-wrap break-words leading-relaxed">
          {displayText}
          {(showCursor || isTyping) && role === "bot" && isLatestMessage && (
            <span className="inline-block w-2 h-4 bg-black/70 ml-1 animate-pulse" />
          )}
        </p>
      </motion.div>
    </div>
  )
}
