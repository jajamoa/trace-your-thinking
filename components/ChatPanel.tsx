"use client"

import { useRef, useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import MessageBubble from "@/components/MessageBubble"
import { useStore } from "@/lib/store"
import { Button } from "@/components/ui/button"
import { Edit2 } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { SyncService } from "@/lib/sync-service"

export default function ChatPanel() {
  const { messages, updateMessage, updateQAPair, qaPairs } = useStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editText, setEditText] = useState("")

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  // Get the last user message
  const lastUserMessage = [...messages].reverse().find((m) => m.role === "user")
  
  // Find the last bot message that is still loading (if any)
  const lastLoadingBotMessage = [...messages].reverse().find(
    (m) => m.role === "bot" && m.loading === true
  )
  
  // If there's a loading bot message, it's the latest one to show cursor
  // Otherwise, find the most recent bot message
  const lastBotMessageId = lastLoadingBotMessage 
    ? lastLoadingBotMessage.id 
    : [...messages].reverse().find((m) => m.role === "bot")?.id

  // When editing a user message, we need to also update the corresponding QA pair
  const handleEditStart = (message: (typeof messages)[0]) => {
    if (message.role !== "user") return
    setEditingMessageId(message.id)
    setEditText(message.text)
  }

  const handleEditSave = () => {
    if (editingMessageId && editText.trim()) {
      // Update the message
      updateMessage(editingMessageId, (prev) => ({
        ...prev,
        text: editText.trim(),
      }))

      // Find the related QA pair for this user message
      if (lastUserMessage) {
        // Find the bot message that came before this user message
        const messageIndex = messages.findIndex(m => m.id === editingMessageId)
        if (messageIndex > 0) {
          const previousMessages = messages.slice(0, messageIndex)
          const lastBotMessage = [...previousMessages].reverse().find(m => m.role === "bot")
          
          if (lastBotMessage) {
            // Find a QA pair with this question
            const relatedQAPair = qaPairs.find(qa => qa.question === lastBotMessage.text)
            if (relatedQAPair) {
              // Update the answer in the QA pair
              updateQAPair(relatedQAPair.id, { answer: editText.trim() })
            }
          }
        }
      }
      
      setEditingMessageId(null)
      setEditText("")
    }
  }

  const handleEditCancel = () => {
    setEditingMessageId(null)
    setEditText("")
  }

  return (
    <div className="flex flex-col space-y-6 py-4 px-2 overflow-y-auto max-h-[calc(100vh-15rem)]">
      <AnimatePresence>
        {messages.map((message) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={`relative group ${
              message.role === "user" ? "items-end" : "items-start"
            }`}
          >
            {editingMessageId === message.id ? (
              <div className="flex flex-col space-y-2 w-full max-w-[80%] ml-auto">
                <Textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="min-h-[100px] p-3 focus:ring-1 focus:ring-gray-400"
                  autoFocus
                />
                <div className="flex justify-end space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleEditCancel}
                    className="text-xs"
                  >
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleEditSave} className="text-xs">
                    Save
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <MessageBubble 
                  role={message.role} 
                  text={message.text} 
                  loading={message.loading} 
                  isLatestMessage={message.role === "bot" && message.id === lastBotMessageId}
                />

                {/* Edit button for the last user message */}
                {message.role === "user" && message.id === lastUserMessage?.id && !editingMessageId && (
                  <Button
                    onClick={() => handleEditStart(message)}
                    size="icon"
                    variant="ghost"
                    className="absolute top-0 right-0 h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Edit message"
                  >
                    <Edit2 className="h-4 w-4" />
                  </Button>
                )}
              </>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
      <div ref={messagesEndRef} />
    </div>
  )
}
