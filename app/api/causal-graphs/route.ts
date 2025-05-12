import { NextResponse } from "next/server";
import connectToDatabase from "../../../lib/mongodb";
import CausalGraph from "../../../models/CausalGraph";
import InterviewSettings from "../../../models/InterviewSettings";

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
 * Interface for the frontend graph data format
 */
interface FrontendGraphData {
  agent_id: string;
  nodes: Record<string, any>;
  edges: Record<string, any>;
  qa_history: Record<string, any>;
}

/**
 * Determine if data is in CBN format
 */
function isCBNFormat(data: any): boolean {
  return data && 
         data.nodes && 
         data.edges && 
         data.qa_history && 
         typeof data.nodes === 'object' && 
         typeof data.edges === 'object' && 
         typeof data.qa_history === 'object';
}

/**
 * Ensure the causal graph has exactly one stance node
 */
function ensureStanceNode(graphData: FrontendGraphData, topic: string): FrontendGraphData {
  // Check if graph data is valid
  if (!graphData || !graphData.nodes) {
    return graphData;
  }
  
  // Sanitize topic value - default to "policy" if none or invalid
  const sanitizedTopic = (!topic || topic.toLowerCase() === "none") ? "policy" : topic;
  const defaultLabel = `Support for ${sanitizedTopic}`;
  
  // Identify all stance nodes
  let stanceNodes: string[] = [];
  
  for (const [nodeId, node] of Object.entries(graphData.nodes)) {
    if (node.is_stance === true) {
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
    
    // Sort nodes to determine which to keep based on incoming connections
    const sortedNodes = stanceNodes.sort((nodeIdA, nodeIdB) => {
      // Get nodes
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
    
    // ALWAYS set label to database topic
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
    // Single stance node - ALWAYS set label to database topic
    const nodeId = stanceNodes[0];
    const node = graphData.nodes[nodeId];
    node.label = defaultLabel;
    console.log(`Updated stance node label to "${defaultLabel}"`);
  }
  
  return graphData;
}

/**
 * Causal Graph API
 * Get causal graphs related to a session ID or user ID
 */
export async function GET(request: Request) {
  try {
    await connectToDatabase();
    
    const { searchParams } = new URL(request.url);
    const sessionId = searchParams.get("sessionId");
    const prolificId = searchParams.get("prolificId");
    const qaPairId = searchParams.get("qaPairId");
    // Topic parameter is ignored - always use database topic

    // At least sessionId or prolificId must be provided
    if (!sessionId && !prolificId) {
      return NextResponse.json({ error: "Either sessionId or prolificId parameter is required" }, { status: 400 });
    }
    
    // Always get the default topic from database
    const defaultTopic = await getDefaultTopic();
    
    // Build query conditions
    const query: any = {};
    
    if (sessionId) {
      query.sessionId = sessionId;
    }
    
    if (prolificId) {
      query.prolificId = prolificId;
    }
    
    if (qaPairId) {
      query.qaPairId = qaPairId;
    }
    
    // Query database to get causal graphs
    const causalGraphs = await CausalGraph.find(query).sort({ timestamp: -1 });
    
    // Process graphs and ensure each has a stance node with the database topic
    const processedGraphs = causalGraphs.map(graph => {
      let graphData = graph.graphData;
      
      // Ensure the graph has a stance node with the database topic
      graphData = ensureStanceNode(graphData, defaultTopic);
      
      // Create a new graph object with the processed data
      return {
        ...graph.toObject(),
        graphData
      };
    });
    
    return NextResponse.json({
      success: true,
      causalGraphs: processedGraphs
    });
  } catch (error) {
    console.error("Error fetching causal graphs:", error);
    return NextResponse.json({ error: "Failed to fetch causal graphs" }, { status: 500 });
  }
}

/**
 * Save a causal graph
 * Stores causal graph data generated from Python backend
 */
export async function POST(request: Request) {
  try {
    await connectToDatabase();
    
    const data = await request.json();
    const { sessionId, prolificId, qaPairId, graphData } = data;
    // Topic parameter is ignored - always use database topic
    
    // Validate required fields
    if (!sessionId || !prolificId || !qaPairId || !graphData) {
      return NextResponse.json(
        { error: "Missing required fields: sessionId, prolificId, qaPairId, and graphData are required" }, 
        { status: 400 }
      );
    }
    
    // Always get the default topic from database
    const defaultTopic = await getDefaultTopic();
    
    // Ensure the graph has a stance node with the database topic
    const processedGraphData = ensureStanceNode(graphData, defaultTopic);
    
    // Check if a graph already exists for this QA pair
    const existingGraph = await CausalGraph.findOne({
      sessionId,
      prolificId,
      qaPairId
    });
    
    if (existingGraph) {
      // Update existing graph
      existingGraph.graphData = processedGraphData;
      existingGraph.timestamp = new Date();
      await existingGraph.save();
      
      return NextResponse.json({
        success: true,
        causalGraph: existingGraph,
        updated: true
      });
    } else {
      // Create new graph
      const newCausalGraph = new CausalGraph({
        sessionId,
        prolificId,
        qaPairId,
        graphData: processedGraphData
      });
      
      await newCausalGraph.save();
      
      return NextResponse.json({
        success: true,
        causalGraph: newCausalGraph,
        created: true
      });
    }
  } catch (error) {
    console.error("Error saving causal graph:", error);
    return NextResponse.json({ error: "Failed to save causal graph" }, { status: 500 });
  }
} 