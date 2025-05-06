"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

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

          // If it's a bot message with a question, add it to qaPairs if it doesn't exist
          if (
            message.role === "bot" &&
            !message.loading &&
            message.text.includes("?") &&
            !state.qaPairs.some((qa) => qa.question === message.text)
          ) {
            newQAPairs.push({
              id: message.id,
              question: message.text,
              answer: "",
            });
          }

          return {
            messages: [...state.messages, message],
            qaPairs: newQAPairs
          };
        }),

      updateMessage: (id, updater) =>
        set((state) => ({
          messages: state.messages.map((message) => (message.id === id ? updater(message) : message)),

          // If it's a bot message that's no longer loading and contains a question, add it to qaPairs
          qaPairs:
            state.messages.find((m) => m.id === id)?.role === "bot" &&
            !updater(state.messages.find((m) => m.id === id)!).loading &&
            updater(state.messages.find((m) => m.id === id)!).text.includes("?") &&
            !state.qaPairs.some((qa) => qa.id === id)
              ? [
                  ...state.qaPairs,
                  {
                    id,
                    question: updater(state.messages.find((m) => m.id === id)!).text,
                    answer: "",
                  },
                ]
              : state.qaPairs,
        })),

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
        const state = get()

        try {
          // First check the server's session status before making updates
          if (state.sessionId) {
            // Check current session status from the server
            await get().checkSessionStatus()
            
            // Get the potentially updated state after status check
            const updatedState = get()
            
            // If session is completed, don't update it further
            if (updatedState.sessionStatus === "completed") {
              console.log("Session is already completed, skipping update")
              return
            }
            
            // Update existing session
            const response = await fetch(`/api/sessions/${state.sessionId}`, {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                prolificId: updatedState.prolificId,
                qaPairs: updatedState.qaPairs,
                pendingQuestions: updatedState.pendingQuestions,
                status: updatedState.sessionStatus
              }),
            })
          } else {
            // Create new session
            const response = await fetch("/api/sessions", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                prolificId: state.prolificId,
                qaPairs: state.qaPairs,
                pendingQuestions: state.pendingQuestions,
                status: state.sessionStatus
              }),
            })

            const data = await response.json()
            if (data.sessionId) {
              set({ sessionId: data.sessionId })
              
              // Check session status after creating a new session
              await get().checkSessionStatus()
            }
          }
        } catch (error) {
          console.error("Failed to save session:", error)
        }
      },

      checkSessionStatus: async () => {
        const state = get()

        try {
          if (state.sessionId) {
            const response = await fetch(`/api/sessions/status/${state.sessionId}`, {
              method: "GET",
            })

            if (response.ok) {
              const data = await response.json()
              if (data.status && data.status !== state.sessionStatus) {
                console.log(`Updating session status from ${state.sessionStatus} to ${data.status}`)
                set({ sessionStatus: data.status })
              }
            }
          }
        } catch (error) {
          console.error("Failed to check session status:", error)
        }
      },
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
