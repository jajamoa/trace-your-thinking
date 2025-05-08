"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import { SyncService } from "./sync-service"
import { v4 as uuidv4 } from "uuid"
import { PythonAPIService } from "./python-api-service"

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
  processed?: boolean // Track if this QA has been processed by the LLM
  processingState?: 'pending' | 'processing' | 'completed' | 'error' // Track processing state
  processingError?: string // Store any error that occurred during processing
  version?: number // Version number to handle concurrent updates
  lastUpdated?: number // Timestamp of last update
}

export interface Progress {
  current: number
  total: number
}

export interface PendingRequest {
  id: string
  qaPairId: string
  timestamp: number
  status: 'pending' | 'processing' | 'completed' | 'error'
  error?: string
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
  pendingRequests: PendingRequest[] // Queue of pending requests
  processingLock: boolean // Lock to prevent concurrent processing
  optimisticUpdates: Map<string, QAPair> // Store for tracking optimistic updates

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
  addPendingRequest: (qaPairId: string) => string // Add async request to queue
  updatePendingRequest: (requestId: string, updates: Partial<PendingRequest>) => void // Update request status
  processNextPendingRequest: () => Promise<void> // Process next request in queue
  hasPendingRequests: () => boolean // Check if there are any pending requests
  isLastQAPairAnswered: () => boolean // Check if the last QA pair is answered
  getUnprocessedQAs: () => QAPair[] // Get all unprocessed QA pairs
  syncProcessingQueue: () => void // Sync the processing queue with QA pairs
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
      pendingRequests: [], // Initialize empty request queue
      processingLock: false, // Initialize processing lock
      optimisticUpdates: new Map(), // Initialize optimistic updates

      // Add async request to queue
      addPendingRequest: (qaPairId) => {
        const requestId = `req_${uuidv4()}`;
        
        // Mark the QA pair as pending processing
        const state = get();
        const qaPairIndex = state.qaPairs.findIndex(qa => qa.id === qaPairId);
        
        if (qaPairIndex >= 0) {
          const qaPair = state.qaPairs[qaPairIndex];
          const updatedQAPair = {
            ...qaPair,
            processingState: 'pending' as 'pending',
            version: (qaPair.version || 0) + 1,
            lastUpdated: Date.now()
          };
          
          const newQAPairs = [...state.qaPairs];
          newQAPairs[qaPairIndex] = updatedQAPair;
          
          // Track this as an optimistic update
          const newOptimisticUpdates = new Map(state.optimisticUpdates);
          newOptimisticUpdates.set(qaPairId, updatedQAPair);
          
          set({ 
            qaPairs: newQAPairs,
            optimisticUpdates: newOptimisticUpdates
          });
        }
        
        set((state) => ({
          pendingRequests: [
            ...state.pendingRequests,
            {
              id: requestId,
              qaPairId,
              timestamp: Date.now(),
              status: 'pending'
            }
          ]
        }));
        return requestId;
      },

      // Update request status with proper concurrency control
      updatePendingRequest: (requestId, updates) => {
        // Get the request first to update the corresponding QA pair
        const state = get();
        const request = state.pendingRequests.find(req => req.id === requestId);
        
        if (request && updates.status) {
          // Update the QA pair processing state with version control
          const qaPairIndex = state.qaPairs.findIndex(qa => qa.id === request.qaPairId);
          
          if (qaPairIndex >= 0) {
            const qaPair = state.qaPairs[qaPairIndex];
            
            // Create updated QA pair with incremented version
            const updatedQAPair = {
              ...qaPair,
              processingState: updates.status as 'pending' | 'processing' | 'completed' | 'error',
              processingError: updates.error,
              processed: updates.status === 'completed' ? true : qaPair.processed,
              version: (qaPair.version || 0) + 1,
              lastUpdated: Date.now()
            };
            
            const newQAPairs = [...state.qaPairs];
            newQAPairs[qaPairIndex] = updatedQAPair;
            
            // Update optimistic updates map
            const newOptimisticUpdates = new Map(state.optimisticUpdates);
            newOptimisticUpdates.set(request.qaPairId, updatedQAPair);
            
            set({ 
              qaPairs: newQAPairs,
              optimisticUpdates: newOptimisticUpdates
            });
          }
        }
        
        // Update request status in pendingRequests array
        set((state) => ({
          pendingRequests: state.pendingRequests.map(req => 
            req.id === requestId ? { ...req, ...updates } : req
          )
        }));
      },

