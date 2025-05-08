"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import { SyncService } from "./sync-service"
import { v4 as uuidv4 } from "uuid"

export interface Message {
  id: string
  role: "user" | "bot"
  text: string
  loading?: boolean
}

export interface QAPair {
  id: string
  question: string
  shortText: string
  answer: string
  category?: string  // Optional category field to identify tutorial vs research questions
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
  status: SessionStatus
  currentQuestionIndex: number

  setProlificId: (id: string) => void
  setSessionId: (id: string) => void
  addMessage: (message: Message) => void
  updateMessage: (id: string, updater: (message: Message) => Message) => void
  setIsRecording: (isRecording: boolean) => void
  updateQAPair: (id: string, updates: Partial<QAPair>) => void
  setProgress: (progress: Progress) => void
  setStatus: (status: SessionStatus) => void
  getNextQuestion: () => QAPair | null
  markQuestionAsAnswered: (questionId: string) => void
  moveToNextQuestion: () => void
  getCurrentQuestionIndex: () => number
  addNewQuestion: (question: Omit<QAPair, "id" | "answer"> & { category?: string }) => string
  loadFromLocalStorage: () => void
  resetStore: () => void
  saveSession: () => Promise<void>
  checkSessionStatus: () => Promise<void>
  initializeWithGuidingQuestions: () => Promise<void>
  recalculateProgress: () => void
}

// Initial seed data
const initialMessages: Message[] = []

// Initial seed data - this can be expanded to 20-30 questions as needed
const initialQAPairs: QAPair[] = []

