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
  // Unique identifiers
  id: string;
  prolificId: string;
  
  // Core data - exactly matching store.ts
  messages: Array<{
    id: string;
    role: "user" | "bot";
    text: string;
    loading?: boolean;
  }>;
  qaPairs: IQAPair[];
  pendingQuestions: IQuestion[];
  questions: IQuestion[];
  
  // Status and progress
  progress: IProgress;
  status: 'in_progress' | 'completed';
  
  // Timestamps
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
  
  // Legacy field (kept for backward compatibility)
  currentQuestionIndex?: number;
  
  // Optional metadata
  metadata?: Record<string, any>;
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
  // Unique identifiers
  id: { type: String, required: true, unique: true },
  prolificId: { type: String, required: true, index: true },
  
  // Core data structures
  messages: [MessageSchema],
  qaPairs: [QAPairSchema],
  pendingQuestions: [QuestionSchema],
  questions: [QuestionSchema],
  
  // Status and progress
  progress: { type: ProgressSchema, default: { current: 0, total: 0 } },
  status: { 
    type: String, 
    enum: ['in_progress', 'completed'], 
    default: 'in_progress' 
  },
  
  // Timestamps
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now },
  completedAt: { type: Date },
  
  // Legacy fields (for backward compatibility)
  currentQuestionIndex: { type: Number, default: 0 },
  
  // Additional metadata
  metadata: { type: Map, of: Schema.Types.Mixed }
}, { 
  timestamps: true 
});

// Check if model already exists (for hot reloading in development)
export default mongoose.models.Session || mongoose.model<ISession>('Session', SessionSchema); 