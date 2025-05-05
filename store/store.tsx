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

export interface Progress {
  current: number
  total: number
}

interface StoreState {
  sessionId: string | null
  prolificId: string | null
  messages: Message[]
  qaPairs: QAPair[]
  isRecording: boolean
  progress: Progress

  setProlificId: (id: string) => void
  setSessionId: (id: string) => void
  addMessage: (message: Message) => void
  updateMessage: (id: string, updater: (message: Message) => Message) => void
  setIsRecording: (isRecording: boolean) => void
  updateQAPair: (id: string, updates: Partial<QAPair>) => void
  setProgress: (progress: Progress) => void
  loadFromLocalStorage: () => void
  resetStore: () => void
  saveSession: () => Promise<void>
}

// Initial seed data
const initialMessages: Message[] = []

const initialQAPairs: QAPair[] = [
  {
    id: "q1",
    question: "Could you describe your current research focus and how it relates to the broader field?",
    answer:
      "My research focuses on human-computer interaction with a specific emphasis on accessibility. I'm developing new interfaces that can adapt to users with different abilities, which connects to the broader field of inclusive design.",
  },
  {
    id: "q2",
    question: "Could you elaborate on the methodologies you're using in your current project?",
    answer:
      "I'm using a mixed-methods approach that combines quantitative user testing with qualitative interviews. This allows me to gather both performance metrics and rich contextual information about the user experience.",
  },
  {
    id: "q3",
    question: "What challenges have you encountered in your research, and how have you addressed them?",
    answer:
      "The biggest challenge has been recruiting diverse participants. I've addressed this by partnering with community organizations and using more inclusive recruitment language in our materials.",
  },
]

const initialProgress: Progress = {
  current: 0,
  total: 3,
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

      setProlificId: (id) => {
        localStorage.setItem("prolificId", id)
        set({ prolificId: id })
      },

      setSessionId: (id) => set({ sessionId: id }),

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],

          // If it's a bot message with a question, add it to qaPairs
          qaPairs:
            message.role === "bot" && !message.loading && message.text.includes("?")
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
                qaPairs: state.qaPairs,
                status: "in_progress",
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
      }),
    },
  ),
)