const initialProgress: Progress = {
  current: 0,
  total: 0,
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
      status: "in_progress",
      currentQuestionIndex: 0,

      setProlificId: (id) => {
        localStorage.setItem("prolificId", id)
        set({ prolificId: id })
      },

      setSessionId: (id) => set({ sessionId: id }),

      setStatus: (status) => set({ status }),

      getCurrentQuestionIndex: () => {
        return get().currentQuestionIndex;
      },

      getNextQuestion: () => {
        const state = get()
        if (state.qaPairs.length === 0) return null;
        
        // Use currentQuestionIndex to get the current question
        if (state.currentQuestionIndex < state.qaPairs.length) {
          return state.qaPairs[state.currentQuestionIndex];
        }
        
        return null;
      },

      moveToNextQuestion: () => {
        set((state) => {
          // Only increment if there are more questions
          if (state.currentQuestionIndex < state.qaPairs.length - 1) {
            const newIndex = state.currentQuestionIndex + 1;
            
            // Update progress based on the new index
            const progress = {
              current: newIndex,
              total: state.qaPairs.length
            };
            
            console.log(`Moving to next question. New index: ${newIndex}, Progress: ${progress.current}/${progress.total}`);
            
            // Get existing message IDs to avoid duplicates
            const existingMessageIds = new Set(state.messages.map(m => m.id));
            const existingAnswerPairs = new Map();
            
            // Identify existing question-answer pairs
            for (let i = 0; i < state.messages.length - 1; i++) {
              const msg = state.messages[i];
              const nextMsg = state.messages[i + 1];
              if (msg.role === 'bot' && nextMsg && nextMsg.role === 'user') {
                existingAnswerPairs.set(msg.text, nextMsg.text);
              }
            }
            
            // Keep existing messages instead of rebuilding
            const filteredMessages = [...state.messages]; 
            
            // Check if the last message is already the next question
            const lastMessageInMessages = state.messages.length > 0 ? 
              state.messages[state.messages.length - 1] : null;
            
            // Only add the next question if it's not already the last message
            const nextQuestion = state.qaPairs[newIndex];
            if (nextQuestion && (!lastMessageInMessages || 
                lastMessageInMessages.role !== 'bot' || 
                lastMessageInMessages.text !== nextQuestion.question)) {
              
              // Add the next question as a message
              filteredMessages.push({
                id: `msg_q_${nextQuestion.id}_${Date.now()}`,
                role: "bot" as const,
                text: nextQuestion.question,
                loading: false
              });
            }
            
            return { 
              currentQuestionIndex: newIndex,
              progress,
              messages: filteredMessages
            };
          } else if (state.currentQuestionIndex === state.qaPairs.length - 1) {
            // We're already at the last question - trying to move beyond
            // This means all questions are answered - set progress to 100%
            const progress = {
              current: state.qaPairs.length,
              total: state.qaPairs.length
            };
            
            console.log(`All questions completed. Progress: ${progress.current}/${progress.total} (100%)`);
            
            return {
              // Keep current index at the last question
              currentQuestionIndex: state.currentQuestionIndex,
              progress
            };
          }
          
          // If we're at beyond the last question already, don't change anything
          return state;
        });
      },

      markQuestionAsAnswered: (questionId) => {
        console.log(`Marking question as answered: ${questionId}`)
        
        // We don't remove from pendingQuestions anymore,
        // we just move to the next question if this was the current one
        const state = get();
        const currentQAPair = state.qaPairs[state.currentQuestionIndex];
        
        if (currentQAPair && currentQAPair.id === questionId) {
          // If this was the current question, move to the next one
          get().moveToNextQuestion();
        }
      },

      addMessage: (message) =>
        set((state) => {
          // If we're adding a user message and it's answering a question
          const currentQAPair = state.currentQuestionIndex < state.qaPairs.length 
            ? state.qaPairs[state.currentQuestionIndex] 
            : null;
          
          const isAnsweringQuestion = 
            message.role === "user" && 
            currentQAPair && 
            !message.loading;
            
          // Create a new QA pair if needed
          let newQAPairs = [...state.qaPairs];
          
          if (isAnsweringQuestion) {
            // Update existing pair
            newQAPairs = newQAPairs.map((pair, index) => {
              if (index === state.currentQuestionIndex) {
                return {
                  ...pair,
                  answer: message.text
                };
              }
              return pair;
            });
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
          
          return {
            messages: state.messages.map(msg => msg.id === id ? updatedMessage : msg)
          };
        }),

      setIsRecording: (isRecording) => set({ isRecording }),

      updateQAPair: (id, updates) =>
        set((state) => {
          const newQAPairs = state.qaPairs.map((pair) => 
            pair.id === id ? { ...pair, ...updates } : pair
          );
          
          // Update QA pairs after, if currentQuestion's answer is updated and has a valid answer, consider moving to the next question
          const currentQAPair = state.currentQuestionIndex < state.qaPairs.length 
            ? state.qaPairs[state.currentQuestionIndex] 
            : null;
            
          // If updating is currentQuestion's answer and has a valid answer, consider moving to the next question
          if (currentQAPair && 
              currentQAPair.id === id && 
              updates.answer && 
              updates.answer.trim() !== '') {
            
            // Update messages list's answer
            let messagesUpdated = false;
            const updatedMessages = state.messages.map(msg => {
              // Find associated user message and update
              if (msg.role === "user" && state.messages.indexOf(msg) > 0) {
                const prevMsgIndex = state.messages.indexOf(msg) - 1;
                const prevMsg = state.messages[prevMsgIndex];
                
                if (prevMsg && prevMsg.role === "bot" && prevMsg.text === currentQAPair.question) {
                  messagesUpdated = true;
                  // 保持原ID但更新文本内容
                  return {
                    ...msg,
                    text: updates.answer || ""
                  };
                }
              }
              return msg;
            });
            
            // 如果没有找到对应消息进行更新，可能需要添加新消息
            if (!messagesUpdated) {
              // 在这种情况下，我们需要添加一个用户答案消息
              const timestamp = Date.now();
              updatedMessages.push({
                id: `msg_a_${id}_${timestamp}`,
                role: "user",
                text: updates.answer || "",
                loading: false
              });
              messagesUpdated = true;
            }
            
            if (messagesUpdated) {
              return {
                qaPairs: newQAPairs,
                messages: updatedMessages
              };
            }
          }
          
          return { qaPairs: newQAPairs };
        }),

      setProgress: (progress) => set({ progress }),

      loadFromLocalStorage: () => {
        // This is handled by the persist middleware
        // But we provide this method for explicit loading if needed
        const prolificId = localStorage.getItem("prolificId")
        if (prolificId) {
          set({ prolificId })
        }
        
        // Always recalculate progress, even if there are no QA pairs
        console.log("Recalculating progress after loading from localStorage")
        
        const state = get();
        
        // Log all questions
        console.log(`Total questions in store (${state.qaPairs.length}):`, 
          state.qaPairs.map(qa => ({id: qa.id, shortText: qa.shortText})));
        
        // Log all QA pairs
        console.log(`Total QA pairs in store (${state.qaPairs.length}):`, 
          state.qaPairs.map(qa => ({id: qa.id, question: qa.question.substring(0, 30) + "...", hasAnswer: Boolean(qa.answer)})));
        
        // Get IDs of answered questions - only those with non-empty answers
        const answeredQAPairs = state.qaPairs.filter(qa => qa.answer && qa.answer.trim() !== '');
        const answeredQuestionIds = answeredQAPairs.map(qa => qa.id);
        
        console.log(`Found ${answeredQuestionIds.length} answered questions out of ${state.qaPairs.length} total QA pairs`)
          
        // Get unanswered questions (but don't replace qaPairs with them)
        const remainingQuestions = state.qaPairs.filter(
          q => !answeredQuestionIds.includes(q.id)
        );
        
        // Log pending questions after calculation
        console.log(`Pending questions (${remainingQuestions.length}):`, 
          remainingQuestions.map(q => ({id: q.id, shortText: q.shortText})));
        
        // Update progress - if all questions are answered, set current to total
        const progress = {
          current: remainingQuestions.length === 0 && state.qaPairs.length > 0 
            ? state.qaPairs.length 
            : answeredQuestionIds.length,
          total: state.qaPairs.length,
        };
        
        console.log(`Progress calculation: ${progress.current}/${progress.total} (${Math.round((progress.current/Math.max(1, progress.total))*100)}%)`)
        console.log(`Questions: ${state.qaPairs.length}, Remaining: ${remainingQuestions.length}`)
        
        // Only update progress, don't modify qaPairs
        set({ progress });
        
        // If all questions are answered, log this
        if (progress.current === progress.total && progress.total > 0) {
          console.log("All questions have been answered in loadFromLocalStorage, should redirect to review page");
        }
      },

      resetStore: () =>
        set({
          messages: initialMessages,
          qaPairs: initialQAPairs,
          isRecording: false,
          progress: initialProgress,
          status: "in_progress",
          // Clear all data including sessionId and prolificId
          sessionId: null,
          prolificId: null,
          currentQuestionIndex: 0
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
            
            // First, fetch the full session data to ensure local and server are in sync
            console.log("Fetching full session data to ensure local/server sync")
            await SyncService.fetchFullSessionData(state.sessionId)
            
            // After data is synced, check the status
            const status = await SyncService.checkSessionStatus(state.sessionId)
            
            if (status && status !== state.status) {
              console.log(`Updating session status from ${state.status} to ${status}`)
              set({ status: status as SessionStatus })
              
              // Recalculate progress after status update
              if (status === "in_progress") {
                console.log("Recalculating progress after status update")
                get().recalculateProgress()
              }
            } else if (status === null) {
              console.log("Session check returned null status")
              
              // Don't reset state for new sessions (created in the last minute)
              const sessionIdTimestamp = state.sessionId.split('_')[1]
              if (sessionIdTimestamp && Date.now() - parseInt(sessionIdTimestamp) < 60000) {
                console.log("Session was recently created, not resetting state")
                return
              }
              
              // Also don't reset if we're not in the middle of creating a new session
              if (state.qaPairs.length === 0) {
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
      
      // Modify recalculateProgress to use currentQuestionIndex
      recalculateProgress: () => {
        const state = get();
        console.log("Manually recalculating progress...")
        
        // Get answered question IDs
        const answeredQAPairs = state.qaPairs.filter(qa => qa.answer && qa.answer.trim() !== '');
        const answeredQuestionIds = answeredQAPairs.map(qa => qa.id);
        
        // Log all questions
        console.log(`Total questions (${state.qaPairs.length}):`, 
          state.qaPairs.map(qa => ({id: qa.id, shortText: qa.shortText})));
        
        // Determine the highest answered question index
        let highestAnsweredIndex = -1;
        
        for (let i = 0; i < state.qaPairs.length; i++) {
          if (answeredQuestionIds.includes(state.qaPairs[i].id)) {
            highestAnsweredIndex = i;
          } else {
            // Found first unanswered question
            break;
          }
        }
        
        // Set currentQuestionIndex to the next unanswered question
        const newIndex = highestAnsweredIndex + 1;
        
        // Ensure we don't go beyond the array length
        const currentQuestionIndex = Math.min(newIndex, state.qaPairs.length - 1);
        
        // Log pending questions
        console.log(`Pending questions (${state.qaPairs.length - answeredQuestionIds.length}):`, 
          state.qaPairs.filter(qa => !answeredQuestionIds.includes(qa.id)).map(q => ({id: q.id, shortText: q.shortText})));
        
        // Log answered questions
        console.log(`Answered questions (${answeredQuestionIds.length}):`, 
          answeredQuestionIds);
        
        // Calculate progress based on answered questions
        // If all questions are answered (newIndex >= length), set current to total for 100% completion
        const progress = {
          current: newIndex >= state.qaPairs.length ? state.qaPairs.length : answeredQuestionIds.length,
          total: state.qaPairs.length,
        };
        
        console.log(`Progress recalculated: ${progress.current}/${progress.total} (${Math.round(progress.current/progress.total*100)}%)`)
        console.log(`New currentQuestionIndex: ${currentQuestionIndex}`);
        
        // Only rebuild messages if they're empty (after page refresh)
        let newMessages = state.messages;
        
        // If no messages or need to completely rebuild messages
        if (state.messages.length === 0) {
          newMessages = [];
          // Build message list including all questions up to current index
          for (let i = 0; i <= currentQuestionIndex && i < state.qaPairs.length; i++) {
            const qaPair = state.qaPairs[i];
            const timestamp = Date.now() + i; // 添加i确保每次循环生成的时间戳不同
            
            // Add question message
            newMessages.push({
              id: `msg_q_${qaPair.id}_${timestamp}`,
              role: "bot" as const,
              text: qaPair.question,
              loading: false
            });
            
            // If there's an answer, add answer message
            if (qaPair.answer && qaPair.answer.trim() !== '') {
              newMessages.push({
                id: `msg_a_${qaPair.id}_${timestamp+1}`,
                role: "user" as const,
                text: qaPair.answer,
                loading: false
              });
            }
          }
        } else {
          // Check if the last message is already the current question
          const lastMessage = state.messages.length > 0 ?
            state.messages[state.messages.length - 1] : null;
          
          // If current question exists
          if (currentQuestionIndex >= 0 && currentQuestionIndex < state.qaPairs.length) {
            const currentQA = state.qaPairs[currentQuestionIndex];
            
            // If the last message is not the current question, need to add it
            if (!lastMessage || lastMessage.role !== 'bot' || lastMessage.text !== currentQA.question) {
              newMessages = [...state.messages];
              newMessages.push({
                id: `msg_q_${currentQA.id}_${Date.now()}`,
                role: "bot" as const,
                text: currentQA.question,
                loading: false
              });
            }
          }
        }
        
        set({ 
          progress,
          currentQuestionIndex,
          messages: newMessages
        });
        
        // Check if all questions have been answered
        if (progress.current === progress.total && progress.total > 0) {
          console.log("All questions answered in recalculateProgress!");
        }
        
        return progress;
      },

      initializeWithGuidingQuestions: async () => {
        console.log("Initializing session with guiding questions")
        
        // Check if initialization has already been done in this session
        const hasInitialized = sessionStorage.getItem('hasInitializedQuestions') === 'true'
        
        // First check if we already have questions
        const state = get()
        if (hasInitialized || state.qaPairs.length > 0) {
          console.log("Session already has questions or has been initialized, skipping initialization")
          
          // Even if we skip initialization, ensure progress is correct
          console.log("Recalculating progress for existing questions")
          get().recalculateProgress();
          return
        }
        
        // Use sync service to load guiding questions
        const success = await SyncService.initializeSessionWithGuidingQuestions()
        
        if (success) {
          console.log("Session initialized with guiding questions")
          
          // Mark as initialized in this session
          sessionStorage.setItem('hasInitializedQuestions', 'true')
          
          // Ensure progress is calculated correctly after initialization
          const state = get();
          console.log(`Initialized with ${state.qaPairs.length} questions, recalculating progress`)
          
          // Update currentQuestionIndex based on answered QA pairs
          const answeredCount = state.qaPairs.filter(qa => qa.answer && qa.answer.trim() !== '').length;
          if (answeredCount > 0) {
            set({ currentQuestionIndex: answeredCount });
          }
          
          get().recalculateProgress();
        } else {
          console.warn("Failed to initialize with guiding questions, using defaults")
          // Keep using defaults if loading from server fails
          set({
            qaPairs: initialQAPairs,
            progress: initialProgress,
            currentQuestionIndex: 0
          })
          
          // Still mark as initialized to prevent repeated attempts
          sessionStorage.setItem('hasInitializedQuestions', 'true')
        }
      },

      /**
       * Add a new question
       * @param questionData Object containing text, shortText, and optionally category
       * @returns Generated ID for the new question
       */
      addNewQuestion: (questionData) => {
        // Generate a unique ID using timestamp and UUID to ensure uniqueness
        // This prevents collisions when multiple questions are added at almost the same time
        const id = `q${Date.now()}_${uuidv4().substring(0, 8)}`

        set((state) => {
          // Create a new QA pair with the generated ID
          const newQAPair: QAPair = {
            id,
            question: questionData.question,
            shortText: questionData.shortText,
            category: questionData.category || 'research', // Default to 'research' if not specified
            answer: ""
          }

          // Add to QA pairs list
          const qaPairs = [...state.qaPairs, newQAPair]
          
          // Update progress calculation
          const progress = {
            current: state.currentQuestionIndex,
            total: qaPairs.length
          }

          return {
            qaPairs,
            progress
          }
        })

        // Return the generated question ID for reference
        return id
      }
    }),
    {
      name: "ach-collector-storage",
      partialize: (state) => ({
        messages: state.messages,
        qaPairs: state.qaPairs,
        progress: state.progress,
        sessionId: state.sessionId,
        prolificId: state.prolificId,
        status: state.status,
        currentQuestionIndex: state.currentQuestionIndex
      }),
    },
  ),
)
