import mongoose, { Schema, Document } from 'mongoose';

export interface IGuidingQuestion extends Document {
  id: string;
  text: string;
  shortText: string;
  category?: string;
  isActive: boolean;
  order: number;
  createdAt: Date;
  updatedAt: Date;
}

const GuidingQuestionSchema = new Schema({
  id: { type: String, required: true, unique: true },
  text: { type: String, required: true },
  shortText: { type: String, required: true },
  category: { type: String },
  isActive: { type: Boolean, default: true },
  order: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
}, { 
  timestamps: true 
});

// Check if model already exists (for hot reloading in development)
export default mongoose.models.GuidingQuestion || 
  mongoose.model<IGuidingQuestion>('GuidingQuestion', GuidingQuestionSchema); 