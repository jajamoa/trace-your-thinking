"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { motion } from "framer-motion"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Send, Mic, MicOff, MessageSquare, X } from "lucide-react"
import { useStore } from "@/lib/store"
import { sendAudioToWhisperAPI } from "@/lib/whisper"
import { toast } from "@/components/ui/use-toast"

interface AnswerInputProps {
  onSendMessage: (text: string) => void
  isProcessing?: boolean
}

// Input mode preference key for localStorage
const INPUT_MODE_PREF_KEY = 'input-mode-preference'

export default function AnswerInput({ onSendMessage, isProcessing = false }: AnswerInputProps) {
  // Get the previous input mode preference, default to voice if none exists
  const getInitialInputMode = (): "voice" | "text" => {
    // Client-side only operation, always return default on server
    return "voice" // Default to voice input
  }

  const [text, setText] = useState("")
  const [inputMode, setInputMode] = useState<"voice" | "text">("voice") // 始终使用默认值
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { isRecording, setIsRecording, messages } = useStore()
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [autoStartRecording, setAutoStartRecording] = useState(false)
  const [waitingForQuestion, setWaitingForQuestion] = useState(false)
  
  // References for audio recording
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  // Add a ref to track whether to process the audio (rather than using state)
  const shouldProcessAudioRef = useRef(false)

  // Listen for forced cancellation from other components (like Review page)
  useEffect(() => {
    const handleForcedCancel = () => {
      console.log("AnswerInput received force-cancel-recording event");
      
      // Stop any active recording without processing
      if (mediaRecorderRef.current && isRecording) {
        console.log("Forcefully stopping recording due to external cancel event");
        shouldProcessAudioRef.current = false;
        audioChunksRef.current = [];
        
        try {
          mediaRecorderRef.current.stop();
        } catch (error) {
          console.error("Error stopping recorder:", error);
        }
      }
      
      // Reset all recording state
      shouldProcessAudioRef.current = false;
      audioChunksRef.current = [];
      setIsTranscribing(false);
      setIsRecording(false);
      setWaitingForQuestion(false);
    };
    
    // Add event listener
    window.addEventListener('force-cancel-recording', handleForcedCancel);
    
    // Clean up
    return () => {
      window.removeEventListener('force-cancel-recording', handleForcedCancel);
    };
  }, [isRecording, setIsRecording]);

  // Check if there is a loading bot message (question is still "typing")
  const isQuestionLoading = useMemo(() => {
    // Find the last bot message
    const lastBotMessage = [...messages].reverse().find(m => m.role === "bot");
    // Return true if it's loading
    return lastBotMessage?.loading || false;
  }, [messages]);

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
          stopRecording(true) // Process recording when using ESC to stop
        } else if (text && inputMode === "text") {
          setText("")
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [text, isRecording, inputMode])

  // Start recording automatically when in voice mode, but only after question is displayed
  useEffect(() => {
    // Don't start recording if question is still being typed
    if (isQuestionLoading) {
      setWaitingForQuestion(true);
      return;
    }
    
    // When question is done typing and we were waiting, start recording
    if (waitingForQuestion && !isQuestionLoading) {
      setWaitingForQuestion(false);
      // Use a slight delay to allow UI to render and user to see the question fully
      const timer = setTimeout(() => {
        if (inputMode === "voice" && !isRecording && autoStartRecording) {
          startRecording();
        }
      }, 800); // Longer delay to ensure user has time to read the question
      
      return () => clearTimeout(timer);
    }
    // Standard auto-start behavior
    else if (inputMode === "voice" && !isRecording && autoStartRecording && !isQuestionLoading) {
      const timer = setTimeout(() => {
        startRecording();
      }, 500); // Small delay to allow user to see the question
      
      return () => clearTimeout(timer);
    }
  }, [inputMode, isRecording, autoStartRecording, isQuestionLoading, waitingForQuestion]);

  // Clean up recording when component unmounts
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop()
      }
    }
  }, [isRecording])

  // 在客户端加载时从存储读取偏好设置
  useEffect(() => {
    // 仅在客户端运行时读取 localStorage
    if (typeof window !== 'undefined') {
      const savedMode = localStorage.getItem(INPUT_MODE_PREF_KEY)
      // 仅接受有效值
      if (savedMode === 'voice' || savedMode === 'text') {
        setInputMode(savedMode as "voice" | "text")
      }
    }
  }, [])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []
      // Set ref to true by default when starting recording
      shouldProcessAudioRef.current = true

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // Only process once - check and immediately set to false to prevent double processing
        const shouldProcess = shouldProcessAudioRef.current && audioChunksRef.current.length > 0;
        shouldProcessAudioRef.current = false;
        
        if (shouldProcess) {
          processAudio()
        } else {
          // Reset transcribing state
          setIsTranscribing(false)
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
      // Save the mode preference when changing due to error
      localStorage.setItem(INPUT_MODE_PREF_KEY, "text")
      setIsTranscribing(false) // Ensure we reset the transcribing state
    }
  }

  const stopRecording = (shouldProcess = true) => {
    if (mediaRecorderRef.current && isRecording) {
      // Set the ref directly - this is synchronous
      shouldProcessAudioRef.current = shouldProcess
      
      // Update UI state based on whether we'll process
      if (shouldProcess) {
        setIsTranscribing(true) // Will process audio
      } else {
        setIsTranscribing(false) // Won't process audio
      }

      mediaRecorderRef.current.stop()
      setIsRecording(false)
    } else {
      // Reset state even if recorder isn't active
      shouldProcessAudioRef.current = false
      setIsTranscribing(false)
      setIsRecording(false)
    }
  }

  const processAudio = async () => {
    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" })
      
      // Only proceed if we have actual audio data
      if (audioBlob.size <= 0) {
        setIsTranscribing(false)
        return
      }

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
        
        // After sending an answer, we don't auto-start recording again
        // User must manually start recording for the next question
        setAutoStartRecording(false)
      }
      
      // Ensure we don't process audio again until explicitly enabled
      shouldProcessAudioRef.current = false
      // Clear audio chunks after processing
      audioChunksRef.current = []
    } catch (error) {
      console.error("Error processing audio:", error)
      setIsTranscribing(false)
      shouldProcessAudioRef.current = false
      audioChunksRef.current = []
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
        // When stopping via mic button, we should process audio
        stopRecording(true)
      } else {
        // When user manually starts recording, we don't need autoStartRecording
        setAutoStartRecording(false)
        startRecording()
      }
    }
  }

  // Method for switching to text mode (cancel recording without transcribing)
  const cancelRecordingAndSwitchToText = () => {
    // When switching to text, we shouldn't process audio
    if (mediaRecorderRef.current && isRecording) {
      stopRecording(false)
    } else {
      // Even if not recording, clear any audio chunks and reset states
      audioChunksRef.current = []
      shouldProcessAudioRef.current = false
      setIsTranscribing(false)
    }
    
    // Switch mode and save preference
    setInputMode("text")
    localStorage.setItem(INPUT_MODE_PREF_KEY, "text")
  }

  const toggleInputMode = () => {
    if (inputMode === "voice") {
      // When switching from voice to text, cancel recording without transcribing
      cancelRecordingAndSwitchToText()
    } else {
      // When switching from text to voice
      setInputMode("voice")
      localStorage.setItem(INPUT_MODE_PREF_KEY, "voice")
      setText("")
      shouldProcessAudioRef.current = true
      setAutoStartRecording(true)
    }
  }

  // Function to be called when a new question appears
  useEffect(() => {
    // This effect should run whenever a new question appears
    // For this to work, the parent component should re-mount this component
    // or pass a key prop that changes with each new question
    
    // Only execute client-side setup code after component is mounted
    // This avoids hydration errors
    if (typeof window === 'undefined') return;
    
    // Reset audio state on mount
    audioChunksRef.current = []
    shouldProcessAudioRef.current = false
    
    // Only prepare recording automatically if current mode is voice
    if (inputMode === "voice") {
      setAutoStartRecording(true)
      // Initially set waiting state based on if the question is still being typed
      setWaitingForQuestion(isQuestionLoading)
    }
    
    return () => {
      // Cleanup when component unmounts or before re-running
      if (isRecording) {
        stopRecording(false) // Don't process when unmounting
      }
      // Extra cleanup
      shouldProcessAudioRef.current = false
      audioChunksRef.current = []
    }
  }, []); // Keep empty dependency array to avoid hydration mismatches

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      className="sticky bottom-0 border-t border-[#e0ddd5] bg-[#f5f2eb]/80 backdrop-blur-lg p-4 z-20"
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
                disabled={isTranscribing || isQuestionLoading || isProcessing}
              >
                {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
              </Button>
            </motion.div>

            <div className="flex-1 flex items-center justify-center h-10">
              <div className="text-sm text-gray-600 font-light">
                {isProcessing
                  ? "Processing your answer with AI..."
                  : isTranscribing
                    ? "Transcribing your speech..."
                    : isQuestionLoading
                      ? "Waiting for question..."
                      : isRecording
                        ? "Listening..."
                        : "Press microphone to start speaking"}
              </div>
            </div>

            <motion.div whileTap={{ scale: 0.96 }} className="flex-shrink-0">
              <Button
                type="button"
                size="icon"
                onClick={toggleInputMode}
                className="h-10 w-10 rounded-full bg-[#e0ddd5] hover:bg-[#d5d2ca] text-[#333333]"
                aria-label="Switch to text input"
                disabled={isTranscribing || isProcessing}
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
                disabled={isProcessing}
              >
                <Mic className="h-5 w-5" />
              </Button>
            </motion.div>

            <Textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={isProcessing ? "Processing your answer..." : "Type your answer..."}
              className="min-h-10 h-10 resize-none bg-white border-[#e0ddd5] rounded-xl focus:ring-blue-400 font-light"
              aria-label="Answer input"
              disabled={isProcessing}
            />

            {text ? (
              <motion.div whileTap={{ scale: 0.96 }} className="flex-shrink-0">
                <Button
                  type="button"
                  size="icon"
                  onClick={() => setText("")}
                  className="h-10 w-10 rounded-full bg-[#e0ddd5] hover:bg-[#d5d2ca] text-[#333333]"
                  aria-label="Clear text"
                  disabled={isProcessing}
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
                disabled={!text.trim() || isProcessing}
                className="h-10 w-10 rounded-full bg-[#333333] hover:bg-[#222222] text-white"
                aria-label="Send message"
              >
                <Send className="h-5 w-5" />
              </Button>
            </motion.div>
          </>
        )}
      </div>

      <div className="text-xs text-gray-500 text-center mt-2 font-light h-5">
        {!isProcessing && (
          <>
            {inputMode === "text" && (
              <>
                Press <kbd className="px-1 py-0.5 bg-[#e0ddd5] rounded">Ctrl</kbd> +{" "}
                <kbd className="px-1 py-0.5 bg-[#e0ddd5] rounded">Enter</kbd> to send •{" "}
                <kbd className="px-1 py-0.5 bg-[#e0ddd5] rounded">ESC</kbd> to clear text
              </>
            )}
            {inputMode === "voice" && !isTranscribing && (
              <>
                Press <kbd className="px-1 py-0.5 bg-[#e0ddd5] rounded">ESC</kbd> to {isRecording ? "stop recording" : "cancel"}
              </>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}
