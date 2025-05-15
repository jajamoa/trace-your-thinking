import mongoose, { Schema, Document } from 'mongoose';

// Interface for evidence on an edge or node
interface IEvidence {
  qa_id: string;
  confidence: number;
  importance?: number;  // Only for node evidence
}

// Interface for a node in the causal graph
interface INode {
  id: string;
  label: string;
  is_stance: boolean;         // True if this is a stance node, false otherwise
  aggregate_confidence: number;  // Aggregate confidence score (0.0-1.0)
  evidence: IEvidence[];      // Evidence that supports this node
  incoming_edges: string[];
  outgoing_edges: string[];
  status?: 'candidate' | 'anchor';  // Node status - candidate or anchor
}

// Interface for an edge in the causal graph
interface IEdge {
  source: string;            // ID of source node
  target: string;            // ID of target node
  aggregate_confidence: number;  // Aggregate confidence from all evidence
  evidence: IEvidence[];     // Supporting evidence
  modifier: number;          // Range: -1.0 to 1.0, negative = prevents, positive = causes
}

// Interface for extracted causal pair
interface IExtractedPair {
  source: string;            // Source label
  target: string;            // Target label
  confidence: number;        // Confidence in this extraction
}

// Interface for QA pair with extracted causal relations
interface IQA {
  question: string;
  answer: string;
  extracted_pairs: IExtractedPair[];
}

// Interface for the causal graph data
export interface ICausalGraphData {
  agent_id: string;
  nodes: { [nodeId: string]: INode };
  edges: { [edgeId: string]: IEdge };
  qa_history: { [qaId: string]: IQA };
  timestamp?: number; // Numeric timestamp in milliseconds for synchronization
  
  // Additional fields from backend CBN structure
  stance_node_id?: string;
  step?: string;
  anchor_queue?: string[];
  node_counter?: number;
  edge_counter?: number;
  qa_counter?: number;
}

// Causal graph document interface for MongoDB
export interface ICausalGraph extends Document {
  sessionId: string;
  prolificId: string;
  qaPairId: string;
  graphData: ICausalGraphData;
  timestamp: Date;
}

// Schema definitions for MongoDB

// Evidence schema - define this first as it's used by other schemas
const EvidenceSchema = new Schema({
  qa_id: { type: String, required: true },
  confidence: { type: Number, required: true },
  importance: { type: Number }
}, { _id: false });

// Extracted pair schema
const ExtractedPairSchema = new Schema({
  source: { type: String, required: true },
  target: { type: String, required: true },
  confidence: { type: Number, required: true }
}, { _id: false });

// QA schema
const QASchema = new Schema({
  question: { type: String, required: true },
  answer: { type: String, required: true },
  extracted_pairs: [{ type: ExtractedPairSchema }]
});

// Node schema
const NodeSchema = new Schema({
  id: { type: String, required: true },
  label: { type: String, required: true },
  is_stance: { type: Boolean, default: false },
  aggregate_confidence: { type: Number, default: 0.9 },
  evidence: [EvidenceSchema],
  incoming_edges: [{ type: String }],
  outgoing_edges: [{ type: String }],
  status: { type: String, enum: ['candidate', 'anchor'], default: 'anchor' }
});

// Edge schema
const EdgeSchema = new Schema({
  source: { type: String, required: true },
  target: { type: String, required: true },
  aggregate_confidence: { type: Number, required: true },
  evidence: [EvidenceSchema],
  modifier: { type: Number, required: true }
});

// Schema for the complete causal graph data
const CausalGraphDataSchema = new Schema({
  agent_id: { type: String, required: true },
  nodes: { type: Schema.Types.Mixed, required: true }, // Map of nodeId to node object
  edges: { type: Schema.Types.Mixed, required: true }, // Map of edgeId to edge object
  qa_history: { type: Schema.Types.Mixed, required: true }, // Map of qaId to QA object
  timestamp: { type: Number }, // Numeric timestamp in milliseconds for synchronization
  
  // Additional fields from backend CBN structure
  stance_node_id: { type: String },
  step: { type: String },
  anchor_queue: [{ type: String }], // Array of node IDs
  node_counter: { type: Number },
  edge_counter: { type: Number },
  qa_counter: { type: Number }
});

// Main CausalGraph schema
const CausalGraphSchema = new Schema({
  sessionId: { type: String, required: true },
  prolificId: { type: String, required: true },
  qaPairId: { type: String, required: true },
  graphData: { type: CausalGraphDataSchema, required: true },
  timestamp: { type: Date, default: Date.now }
});

// Create indexes for efficient queries
CausalGraphSchema.index({ sessionId: 1, prolificId: 1, qaPairId: 1 });
CausalGraphSchema.index({ 'graphData.agent_id': 1 });

// Check if model already exists (for hot reloading in development)
export default mongoose.models.CausalGraph || 
  mongoose.model<ICausalGraph>('CausalGraph', CausalGraphSchema); 