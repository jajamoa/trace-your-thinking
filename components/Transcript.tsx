"use client"

import { motion } from "framer-motion"
import { useStore } from "@/lib/store"

export default function Transcript() {
  const { messages } = useStore()

  // Filter out only the text content for the transcript
  const transcriptMessages = messages.map((message) => ({
    role: message.role,
    text: message.text,
  }))

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
      aria-live="polite"
    >
      <h3 className="text-sm font-medium text-gray-400">Transcript</h3>

      <div className="font-mono text-xs space-y-3 overflow-y-auto max-h-[calc(100vh-250px)]">
        {transcriptMessages.map((message, index) => (
          <div key={index} className="space-y-1">
            <div className={`font-semibold ${message.role === "bot" ? "text-blue-400" : "text-white"}`}>
              {message.role === "bot" ? "Interviewer" : "You"}:
            </div>
            <div className="text-gray-300 break-words whitespace-pre-wrap">{message.text || "..."}</div>
          </div>
        ))}

        {transcriptMessages.length === 0 && (
          <div className="text-gray-500 italic">
            No transcript available yet. Start the interview to see the conversation.
          </div>
        )}
      </div>
    </motion.div>
  )
}
