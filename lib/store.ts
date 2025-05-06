"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import { SyncService } from "./sync-service"

export interface Message {
  id: string
  role: "user" | "bot"
  text: string
  loading?: boolean
}

export interface QAPair {
  id: string
  question: string
  answer: string
}

export interface Question {
  id: string
  text: string
  shortText: string
}

export interface Progress {
  current: number
  total: number
}

type SessionStatus = "in_progress" | "completed"

interface StoreState {
  sessionId: string | null
  prolificId: string | null
  messages: Message[]
  qaPairs: QAPair[]
  pendingQuestions: Question[]
  isRecording: boolean
  progress: Progress
  sessionStatus: SessionStatus
  questions: Question[]

  setProlificId: (id: string) => void
  setSessionId: (id: string) => void
  addMessage: (message: Message) => void
  updateMessage: (id: string, updater: (message: Message) => Message) => void
  setIsRecording: (isRecording: boolean) => void
  updateQAPair: (id: string, updates: Partial<QAPair>) => void
  setProgress: (progress: Progress) => void
  setSessionStatus: (status: SessionStatus) => void
  getNextQuestion: () => Question | null
  markQuestionAsAnswered: (questionId: string) => void
  addNewQuestion: (question: Omit<Question, "id">) => string
  loadFromLocalStorage: () => void
  resetStore: () => void
  saveSession: () => Promise<void>
  checkSessionStatus: () => Promise<void>
  initializeWithGuidingQuestions: () => Promise<void>
}

// Initial seed data
const initialMessages: Message[] = []

// Initial seed data - this can be expanded to 20-30 questions as needed
const initialQuestions: Question[] = [
  {
    id: "q1",
    text: "Could you describe your current research focus and how it relates to the broader field?",
    shortText: "Research focus",
  },
  {
    id: "q2",
    text: "Could you elaborate on the methodologies you're using in your current project?",
    shortText: "Methodologies",
  },
  {
    id: "q3",
    text: "What challenges have you encountered in your research, and how have you addressed them?",
    shortText: "Challenges",
  },
  // Additional questions can be added here or loaded from an API
]

const initialQAPairs: QAPair[] = []

const initialProgress: Progress = {
  current: 0,
  total: initialQuestions.length,
}

