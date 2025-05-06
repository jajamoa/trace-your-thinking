import mongoose, { Schema, Document } from 'mongoose';

// Interface for node appearance in the graph
interface INodeAppearance {
  qa_ids: string[];
  frequency: number;
}

// Interface for a node in the causal graph
interface INode {
  id: string;
  label: string;
  type: string;
  range?: number[];          // Required if type is "continuous"
  values?: boolean[];        // Required if type is "binary"
  semantic_role: string;     // "external_state", "internal_affect", or "behavioral_intention"
  appearance: INodeAppearance;
  incoming_edges: string[];
  outgoing_edges: string[];
}

// Interface for function parameters
interface IFunctionParameters {
  weights?: number[];      // For sigmoid function
  bias?: number;           // For sigmoid function
  threshold?: number;      // For threshold function
  direction?: string;      // For threshold function: "less", "greater", "equal"
}

// Interface for edge function
interface IEdgeFunction {
  target: string;
  inputs: string[];
  function_type: string;   // "sigmoid" or "threshold"
  parameters: IFunctionParameters;
  noise_std: number;
  support_qas: string[];
  confidence?: number;
}

// Interface for an edge in the causal graph
interface IEdge {
  from: string;
  to: string;
  function: IEdgeFunction;
  support_qas: string[];
}

// Interface for belief structure
interface IBeliefStructure {
  from: string;
  to: string;
  direction: string;      // "positive" or "negative"
}

// Interface for belief strength
interface IBeliefStrength {
  estimated_probability: number;
  confidence_rating: number;
}

// Interface for parsed belief
interface IParsedBelief {
  belief_structure: IBeliefStructure;
  belief_strength: IBeliefStrength;
  counterfactual?: string;
}

// Interface for QA pair
interface IQA {
  qa_id: string;
  question: string;
  answer: string;
  parsed_belief: IParsedBelief;
}

// Interface for the causal graph data
export interface ICausalGraphData {
  agent_id: string;
  nodes: { [nodeId: string]: INode };
  edges: { [edgeId: string]: IEdge };
  qas: IQA[];
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

// Node appearance schema
const NodeAppearanceSchema = new Schema({
  qa_ids: [{ type: String }],
  frequency: { type: Number, default: 1 }
});

// Node schema
const NodeSchema = new Schema({
  id: { type: String, required: true },
  label: { type: String, required: true },
  type: { type: String, enum: ['binary', 'continuous'], required: true },
  range: [{ type: Number }],  // For continuous nodes
  values: [{ type: Boolean }], // For binary nodes
  semantic_role: { 
    type: String, 
    enum: ['external_state', 'internal_affect', 'behavioral_intention'], 
    required: true 
  },
  appearance: { type: NodeAppearanceSchema, required: true },
  incoming_edges: [{ type: String }],
  outgoing_edges: [{ type: String }]
});

// Function parameters schema
const FunctionParametersSchema = new Schema({
  weights: [{ type: Number }],
  bias: { type: Number },
  threshold: { type: Number },
  direction: { type: String, enum: ['less', 'greater', 'equal'] }
}, { _id: false });

// Edge function schema
const EdgeFunctionSchema = new Schema({
  target: { type: String, required: true },
  inputs: [{ type: String, required: true }],
  function_type: { type: String, enum: ['sigmoid', 'threshold'], required: true },
  parameters: { type: FunctionParametersSchema, required: true },
  noise_std: { type: Number, required: true },
  support_qas: [{ type: String }],
  confidence: { type: Number }
});

// Edge schema
const EdgeSchema = new Schema({
  from: { type: String, required: true },
  to: { type: String, required: true },
  function: { type: EdgeFunctionSchema, required: true },
  support_qas: [{ type: String, required: true }]
});

// Belief structure schema
const BeliefStructureSchema = new Schema({
  from: { type: String, required: true },
  to: { type: String, required: true },
  direction: { type: String, enum: ['positive', 'negative'], required: true }
});

// Belief strength schema
const BeliefStrengthSchema = new Schema({
  estimated_probability: { type: Number, required: true },
  confidence_rating: { type: Number, required: true }
});

// Parsed belief schema
const ParsedBeliefSchema = new Schema({
  belief_structure: { type: BeliefStructureSchema, required: true },
  belief_strength: { type: BeliefStrengthSchema, required: true },
  counterfactual: { type: String }
});

// QA schema
const QASchema = new Schema({
  qa_id: { type: String, required: true },
  question: { type: String, required: true },
  answer: { type: String, required: true },
  parsed_belief: { type: ParsedBeliefSchema, required: true }
});

// Schema for the complete causal graph data
const CausalGraphDataSchema = new Schema({
  agent_id: { type: String, required: true },
  nodes: { type: Schema.Types.Mixed, required: true }, // Map of nodeId to node object
  edges: { type: Schema.Types.Mixed, required: true }, // Map of edgeId to edge object
  qas: [{ type: QASchema, required: true }]
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