      // Process next request in queue with improved concurrency control
      processNextPendingRequest: async () => {
        const state = get();
        
        // If locked, another process is already running
        if (state.processingLock) {
          console.log('Processing already in progress, skipping');
          return;
        }
        
        // Find next pending request
        const nextRequest = state.pendingRequests.find(req => req.status === 'pending');
        if (!nextRequest) return;
        
        try {
          // Set processing lock
          set({ processingLock: true });
          
          // Mark as processing
          get().updatePendingRequest(nextRequest.id, { status: 'processing' });
          
          // Find corresponding QA pair
          const qaPair = state.qaPairs.find(qa => qa.id === nextRequest.qaPairId);
          if (!qaPair) {
            get().updatePendingRequest(nextRequest.id, { status: 'error', error: 'QA pair not found' });
            set({ processingLock: false }); // Release lock
            return;
          }
          
          // Get existing QA pairs for context
          const index = state.qaPairs.findIndex(qa => qa.id === nextRequest.qaPairId);
          
          // Ensure all QA pairs have the correct format
          const validQAPairs = state.qaPairs.map(qa => {
            // Ensure each QA pair is a proper object with required fields
            return {
              id: qa.id,
              question: qa.question || '',
              shortText: qa.shortText || '',
              answer: qa.answer || '',
              category: qa.category || 'research'
            };
          });
          
          // Send request to Python backend
          const response = await PythonAPIService.processAnswer(
            state.sessionId || '',
            state.prolificId || '',
            qaPair,
            validQAPairs, // Use the validated QA pairs
            index,
            null
          );
          
          if (response.success) {
            // Update with transaction-like approach to prevent race conditions
            set((state) => {
              // Get current state after async operation completed
              const currentQAPairs = [...state.qaPairs];
              const currentIndex = currentQAPairs.findIndex(qa => qa.id === qaPair.id);
              
              // If QA pair no longer exists, skip update
              if (currentIndex < 0) {
                return state;
              }
              
              // Check if local state has been updated during processing
              const currentQAPair = currentQAPairs[currentIndex];
              const optimisticQAPair = state.optimisticUpdates.get(qaPair.id);
              
              // If local version is newer than when we started processing, be careful with updates
              if (optimisticQAPair && 
                  optimisticQAPair.version !== undefined && 
                  currentQAPair.version !== undefined &&
                  optimisticQAPair.version > currentQAPair.version) {
                console.log('Local state has newer version, careful merge required');
                // We'll still add follow-up questions but preserve other local changes
              }
              
              // Add follow-up questions if provided
              if (response.followUpQuestions && response.followUpQuestions.length > 0) {
                // Add version and timestamp to follow-up questions
                const versionedFollowUps = response.followUpQuestions.map(q => ({
                  ...q,
                  version: 1,
                  lastUpdated: Date.now()
                }));
                
                // Filter out any potentially empty or invalid questions from backend
                const validFollowUps = versionedFollowUps.filter(q => {
                  // Ensure question has meaningful content
                  const hasValidQuestion = q.question && 
                                         q.question.trim().length > 10 && 
                                         q.question !== "placeholder";
                  // Ensure shortText is present
                  const hasValidShortText = q.shortText && q.shortText.trim().length > 0;
                  
                  if (!hasValidQuestion || !hasValidShortText) {
                    console.warn("Filtered out invalid follow-up question from backend:", q);
                    return false;
                  }
                  return true;
                });
                
                // Only add valid follow-up questions
                if (validFollowUps.length > 0) {
                  // Insert follow-up questions at the end of the array, not after current question
                  currentQAPairs.push(...validFollowUps);
                  
                  // Update the parent QA pair as processed with proper version increment
                  currentQAPairs[currentIndex] = {
                    ...currentQAPairs[currentIndex],
                    processed: true,
                    processingState: 'completed' as 'completed',
                    version: (currentQAPair.version || 0) + 1,
                    lastUpdated: Date.now()
                  };
                  
                  // Update progress
                  const progress = {
                    current: state.progress.current,
                    total: currentQAPairs.length
                  };
                  
                  // Remove from optimistic updates as server processing is complete
                  const newOptimisticUpdates = new Map(state.optimisticUpdates);
                  newOptimisticUpdates.delete(qaPair.id);
                  
                  // Schedule the next request processing with a slight delay to allow UI updates
                  setTimeout(() => {
                    // Sync the processing queue with QA pairs to ensure follow-up questions get processed
                    get().syncProcessingQueue();
                  }, 300);
                  
                  return { 
                    qaPairs: currentQAPairs, 
                    progress,
                    optimisticUpdates: newOptimisticUpdates
                  };
                } else {
                  console.log("No valid follow-up questions received from backend");
                  
                  // Still mark the current QA as processed, even if no follow-up questions were added
                  currentQAPairs[currentIndex] = {
                    ...currentQAPairs[currentIndex],
                    processed: true,
                    processingState: 'completed' as 'completed',
                    version: (currentQAPair.version || 0) + 1,
                    lastUpdated: Date.now()
                  };
                  
                  // Remove from optimistic updates
                  const newOptimisticUpdates = new Map(state.optimisticUpdates);
                  newOptimisticUpdates.delete(qaPair.id);
                  
                  // Since no valid follow-up questions, check if there are other unprocessed questions
                  setTimeout(() => {
                    get().syncProcessingQueue();
                  }, 300);
                  
                  return { 
                    qaPairs: currentQAPairs,
                    optimisticUpdates: newOptimisticUpdates 
                  };
                }
              }
              
              // Just mark as completed if no follow-up questions
              currentQAPairs[currentIndex] = {
                ...currentQAPairs[currentIndex],
                processed: true,
                processingState: 'completed' as 'completed',
                version: (currentQAPair.version || 0) + 1,
                lastUpdated: Date.now()
              };
              
              // Remove from optimistic updates
              const newOptimisticUpdates = new Map(state.optimisticUpdates);
              newOptimisticUpdates.delete(qaPair.id);
              
              // Since no valid follow-up questions, check if there are other unprocessed questions
              setTimeout(() => {
                get().syncProcessingQueue();
              }, 300);
              
              return { 
                qaPairs: currentQAPairs,
                optimisticUpdates: newOptimisticUpdates 
              };
            });
            
            // Mark request as completed
            get().updatePendingRequest(nextRequest.id, { status: 'completed' });
          } else {
            // Mark request as error
            get().updatePendingRequest(nextRequest.id, { 
              status: 'error', 
              error: response.error || 'Error processing request' 
            });
          }
        } catch (error) {
          console.error('Error processing async request:', error);
          get().updatePendingRequest(nextRequest.id, { 
            status: 'error', 
            error: error instanceof Error ? error.message : 'Unknown error' 
          });
        } finally {
          // Always release the lock
          set({ processingLock: false });
          
          // Schedule next processing with a delay
          setTimeout(() => {
            // Check again for pending requests
            const state = get();
            const hasPending = state.pendingRequests.some(req => req.status === 'pending');
            if (hasPending) {
              get().processNextPendingRequest();
            }
          }, 100);
        }
      },

