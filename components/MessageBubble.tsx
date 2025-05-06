"use client"

import { useEffect, useState } from "react"
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
  const [displayText, setDisplayText] = useState(text)
  const [showCursor, setShowCursor] = useState(loading && isLatestMessage)

  // Handle typing animation for bot messages
  useEffect(() => {
    // If message is not the latest bot message, always hide cursor
    if (!isLatestMessage) {
      setShowCursor(false)
      return;
    }
    
    // Only proceed with cursor logic for the latest bot message
    if (role === "bot") {
      if (loading) {
        setShowCursor(true)
        setDisplayText(text)
      } else if (text !== displayText) {
        setDisplayText(text)
        setShowCursor(false)
      }
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
          {showCursor && <span className="inline-block w-2 h-4 bg-black/70 ml-1 animate-pulse" />}
        </p>
      </motion.div>
    </div>
  )
}
