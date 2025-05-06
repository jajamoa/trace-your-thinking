import mongoose, { Schema, Document } from 'mongoose';

// Interface for a node in the causal graph
interface INode {
  id: string;
  label: string;
  type: string;
}

// Interface for an edge in the causal graph
interface IEdge {
  source: string;
  target: string;
  label: string;
}

// Interface for the causal graph data
export interface ICausalGraphData {
  id: string;
  nodes: INode[];
  edges: IEdge[];
}

// Causal graph document interface for MongoDB
export interface ICausalGraph extends Document {
  sessionId: string;
  prolificId: string;
  qaPairId: string;
  graphData: ICausalGraphData;
  timestamp: Date;
}

// Schema for a node in the causal graph
const NodeSchema = new Schema({
  id: { type: String, required: true },
  label: { type: String, required: true },
  type: { type: String, required: true }
});

// Schema for an edge in the causal graph
const EdgeSchema = new Schema({
  source: { type: String, required: true },
  target: { type: String, required: true },
  label: { type: String, required: true }
});

// Schema for the causal graph data
const CausalGraphDataSchema = new Schema({
  id: { type: String, required: true },
  nodes: [NodeSchema],
  edges: [EdgeSchema]
});

// Main CausalGraph schema
const CausalGraphSchema = new Schema({
  sessionId: { type: String, required: true },
  prolificId: { type: String, required: true },
  qaPairId: { type: String, required: true },
  graphData: { type: CausalGraphDataSchema, required: true },
  timestamp: { type: Date, default: Date.now }
});

// Create an index for efficient queries
CausalGraphSchema.index({ sessionId: 1, prolificId: 1, qaPairId: 1 });

// Check if model already exists (for hot reloading in development)
export default mongoose.models.CausalGraph || 
  mongoose.model<ICausalGraph>('CausalGraph', CausalGraphSchema); 