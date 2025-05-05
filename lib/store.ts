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
  isRecording: boolean
  progress: Progress
  sessionStatus: SessionStatus
  questions: Question[]
  currentQuestionIndex: number

  setProlificId: (id: string) => void
  setSessionId: (id: string) => void
  addMessage: (message: Message) => void
  updateMessage: (id: string, updater: (message: Message) => Message) => void
  setIsRecording: (isRecording: boolean) => void
  updateQAPair: (id: string, updates: Partial<QAPair>) => void
  setProgress: (progress: Progress) => void
  setSessionStatus: (status: SessionStatus) => void
  setCurrentQuestionIndex: (index: number) => void
  loadFromLocalStorage: () => void
  resetStore: () => void
  saveSession: () => Promise<void>
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

const initialQAPairs: QAPair[] = initialQuestions.map((q) => ({
  id: q.id,
  question: q.text,
  answer: "",
}))

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
      isRecording: false,
      progress: initialProgress,
      sessionStatus: "in_progress",
      questions: initialQuestions,
      currentQuestionIndex: 0,

      setProlificId: (id) => {
        localStorage.setItem("prolificId", id)
        set({ prolificId: id })
      },

      setSessionId: (id) => set({ sessionId: id }),

      setSessionStatus: (status) => set({ sessionStatus: status }),

      setCurrentQuestionIndex: (index) => {
        set({ currentQuestionIndex: index })
        // Also update progress
        set((state) => ({
          progress: {
            ...state.progress,
            current: index,
          },
        }))
      },

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],

          // If it's a bot message with a question, add it to qaPairs if it doesn't exist
          qaPairs:
            message.role === "bot" &&
            !message.loading &&
            message.text.includes("?") &&
            !state.qaPairs.some((qa) => qa.question === message.text)
              ? [
                  ...state.qaPairs,
                  {
                    id: message.id,
                    question: message.text,
                    answer: "",
                  },
                ]
              : state.qaPairs,
        })),

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
      },

      resetStore: () =>
        set({
          messages: initialMessages,
          qaPairs: initialQAPairs,
          isRecording: false,
          progress: initialProgress,
          sessionStatus: "in_progress",
          currentQuestionIndex: 0,
          // Don't reset sessionId or prolificId
        }),

      saveSession: async () => {
        const state = get()

        try {
          if (state.sessionId) {
            // Update existing session
            await fetch(`/api/sessions/${state.sessionId}`, {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                prolificId: state.prolificId,
                qaPairs: state.qaPairs,
                status: state.sessionStatus,
                currentQuestionIndex: state.currentQuestionIndex,
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
                status: state.sessionStatus,
                currentQuestionIndex: state.currentQuestionIndex,
              }),
            })

            const data = await response.json()
            if (data.sessionId) {
              set({ sessionId: data.sessionId })
            }
          }
        } catch (error) {
          console.error("Failed to save session:", error)
        }
      },
    }),
    {
      name: "ach-collector-storage",
      partialize: (state) => ({
        messages: state.messages,
        qaPairs: state.qaPairs,
        progress: state.progress,
        sessionId: state.sessionId,
        prolificId: state.prolificId,
        sessionStatus: state.sessionStatus,
        currentQuestionIndex: state.currentQuestionIndex,
      }),
    },
  ),
)