      // Get all unprocessed QA pairs that have answers
      getUnprocessedQAs: () => {
        const state = get();
        return state.qaPairs.filter(qa => 
          !qa.processed && 
          qa.answer && 
          qa.answer.trim() !== '' &&
          qa.category !== 'tutorial'
        );
      },

      // Sync the processing queue with QA pairs
      syncProcessingQueue: () => {
        const state = get();
        
        // Find QA pairs that are answered but not processed
        const unprocessedQAs = state.getUnprocessedQAs();
        
        if (unprocessedQAs.length === 0) {
          return; // Nothing to sync
        }
        
        // Create a new queue based on unprocessed QAs
        const newQueue: PendingRequest[] = [];
        
        // Filter existing requests to keep only active ones
        const activeRequests = state.pendingRequests.filter(req => 
          req.status === 'pending' || req.status === 'processing'
        );
        
        // Add existing active requests to the new queue
        newQueue.push(...activeRequests);
        
        // Add requests for unprocessed QAs that aren't already in the queue
        const existingQAIds = new Set(activeRequests.map(req => req.qaPairId));
        
        for (const qa of unprocessedQAs) {
          if (!existingQAIds.has(qa.id)) {
            newQueue.push({
              id: `req_${uuidv4()}`,
              qaPairId: qa.id,
              timestamp: Date.now(),
              status: 'pending'
            });
          }
        }
        
        // Update the queue
        set({ pendingRequests: newQueue });
        
        // Start processing if there are requests and none are currently processing
        const isProcessing = activeRequests.some(req => req.status === 'processing');
        if (newQueue.length > 0 && !isProcessing) {
          setTimeout(() => get().processNextPendingRequest(), 100);
        }
      },

