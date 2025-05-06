"use client"

import { useStore } from './store'

// Track the last logged state to avoid repetitive logs
let lastLoggedState = ''

/**
 * Debug utility function to log the current state of useStore to the console
 */
export function logStoreState() {
  const store = useStore.getState()
  
  // Create a simple representation of the current state
  const stateSnapshot = JSON.stringify({
    sessionId: store.sessionId,
    prolificId: store.prolificId,
    messagesCount: store.messages.length,
    qaPairsCount: store.qaPairs.length,
    pendingQuestionsCount: store.pendingQuestions.length
  })
  
  // Only log if state has changed
  if (stateSnapshot !== lastLoggedState) {
    lastLoggedState = stateSnapshot
    
    console.log('===== useStore Current State =====')
    console.log('sessionId:', store.sessionId)
    console.log('prolificId:', store.prolificId)
    console.log('messages count:', store.messages.length)
    console.log('qaPairs count:', store.qaPairs.length)
    console.log('pendingQuestions count:', store.pendingQuestions.length)
    console.log('isRecording:', store.isRecording)
    console.log('progress:', store.progress)
    console.log('sessionStatus:', store.sessionStatus)
    console.log('qaPairs:', JSON.stringify(store.qaPairs, null, 2))
    console.log('================================')
  }
  
  return store
}

// Track the last subscription update to avoid repetitive logs
let lastSubscriptionUpdate = ''

/**
 * Creates a subscription to automatically log store state changes
 */
export function setupStoreLogger() {
  if (typeof window !== 'undefined') {
    useStore.subscribe(
      (state) => {
        // Create a simple representation of the current state
        const stateSnapshot = JSON.stringify({
          sessionId: state.sessionId,
          prolificId: state.prolificId,
          messagesCount: state.messages.length,
          qaPairsCount: state.qaPairs.length,
          pendingQuestionsCount: state.pendingQuestions.length
        })
        
        // Only log if state has changed significantly
        if (stateSnapshot !== lastSubscriptionUpdate) {
          lastSubscriptionUpdate = stateSnapshot
          
          console.log('===== useStore State Updated =====')
          console.log('sessionId:', state.sessionId)
          console.log('prolificId:', state.prolificId)
          console.log('messages count:', state.messages.length)
          console.log('qaPairs count:', state.qaPairs.length)
          console.log('pendingQuestions count:', state.pendingQuestions.length)
          console.log('isRecording:', state.isRecording)
          console.log('progress:', state.progress)
          console.log('sessionStatus:', state.sessionStatus)
          console.log('================================')
        }
      }
    )
    console.log('Store logger has been setup')
  }
} 