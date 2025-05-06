"use client"

import { useStore } from './store'

/**
 * Debug utility function to log the current state of useStore to the console
 */
export function logStoreState() {
  const store = useStore.getState()
  
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
  
  return store
}

/**
 * Creates a subscription to automatically log store state changes
 */
export function setupStoreLogger() {
  if (typeof window !== 'undefined') {
    useStore.subscribe(
      (state) => {
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
    )
    console.log('Store logger has been setup')
  }
} 