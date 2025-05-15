// Dependencies needed for this module:
// npm install mongodb mongoose
// npm install --save-dev @types/mongoose

import mongoose, { Schema, Document } from 'mongoose';

// Question interface - must match store.ts exactly
export interface IQuestion {
  id: string;
  text: string;
  shortText: string;
}

// QA Pair interface - must match store.ts exactly
export interface IQAPair {
  id: string;
  question: string;
  answer: string;
}

// Progress interface
export interface IProgress {
  current: number;
  total: number;
}

// Session document interface for MongoDB
export interface ISession extends Document {
  id: string;
  prolificId: string;
  status: string;
  messages: any[];
  qaPairs: any[];
  progress: {
    current: number;
    total: number;
  };
  currentQuestionIndex: number;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
  order?: number; // For drag-and-drop ordering
  topic?: string; // Research topic for the interview session
}

// Schema for Message objects
const MessageSchema = new Schema({
  id: { type: String, required: true },
  role: { type: String, enum: ['user', 'bot'], required: true },
  text: { type: String, required: true },
  loading: { type: Boolean }
});

// Schema for Question objects - must match store.ts
const QuestionSchema = new Schema({
  id: { type: String, required: true },
  text: { type: String, required: true },
  shortText: { type: String, required: true }
});

// Schema for QA Pair objects - must match store.ts
const QAPairSchema = new Schema({
  id: { type: String, required: true },
  question: { type: String, required: true },
  answer: { type: String, default: '' }
});

// Schema for Progress
const ProgressSchema = new Schema({
  current: { type: Number, default: 0 },
  total: { type: Number, default: 0 }
});

// Main Session schema
const SessionSchema = new Schema({
  id: { type: String, required: true, unique: true },
  prolificId: { type: String, required: true },
  status: { type: String, default: 'in_progress' },
  messages: { type: Array, default: [] },
  qaPairs: { type: Array, default: [] },
  progress: {
    current: { type: Number, default: 0 },
    total: { type: Number, default: 0 }
  },
  currentQuestionIndex: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now },
  completedAt: { type: Date },
  order: { type: Number }, // For drag-and-drop ordering
  topic: { type: String, default: 'climate change' } // Default research topic
});

// Check if model already exists (for hot reloading in development)
export default mongoose.models.Session || 
  mongoose.model<ISession>('Session', SessionSchema); 