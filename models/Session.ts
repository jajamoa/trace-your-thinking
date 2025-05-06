// Dependencies needed for this module:
// npm install mongodb mongoose
// npm install --save-dev @types/mongoose

import mongoose, { Schema, Document } from 'mongoose';
import { Question } from '@/lib/store';

export interface IQAPair {
  id: string;
  question: string;
  answer: string;
  timestamp?: Date;
}

// Interface for Question objects stored in pendingQuestions
export interface IQuestion {
  id: string;
  text: string;
  shortText: string;
}

export interface ISession extends Document {
  id: string;
  prolificId: string;
  qaPairs: IQAPair[];
  pendingQuestions: IQuestion[]; // Added to match store.ts
  questions: IQuestion[]; // Master list of all questions
  createdAt: Date;
  updatedAt: Date;
  status: 'in_progress' | 'completed' | 'reviewed';
  currentQuestionIndex?: number; // Kept for backward compatibility
  metadata?: Record<string, any>;
}

const QAPairSchema = new Schema({
  id: { type: String, required: true },
  question: { type: String, required: true },
  answer: { type: String, default: '' },
  timestamp: { type: Date, default: Date.now }
});

// Schema for Question objects
const QuestionSchema = new Schema({
  id: { type: String, required: true },
  text: { type: String, required: true },
  shortText: { type: String, required: true }
});

const SessionSchema = new Schema({
  id: { type: String, required: true, unique: true },
  prolificId: { type: String, required: true, index: true },
  qaPairs: [QAPairSchema],
  // Added pendingQuestions to store questions that haven't been answered yet
  pendingQuestions: [QuestionSchema],
  // Master list of all questions for this session
  questions: [QuestionSchema],
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now },
  status: { 
    type: String, 
    enum: ['in_progress', 'completed', 'reviewed'], 
    default: 'in_progress' 
  },
  // Retained for backward compatibility
  currentQuestionIndex: { type: Number, default: 0 },
  metadata: { type: Map, of: Schema.Types.Mixed }
}, { timestamps: true });

// Check if model already exists (for hot reloading in development)
export default mongoose.models.Session || mongoose.model<ISession>('Session', SessionSchema); 