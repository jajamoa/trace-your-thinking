import OpenAI from 'openai';

// Initialize the OpenAI client
export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Define types for the Whisper API response
export interface WhisperSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  confidence?: number;
}

export interface WhisperResponse {
  text: string;
  segments?: WhisperSegment[];
  language?: string;
} 