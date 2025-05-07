import { NextResponse } from "next/server";
import connectToDatabase from "../../../lib/mongodb";
import Session from "../../../models/Session";
import CausalGraph, { ICausalGraphData } from "../../../models/CausalGraph";
import { v4 as uuidv4 } from 'uuid';

// Get Python backend URL - server-side only, not exposed to client
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:5000';

/**
 * Process Answer API
 * Sends user answer to Python backend for processing, retrieves causal graph and follow-up questions
 */
export async function POST(request: Request) {
  try {
    await connectToDatabase();
    
    const body = await request.json();
    const { sessionId, prolificId, qaPair, qaPairs, currentQuestionIndex } = body;

    if (!sessionId || !prolificId || !qaPair) {
      return NextResponse.json({ error: "Missing required parameters" }, { status: 400 });
    }

    // Find session to ensure it exists
    const session = await Session.findOne({ id: sessionId });
    
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 });
    }

    // Get all qaPairs from the session if not provided in request
    const allQaPairs = qaPairs || session.qaPairs || [];
    
    // Default current index to 0 if not provided
    const questionIndex = currentQuestionIndex !== undefined ? currentQuestionIndex : 0;

    // Call Python backend API for processing
    const pythonResponse = await fetch(`${PYTHON_BACKEND_URL}/api/process_answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sessionId,
        prolificId,
        qaPair,
        qaPairs: allQaPairs,
        currentQuestionIndex: questionIndex,
      }),
    });

    if (!pythonResponse.ok) {
      const errorData = await pythonResponse.json();
      console.error("Python backend processing failed:", errorData);
      return NextResponse.json(
        { error: "Error processing answer", details: errorData },
        { status: pythonResponse.status }
      );
    }

    const data = await pythonResponse.json();

    // Save causal graph to database
    if (data.causalGraph) {
      try {
        // Check if this is a valid causal graph according to our schema
        // If Python backend returns legacy format, transform it to new schema format
        const graphData = transformToSchemaFormat(data.causalGraph, sessionId, prolificId, qaPair);
        
        // Check if a graph already exists for this QA pair
        const existingGraph = await CausalGraph.findOne({
          sessionId,
          prolificId,
          qaPairId: qaPair.id
        });
        
        if (existingGraph) {
          // Update existing graph
          existingGraph.graphData = graphData;
          existingGraph.timestamp = new Date();
          await existingGraph.save();
          console.log(`Updated existing causal graph for QA pair: ${qaPair.id}`);
        } else {
          // Create new graph
          const newCausalGraph = new CausalGraph({
            sessionId,
            prolificId,
            qaPairId: qaPair.id,
            graphData,
            timestamp: new Date(data.timestamp * 1000 || Date.now())
          });
          
          await newCausalGraph.save();
          console.log(`Created new causal graph for QA pair: ${qaPair.id}`);
        }
      } catch (graphError) {
        console.error("Error saving causal graph:", graphError);
        // Continue with the rest of the processing even if graph saving fails
      }
    }

    // Update QA pair in session
    if (qaPair.id) {
      // Find and update the answer for the current QA pair in the session
      const updatedSession = await Session.findOneAndUpdate(
        { id: sessionId, "qaPairs.id": qaPair.id },
        { 
          $set: { 
            "qaPairs.$.answer": qaPair.answer,
            updatedAt: new Date()
          } 
        },
        { new: true }
      );

      // If follow-up questions are returned, add them to the session
      if (data.followUpQuestions && data.followUpQuestions.length > 0) {
        // Find index of current question
        const currentQuestionIndex = updatedSession.qaPairs.findIndex(
          (q: any) => q.id === qaPair.id
        );
        
        // Determine insertion position for follow-up questions
        const insertPosition = currentQuestionIndex + 1;
        
        // Prepare follow-up questions, ensuring no ID conflicts with existing questions
        const followUpQuestions = data.followUpQuestions.map((q: any, index: number) => {
          // Generate a unique ID with timestamp and UUID fragment to ensure uniqueness
          // This prevents ID collisions when multiple follow-up questions are added in quick succession
          const uniqueId = `${Date.now()}_${uuidv4().substring(0, 8)}`;
          return {
            ...q,
            id: q.id || `followup_${qaPair.id}_${index + 1}_${uniqueId}`
          };
        });
        
        // Insert follow-up questions into the session
        const newQaPairs = [
          ...updatedSession.qaPairs.slice(0, insertPosition),
          ...followUpQuestions,
          ...updatedSession.qaPairs.slice(insertPosition)
        ];
        
        // Update questions list and progress in the session
        await Session.findOneAndUpdate(
          { id: sessionId },
          { 
            $set: { 
              qaPairs: newQaPairs,
              progress: {
                current: updatedSession.progress.current,
                total: newQaPairs.length
              },
              updatedAt: new Date()
            } 
          },
          { new: true }
        );
      }
    }

    return NextResponse.json({
      success: true,
      data: data
    });
  } catch (error) {
    console.error("Error processing answer:", error);
    return NextResponse.json({ error: "Failed to process answer" }, { status: 500 });
  }
}

// Type definitions for transformation
interface LegacyNode {
  id?: string;
  label?: string;
  type?: string;
}

interface LegacyEdge {
  source: string;
  target: string;
  label?: string;
}

interface LegacyGraph {
  id?: string;
  nodes: LegacyNode[];
  edges: LegacyEdge[];
}

/**
 * Transform causal graph from Python backend format to schema format
 * Handles both the new schema format and the legacy format
 */
function transformToSchemaFormat(graphData: any, sessionId: string, prolificId: string, qaPair: any): ICausalGraphData {
  // If the graph data is already in the expected format with agent_id, nodes, edges, qas
  if (graphData.agent_id && graphData.nodes && graphData.edges && graphData.qas) {
    return graphData as ICausalGraphData;
  }
  
  // Otherwise, transform from the legacy format (simple nodes and edges arrays)
  const qaId = `qa_${qaPair.id}`;
  
  // Create a simplified causal graph following the schema
  const transformedGraph: ICausalGraphData = {
    agent_id: prolificId,
    nodes: {},
    edges: {},
    qas: []
  };
  
  // Cast to LegacyGraph for type safety
  const legacyGraph = graphData as LegacyGraph;
  
  // Transform nodes
  if (Array.isArray(legacyGraph.nodes)) {
    legacyGraph.nodes.forEach((node: LegacyNode, index: number) => {
      const nodeId = `n${index + 1}`; // Generate node ID if not present
      
      transformedGraph.nodes[nodeId] = {
        id: nodeId,
        label: node.label || `Node ${index + 1}`,
        type: "binary", // Default to binary
        values: [true, false],
        semantic_role: "external_state", // Default semantic role
        appearance: {
          qa_ids: [qaId],
          frequency: 1
        },
        incoming_edges: [],
        outgoing_edges: []
      };
    });
  }
  
  // Transform edges
  if (Array.isArray(legacyGraph.edges)) {
    legacyGraph.edges.forEach((edge: LegacyEdge, index: number) => {
      const edgeId = `e${index + 1}`; // Generate edge ID
      
      // Extract node numbers, default to basic IDs if parsing fails
      let sourceId = "n1";
      let targetId = "n2";
      
      try {
        sourceId = `n${parseInt(edge.source.replace('cause_', '')) + 1}`;
      } catch (e) {
        console.warn(`Could not parse source ID: ${edge.source}. Using default n1.`);
      }
      
      try {
        targetId = `n${parseInt(edge.target.replace('effect_', '')) + 1}`;
      } catch (e) {
        console.warn(`Could not parse target ID: ${edge.target}. Using default n2.`);
      }
      
      // Add edge to outgoing/incoming lists of nodes
      if (transformedGraph.nodes[sourceId]) {
        transformedGraph.nodes[sourceId].outgoing_edges.push(edgeId);
      }
      
      if (transformedGraph.nodes[targetId]) {
        transformedGraph.nodes[targetId].incoming_edges.push(edgeId);
      }
      
      // Add the edge with basic function
      transformedGraph.edges[edgeId] = {
        from: sourceId,
        to: targetId,
        function: {
          target: targetId,
          inputs: [sourceId],
          function_type: "sigmoid",
          parameters: {
            weights: [1.0],
            bias: 0.0
          },
          noise_std: 0.1,
          support_qas: [qaId]
        },
        support_qas: [qaId]
      };
    });
  }
  
  // Find first two nodes for default values
  const nodeIds = Object.keys(transformedGraph.nodes);
  const firstNodeId = nodeIds.length > 0 ? nodeIds[0] : "n1";
  const secondNodeId = nodeIds.length > 1 ? nodeIds[1] : "n2";
  
  // Add QA pair
  transformedGraph.qas.push({
    qa_id: qaId,
    question: qaPair.question,
    answer: qaPair.answer,
    parsed_belief: {
      belief_structure: {
        from: firstNodeId,
        to: secondNodeId,
        direction: "positive"
      },
      belief_strength: {
        estimated_probability: 0.7,
        confidence_rating: 0.6
      },
      counterfactual: ""
    }
  });
  
  return transformedGraph;
} 