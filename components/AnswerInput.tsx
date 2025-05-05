"use client"

import { useState, useRef, useEffect } from "react"
import { motion } from "framer-motion"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Send, Mic, MicOff, MessageSquare, X } from "lucide-react"
import { useStore } from "@/lib/store"
import { sendAudioToWhisperAPI } from "@/lib/whisper"
import { toast } from "@/components/ui/use-toast"

interface AnswerInputProps {
  onSendMessage: (text: string) => void
}

export default function AnswerInput({ onSendMessage }: AnswerInputProps) {
  const [text, setText] = useState("")
  const [inputMode, setInputMode] = useState<"voice" | "text">("voice")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { isRecording, setIsRecording } = useStore()
  const [isTranscribing, setIsTranscribing] = useState(false)

  // References for audio recording
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [text])

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + Enter to send
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        if (text.trim() && !isRecording && inputMode === "text") {
          handleSend()
        }
        e.preventDefault()
      }

      // Escape to cancel recording or clear text
      if (e.key === "Escape") {
        if (isRecording) {
          stopRecording(true) // Cancel recording
        } else if (text && inputMode === "text") {
          setText("")
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [text, isRecording, inputMode])

  // Start recording automatically when in voice mode
  useEffect(() => {
    if (inputMode === "voice" && !isRecording) {
      startRecording()
    }
  }, [inputMode, isRecording])

  // Clean up recording when component unmounts
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop()
      }
    }
  }, [isRecording])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // Only process if we have audio data and we're not cancelling
        if (audioChunksRef.current.length > 0 && !isTranscribing) {
          processAudio()
        }

        // Stop all audio tracks
        stream.getTracks().forEach((track) => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error("Error starting recording:", error)
      toast({
        title: "Microphone Error",
        description: "Could not access your microphone. Please check permissions.",
        variant: "destructive",
      })
      setInputMode("text")
    }
  }

  const stopRecording = (cancel = false) => {
    if (mediaRecorderRef.current && isRecording) {
      if (cancel) {
        setIsTranscribing(false) // Make sure we don't process on cancel
      } else {
        setIsTranscribing(true) // We're going to process this audio
      }

      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const processAudio = async () => {
    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" })

      // Show transcribing indicator
      setIsTranscribing(true)

      // Send to Whisper API
      const result = await sendAudioToWhisperAPI(audioBlob)

      // Update text with transcription
      setText(result.text)

      // Hide transcribing indicator
      setIsTranscribing(false)

      // Auto-send if we have text
      if (result.text.trim()) {
        onSendMessage(result.text.trim())
        setText("")
      }
    } catch (error) {
      console.error("Error processing audio:", error)
      setIsTranscribing(false)
      toast({
        title: "Transcription Error",
        description: "Could not transcribe your audio. Please try again or switch to text input.",
        variant: "destructive",
      })
    }
  }

  const handleSend = () => {
    if (text.trim()) {
      onSendMessage(text.trim())
      setText("")
    }
  }

  const toggleRecording = () => {
    if (inputMode === "voice") {
      if (isRecording) {
        stopRecording()
      } else {
        startRecording()
      }
    }
  }

  const toggleInputMode = () => {
    const newMode = inputMode === "voice" ? "text" : "voice"
    setInputMode(newMode)

    if (newMode === "voice") {
      setText("")
    } else {
      if (isRecording) {
        stopRecording(true) // Cancel recording when switching to text
      }
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      className="sticky bottom-0 border-t border-[#e0ddd5] bg-[#f5f2eb]/80 backdrop-blur-lg p-4"
    >
      <div className="flex gap-2 max-w-4xl mx-auto">
        {inputMode === "voice" ? (
          <>
            <motion.div whileTap={{ scale: 0.96 }} className="flex-shrink-0">
              <Button
                type="button"
                size="icon"
                variant={isRecording ? "destructive" : "outline"}
                onClick={toggleRecording}
                className="h-10 w-10 rounded-full border-[#e0ddd5]"
                aria-label={isRecording ? "Stop recording" : "Start recording"}
                disabled={isTranscribing}
              >
                {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
              </Button>
            </motion.div>

            <div className="flex-1 flex items-center justify-center">
              <div className="text-sm text-gray-600 font-light">
                {isTranscribing
                  ? "Transcribing your speech..."
                  : isRecording
                    ? "Listening..."
                    : "Click the microphone to start speaking"}
              </div>
            </div>

            <motion.div whileTap={{ scale: 0.96 }} className="flex-shrink-0">
              <Button
                type="button"
                size="icon"
                onClick={toggleInputMode}
                className="h-10 w-10 rounded-full bg-[#e0ddd5] hover:bg-[#d5d2ca] text-[#333333]"
                aria-label="Switch to text input"
                disabled={isTranscribing}
              >
                <MessageSquare className="h-5 w-5" />
              </Button>
            </motion.div>
          </>
        ) : (
          <>
            <motion.div whileTap={{ scale: 0.96 }} className="flex-shrink-0">
              <Button
                type="button"
                size="icon"
                onClick={toggleInputMode}
                className="h-10 w-10 rounded-full bg-[#e0ddd5] hover:bg-[#d5d2ca] text-[#333333]"
                aria-label="Switch to voice input"
              >
                <Mic className="h-5 w-5" />
              </Button>
            </motion.div>

            <Textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type your answer..."
              className="min-h-10 resize-none bg-white border-[#e0ddd5] rounded-xl focus:ring-blue-400 font-light"
              aria-label="Answer input"
            />

            {text ? (
              <motion.div whileTap={{ scale: 0.96 }} className="flex-shrink-0">
                <Button
                  type="button"
                  size="icon"
                  onClick={() => setText("")}
                  className="h-10 w-10 rounded-full bg-[#e0ddd5] hover:bg-[#d5d2ca] text-[#333333]"
                  aria-label="Clear text"
                >
                  <X className="h-5 w-5" />
                </Button>
              </motion.div>
            ) : null}

            <motion.div whileTap={{ scale: 0.96 }} className="flex-shrink-0">
              <Button
                type="button"
                size="icon"
                onClick={handleSend}
                disabled={!text.trim()}
                className="h-10 w-10 rounded-full bg-[#333333] hover:bg-[#222222] text-white"
                aria-label="Send message"
              >
                <Send className="h-5 w-5" />
              </Button>
            </motion.div>
          </>
        )}
      </div>

      {inputMode === "text" && (
        <div className="text-xs text-gray-500 text-center mt-2 font-light">
          Press <kbd className="px-1 py-0.5 bg-[#e0ddd5] rounded">Ctrl</kbd> +{" "}
          <kbd className="px-1 py-0.5 bg-[#e0ddd5] rounded">Enter</kbd> to send
        </div>
      )}
    </motion.div>
  )
}
