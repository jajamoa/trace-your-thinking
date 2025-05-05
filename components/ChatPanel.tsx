"use client"

import { useRef, useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import MessageBubble from "@/components/MessageBubble"
import { useStore } from "@/lib/store"
import { Button } from "@/components/ui/button"
import { Edit2 } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"

export default function ChatPanel() {
  const { messages, updateMessage } = useStore()
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

  const handleEditStart = (message: (typeof messages)[0]) => {
    setEditingMessageId(message.id)
    setEditText(message.text)
  }

  const handleEditSave = () => {
    if (editingMessageId && editText.trim()) {
      updateMessage(editingMessageId, (prev) => ({
        ...prev,
        text: editText.trim(),
      }))
      setEditingMessageId(null)
      setEditText("")
    }
  }

  const handleEditCancel = () => {
    setEditingMessageId(null)
    setEditText("")
  }

  return (
    <div className="flex flex-col p-4 gap-4 max-w-4xl mx-auto">
      <AnimatePresence initial={false}>
        {messages.map((message) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="relative group"
          >
            {editingMessageId === message.id ? (
              <div className="flex flex-col gap-2">
                <Textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="min-h-[100px] bg-white border-[#e0ddd5] rounded-xl focus:ring-blue-400 resize-none font-light"
                  autoFocus
                />
                <div className="flex justify-end gap-2">
                  <Button
                    onClick={handleEditCancel}
                    variant="outline"
                    size="sm"
                    className="border-[#e0ddd5] text-[#333333] rounded-full hover:bg-[#e0ddd5]"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleEditSave}
                    size="sm"
                    className="bg-[#333333] hover:bg-[#222222] text-white rounded-full"
                  >
                    Save
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <MessageBubble role={message.role} text={message.text} loading={message.loading} />

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
