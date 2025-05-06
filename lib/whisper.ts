// Mock implementation of OpenAI Whisper API integration
// In a real application, this would connect to a backend service

import { WhisperResponse } from './openai-client';

export interface WhisperTranscriptionResult {
  text: string
  segments: Array<{
    id: number
    start: number
    end: number
    text: string
    confidence: number
  }>
  language: string
}

/**
 * Sends audio to the Whisper API for transcription
 * @param audioBlob The audio recording as a Blob
 * @returns A promise that resolves to the transcription result
 */
export async function transcribeAudio(audioBlob: Blob): Promise<WhisperTranscriptionResult> {
  console.log("Transcribing audio with size:", audioBlob.size)
  
  try {
    // Send the audio to our backend API
    return await sendAudioToWhisperAPI(audioBlob)
  } catch (error) {
    console.error("Transcription error:", error)
    throw error
  }
}

/**
 * Sends audio to our backend Whisper API endpoint
 */
export async function sendAudioToWhisperAPI(audioBlob: Blob): Promise<WhisperTranscriptionResult> {
  // Create a form to send the audio file
  const formData = new FormData()
  formData.append('file', audioBlob, 'recording.webm')
  formData.append('model', 'whisper-1')
  formData.append('language', 'en')

  console.log("Sending audio to Whisper API endpoint")
  
  try {
    const response = await fetch('/api/whisper/transcribe', {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Whisper API error (${response.status}): ${errorText}`)
    }
    
    const result = await response.json()
    console.log("Transcription received:", result.text.substring(0, 50) + "...")
    
    // If the API doesn't return segments, create a single segment
    if (!result.segments || result.segments.length === 0) {
      result.segments = [
        {
          id: 0,
          start: 0,
          end: 1,
          text: result.text,
          confidence: 0.9
        }
      ]
    }
    
    return {
      text: result.text,
      segments: result.segments,
      language: result.language || "en"
    }
  } catch (error) {
    console.error("Error sending audio to Whisper API:", error)
    throw error
  }
}
