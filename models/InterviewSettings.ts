import mongoose, { Schema, Document } from 'mongoose';

export interface IInterviewSettings extends Document {
  defaultTopic: string;
  updatedAt: Date;
}

const InterviewSettingsSchema = new Schema({
  defaultTopic: { 
    type: String, 
    default: 'policy',
    required: true
  },
  updatedAt: { 
    type: Date, 
    default: Date.now 
  }
});

// Check if model already exists (for hot reloading in development)
export default mongoose.models.InterviewSettings || 
  mongoose.model<IInterviewSettings>('InterviewSettings', InterviewSettingsSchema); 