      // Check if there are any pending requests
      hasPendingRequests: () => {
        const state = get();
        // Include both pending and processing requests
        const hasPending = state.pendingRequests.some(req => 
          req.status === 'pending' || req.status === 'processing'
        );
        
        // Also check if there are any unprocessed QA pairs
        const hasUnprocessedQAs = state.getUnprocessedQAs().length > 0;
        
        // Consider as pending if either condition is true
        const result = hasPending || hasUnprocessedQAs;
        
        // Log for debugging
        if (result) {
          console.log("hasPendingRequests: true - ", 
            hasPending ? "Has pending/processing requests" : "Has unprocessed QAs");
        } else {
          console.log("hasPendingRequests: false - No pending work");
        }
        
        return result;
      },

      // Check if the last QA pair is answered
      isLastQAPairAnswered: () => {
        const state = get();
        const lastQAPair = state.qaPairs[state.qaPairs.length - 1];
        return Boolean(lastQAPair && lastQAPair.answer && lastQAPair.answer.trim() !== '');
      },

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

      // Modified addMessage to prevent duplicates
      addMessage: (message) =>
        set((state) => {
          // Check for possible duplicates
          const isDuplicate = state.messages.some(m => {
            // Check if message IDs have same QA reference or timestamps are very close
            const [msgType1, role1, qaId1, timestamp1] = m.id.split('_');
            const [msgType2, role2, qaId2, timestamp2] = message.id.split('_');
            
            // If both are answers (user messages) to same question in a short time window
            if (role1 === role2 && role1 === 'a' && qaId1 === qaId2 &&
                timestamp1 && timestamp2 &&
                Math.abs(parseInt(timestamp1) - parseInt(timestamp2)) < 1000) {
              return true;
            }
            
            // Or if text content and role are identical for very recent messages
            return m.role === message.role && 
                   m.text === message.text && 
                   Date.now() - parseInt(m.id.split('_')[3] || '0') < 1000;
          });
          
          if (isDuplicate) {
            console.log('Prevented duplicate message:', message.id);
            return state;
          }
          
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
            // Update existing pair with version control
            newQAPairs = newQAPairs.map((pair, index) => {
              if (index === state.currentQuestionIndex) {
                return {
                  ...pair,
                  answer: message.text,
                  version: (pair.version || 0) + 1,
                  lastUpdated: Date.now()
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
                  // Keep original ID but update text content
                  return {
                    ...msg,
                    text: updates.answer || ""
                  };
                }
              }
              return msg;
            });
            
            // If no corresponding message was found for update, might need to add a new message
            if (!messagesUpdated) {
              // In this case, we need to add a user answer message
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
          // Don't allow session creation here, only updates
          const result = await SyncService.syncSession(0, false)
          
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