export const useStore = create<StoreState>()(
  persist(
    (set, get) => ({
      sessionId: null,
      prolificId: null,
      messages: initialMessages,
      qaPairs: initialQAPairs,
      pendingQuestions: [...initialQuestions], // Create a copy of initialQuestions
      isRecording: false,
      progress: initialProgress,
      sessionStatus: "in_progress",
      questions: initialQuestions,

      setProlificId: (id) => {
        localStorage.setItem("prolificId", id)
        set({ prolificId: id })
      },

      setSessionId: (id) => set({ sessionId: id }),

      setSessionStatus: (status) => set({ sessionStatus: status }),

      getNextQuestion: () => {
        const state = get()
        return state.pendingQuestions.length > 0 ? state.pendingQuestions[0] : null
      },

      markQuestionAsAnswered: (questionId) => {
        set((state) => {
          const pendingQuestions = state.pendingQuestions.filter(q => q.id !== questionId)
          
          // Update progress
          const progress = {
            current: state.questions.length - pendingQuestions.length,
            total: state.questions.length
          }

          return { 
            pendingQuestions,
            progress
          }
        })
      },

      /**
       * Adds a new question to both the master question list and pending questions queue
       * @param questionData Object containing text and shortText for the new question
       * @returns The generated ID for the new question
       */
      addNewQuestion: (questionData) => {
        // Generate unique ID using timestamp
        const id = `q${Date.now()}`

        set((state) => {
          // Create the new question with generated ID
          const newQuestion: Question = {
            id,
            text: questionData.text,
            shortText: questionData.shortText
          }

          // Add to master questions list and pending questions
          const questions = [...state.questions, newQuestion]
          const pendingQuestions = [...state.pendingQuestions, newQuestion]
          
          // Update progress calculation
          const progress = {
            current: state.progress.current,
            total: questions.length
          }

          return {
            questions,
            pendingQuestions,
            progress
          }
        })

        // Return the generated question ID so it can be referenced
        return id
      },

      addMessage: (message) =>
        set((state) => {
          // If we're adding a user message and it's answering a question
          const nextQuestion = state.pendingQuestions[0];
          const isAnsweringQuestion = 
            message.role === "user" && 
            nextQuestion && 
            !message.loading;
            
          // Create a new QA pair if needed
          let newQAPairs = [...state.qaPairs];
          
          if (isAnsweringQuestion) {
            // Check if this question is already in QA pairs
            const existingPairIndex = newQAPairs.findIndex(pair => pair.id === nextQuestion.id);
            
            if (existingPairIndex >= 0) {
              // Update existing pair
              newQAPairs[existingPairIndex] = {
                ...newQAPairs[existingPairIndex],
                answer: message.text
              };
            } else {
              // Add new pair
              newQAPairs.push({
                id: nextQuestion.id,
                question: nextQuestion.text,
                answer: message.text
              });
            }
          }

          // If it's a bot message with a question that doesn't exist in QA pairs yet
          // We'll associate it with an existing question from our questions array
          if (
            message.role === "bot" &&
            !message.loading &&
            message.text.includes("?")
          ) {
            // Try to find a matching question in our questions array
            const matchingQuestion = state.questions.find(q => q.text === message.text);
            
            if (matchingQuestion && !state.qaPairs.some(qa => qa.id === matchingQuestion.id)) {
              // Use the question's ID from our questions array
              newQAPairs.push({
                id: matchingQuestion.id,
                question: message.text,
                answer: "",
              });
            }
          }

          return {
            messages: [...state.messages, message],
            qaPairs: newQAPairs
          };
        }),

      updateMessage: (id, updater) =>
        set((state) => {
          // Get the updated message
          const originalMessage = state.messages.find(m => m.id === id);
          if (!originalMessage) return state;
          
          const updatedMessage = updater(originalMessage);
          
          // Update QA pairs if needed
          let updatedQAPairs = [...state.qaPairs];
          
          // If it's a bot message that changed from loading to not loading and has a question
          if (
            originalMessage.role === "bot" && 
            originalMessage.loading && 
            !updatedMessage.loading && 
            updatedMessage.text.includes("?")
          ) {
            // Try to find a matching question in our questions array
            const matchingQuestion = state.questions.find(q => q.text === updatedMessage.text);
            
            if (matchingQuestion && !state.qaPairs.some(qa => qa.id === matchingQuestion.id)) {
              // Use the question's ID from our questions array
              updatedQAPairs.push({
                id: matchingQuestion.id,
                question: updatedMessage.text,
                answer: "",
              });
            }
          }
          
          return {
            messages: state.messages.map(msg => msg.id === id ? updatedMessage : msg),
            qaPairs: updatedQAPairs
          };
        }),

      setIsRecording: (isRecording) => set({ isRecording }),

      updateQAPair: (id, updates) =>
        set((state) => ({
          qaPairs: state.qaPairs.map((pair) => (pair.id === id ? { ...pair, ...updates } : pair)),
        })),

      setProgress: (progress) => set({ progress }),

      loadFromLocalStorage: () => {
        // This is handled by the persist middleware
        // But we provide this method for explicit loading if needed
        const prolificId = localStorage.getItem("prolificId")
        if (prolificId) {
          set({ prolificId })
        }
        
        // Update pendingQuestions based on answered questions
        const state = get();
        if (state.qaPairs.length > 0) {
          // Get IDs of answered questions
          const answeredQuestionIds = state.qaPairs
            .filter(qa => qa.answer && qa.answer.trim() !== '')
            .map(qa => qa.id);
            
          // Remove answered questions from pendingQuestions
          const remainingQuestions = state.questions.filter(
            q => !answeredQuestionIds.includes(q.id)
          );
          
          // Update progress
          const progress = {
            current: state.questions.length - remainingQuestions.length,
            total: state.questions.length,
          };
          
          set({ 
            pendingQuestions: remainingQuestions,
            progress
          });
        }
      },

      resetStore: () =>
        set({
          messages: initialMessages,
          qaPairs: initialQAPairs,
          pendingQuestions: [...initialQuestions],
          isRecording: false,
          progress: initialProgress,
          sessionStatus: "in_progress",
          // Clear all data including sessionId and prolificId
          sessionId: null,
          prolificId: null
        }),

      saveSession: async () => {
        console.log("==== saveSession execution started ====")
        
        try {
          // Use the simplified sync service instead of complex logic
          const result = await SyncService.syncSession()
          
          if (result.success) {
            console.log("Session saved successfully with ID:", result.sessionId)
          } else {
            console.error("Failed to save session:", result.error)
          }
        } catch (error) {
          console.error("Error in saveSession:", error)
        } finally {
          console.log("==== saveSession execution completed ====")
        }
      },

      checkSessionStatus: async () => {
        const state = get()

        try {
          if (state.sessionId) {
            console.log(`Checking status for session: ${state.sessionId}`)
            
            // Add a delay for new sessions to ensure they're properly registered in the database
            const isNewSession = state.messages.length <= 1
            if (isNewSession) {
              console.log("This appears to be a new session, adding delay before status check")
              await new Promise(resolve => setTimeout(resolve, 2000))
            }
            
            // Use the sync service for status checking
            const status = await SyncService.checkSessionStatus(state.sessionId)
            
            if (status && status !== state.sessionStatus) {
              console.log(`Updating session status from ${state.sessionStatus} to ${status}`)
              set({ sessionStatus: status as SessionStatus })
            } else if (status === null) {
              console.log("Session check returned null status")
              
              // Don't reset state for new sessions (created in the last minute)
              const sessionIdTimestamp = state.sessionId.split('_')[1]
              if (sessionIdTimestamp && Date.now() - parseInt(sessionIdTimestamp) < 60000) {
                console.log("Session was recently created, not resetting state")
                return
              }
              
              // Also don't reset if we're not in the middle of creating a new session
              if (state.qaPairs.length === 0 || state.pendingQuestions.length === 0) {
                console.log("Session appears to be incomplete, not resetting state")
                return
              }
              
              // Session not found and all safety checks passed, now it's safe to reset state
              console.log("Session not found on server and it's not a new session, resetting state")
              get().resetStore()
              
              // Force reload to return to home page
              if (typeof window !== 'undefined') {
                window.location.href = "/"
              }
            }
          }
        } catch (error) {
          console.error("Failed to check session status:", error)
        }
      },
      
      // Add new function to initialize a session with guiding questions
      initializeWithGuidingQuestions: async () => {
        console.log("Initializing session with guiding questions")
        
        // First check if we already have questions
        const state = get()
        if (state.questions.length > 0) {
          console.log("Session already has questions, skipping initialization")
          return
        }
        
        // Use sync service to load guiding questions
        const success = await SyncService.initializeSessionWithGuidingQuestions()
        
        if (success) {
          console.log("Session initialized with guiding questions")
        } else {
          console.warn("Failed to initialize with guiding questions, using defaults")
          // Keep using defaults if loading from server fails
          set({
            questions: initialQuestions,
            pendingQuestions: [...initialQuestions],
            qaPairs: initialQAPairs,
            progress: initialProgress
          })
        }
      }
    }),
    {
      name: "ach-collector-storage",
      partialize: (state) => ({
        messages: state.messages,
        qaPairs: state.qaPairs,
        pendingQuestions: state.pendingQuestions,
        progress: state.progress,
        sessionId: state.sessionId,
        prolificId: state.prolificId,
        sessionStatus: state.sessionStatus,
      }),
    },
  ),
)
