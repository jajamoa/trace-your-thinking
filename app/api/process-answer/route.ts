import { NextResponse } from "next/server";
import connectToDatabase from "../../../lib/mongodb";
import Session from "../../../models/Session";
import CausalGraph from "../../../models/CausalGraph";
import InterviewSettings from "../../../models/InterviewSettings";
import { v4 as uuidv4 } from 'uuid';

// Get Python backend URL - server-side only, not exposed to client
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:5000';

/**
 * Get the default interview topic from settings
 */
async function getDefaultTopic(): Promise<string> {
  try {
    // Find settings or create default if not exists
    let settings = await InterviewSettings.findOne();
    
    if (!settings) {
      return "policy";  // Default fallback
    }
    
    return settings.defaultTopic || "policy";
  } catch (error) {
    console.error("Error fetching default topic:", error);
    return "policy";  // Default fallback on error
  }
}

/**
 * Ensure the causal graph has exactly one stance node
 */
function ensureStanceNode(graphData: any, topic: string): any {
  if (!graphData || !graphData.nodes) {
    return graphData;
  }
  
  // Sanitize topic value - default to "policy" if none or invalid
  const sanitizedTopic = (!topic || topic.toLowerCase() === "none") ? "policy" : topic;
  const defaultLabel = `Support for ${sanitizedTopic}`;
  
  // Identify all stance nodes
  let stanceNodes: string[] = [];
  
  for (const nodeId in graphData.nodes) {
    if (graphData.nodes[nodeId].is_stance === true) {
      stanceNodes.push(nodeId);
    }
  }
  
  // Handle based on number of stance nodes found
  if (stanceNodes.length === 0) {
    // No stance node exists, create one
    console.log(`Adding default stance node with topic: ${sanitizedTopic}`);
    const stanceNodeId = `n_${Date.now().toString(16)}`;
    graphData.nodes[stanceNodeId] = {
      id: stanceNodeId,
      label: defaultLabel,
      is_stance: true,
      confidence: 1.0,
      source_qa: [],
      incoming_edges: [],
      outgoing_edges: []
    };
  } 
  else if (stanceNodes.length > 1) {
    // Multiple stance nodes detected - keep the best one and remove others
    console.log(`Detected ${stanceNodes.length} stance nodes. Removing duplicates.`);
    
    // Sort nodes to determine which to keep - prioritize nodes with more connections
    const sortedNodes = stanceNodes.sort((nodeIdA, nodeIdB) => {
      // Safely get node data
      const nodeA = graphData.nodes[nodeIdA];
      const nodeB = graphData.nodes[nodeIdB];
      
      // Prefer nodes with more incoming connections
      const incomingA = nodeA.incoming_edges?.length || 0;
      const incomingB = nodeB.incoming_edges?.length || 0;
      
      return incomingB - incomingA;
    });
    
    // Keep the first (best) node
    const keepNodeId = sortedNodes[0];
    const keptNode = graphData.nodes[keepNodeId];
    
    // ALWAYS set the stance node label to use the database topic
    keptNode.label = defaultLabel;
    console.log(`Set stance node label to "${defaultLabel}"`);
    
    // Remove all other stance nodes
    for (let i = 1; i < sortedNodes.length; i++) {
      const removeNodeId = sortedNodes[i];
      
      // Before removing, transfer any incoming edges to the kept node
      const nodeToRemove = graphData.nodes[removeNodeId];
      if (nodeToRemove.incoming_edges && nodeToRemove.incoming_edges.length > 0) {
        // For each incoming edge to the node being removed
        for (const edgeId of nodeToRemove.incoming_edges) {
          if (graphData.edges[edgeId]) {
            // Update the edge to point to the kept node
            graphData.edges[edgeId].target = keepNodeId;
            
            // Add this edge to the kept node's incoming edges
            if (!graphData.nodes[keepNodeId].incoming_edges.includes(edgeId)) {
              graphData.nodes[keepNodeId].incoming_edges.push(edgeId);
            }
          }
        }
      }
      
      // Remove the node
      delete graphData.nodes[removeNodeId];
      
      // Clean up any edges that pointed to this node
      for (const edgeId in graphData.edges) {
        if (graphData.edges[edgeId].source === removeNodeId ||
            graphData.edges[edgeId].target === removeNodeId) {
          delete graphData.edges[edgeId];
        }
      }
    }
  } else {
    // Single stance node - ALWAYS set label to use database topic
    const nodeId = stanceNodes[0];
    const node = graphData.nodes[nodeId];
    node.label = defaultLabel;
    console.log(`Updated stance node label to "${defaultLabel}"`);
  }
  
  return graphData;
}

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

    // Get the database topic - this is the ONLY source of topic now
    const defaultTopic = await getDefaultTopic();

    // Get all qaPairs from the session if not provided in request
    const allQaPairs = qaPairs || session.qaPairs || [];
    
    // Default current index to 0 if not provided
    const questionIndex = currentQuestionIndex !== undefined ? currentQuestionIndex : 0;

    // Try to get the latest causal graph from the database
    let existingCausalGraph = null;
    try {
      const latestGraph = await CausalGraph.findOne({ 
        sessionId, 
        prolificId 
      }).sort({ timestamp: -1 });  // Get the most recent graph
      
      if (latestGraph && latestGraph.graphData) {
        console.log(`Found existing causal graph for session ${sessionId}`);
        existingCausalGraph = latestGraph.graphData;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.warn(`Could not fetch existing causal graph: ${errorMessage}`);
      // Proceed without the existing graph
    }

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
        existingCausalGraph,  // Include the latest causal graph if available
        defaultTopic          // Always pass the database topic
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

    // Ensure the causal graph has a stance node with the database topic
    if (data.causalGraph) {
      data.causalGraph = ensureStanceNode(data.causalGraph, defaultTopic);
    }

    // Save causal graph to database if present
    if (data.causalGraph) {
      try {
        console.log("Attempting to save causal graph to database...");
        console.log(`QA pair ID: ${qaPair.id}, Session ID: ${sessionId}, Prolific ID: ${prolificId}`);
        
        if (!qaPair.id) {
          console.error("Cannot save causal graph: Missing qaPair.id");
          throw new Error("QA pair ID is required to save causal graph");
        }
        
        // Check if a graph already exists for this QA pair
        const existingGraph = await CausalGraph.findOne({
          sessionId,
          prolificId,
          qaPairId: qaPair.id
        });
        
        if (existingGraph) {
          // Update existing graph
          existingGraph.graphData = data.causalGraph;
          existingGraph.timestamp = new Date();
          await existingGraph.save();
          console.log(`Updated existing causal graph for QA pair: ${qaPair.id}`);
        } else {
          // Create new graph
          const newCausalGraph = new CausalGraph({
            sessionId,
            prolificId,
            qaPairId: qaPair.id,
            graphData: data.causalGraph,
            timestamp: new Date()
          });
          
          const savedGraph = await newCausalGraph.save();
          console.log(`Created new causal graph for QA pair: ${qaPair.id}`);
          console.log(`Graph saved with ID: ${savedGraph._id}`);
        }
      } catch (graphError) {
        const errorMessage = graphError instanceof Error ? graphError.message : String(graphError);
        console.error(`Error saving causal graph: ${errorMessage}`);
        console.error("Stack trace:", graphError instanceof Error ? graphError.stack : "No stack trace");
      }
    } else {
      console.warn("No causal graph returned from Python backend to save");
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