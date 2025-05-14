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
  timestamp: number;
  
  // Additional fields from backend CBN
  stance_node_id?: string;
  step?: string;
  anchor_queue?: string[];
  node_counter?: number;
  edge_counter?: number;
  qa_counter?: number;
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

    // At least sessionId or prolificId must be provided
    if (!sessionId && !prolificId) {
      return NextResponse.json({ error: "Either sessionId or prolificId parameter is required" }, { status: 400 });
    }
    
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
    
    console.log(`Found ${causalGraphs.length} causal graphs matching query criteria`);
    
    // Return original graph data, ensuring empty objects are preserved
    const processedGraphs = causalGraphs.map(graph => {
      let graphData = graph.graphData;
      
      // Log each retrieved graph before processing
      console.log(`======= RETRIEVED CAUSAL GRAPH FROM DATABASE =======`);
      console.log(`MongoDB document ID: ${graph._id}`);
      console.log(`Session ID: ${graph.sessionId}, Prolific ID: ${graph.prolificId}, QA Pair ID: ${graph.qaPairId}`);
      console.log(`DB Timestamp: ${graph.timestamp}`);
      console.log(`timestamp: ${graphData.timestamp !== undefined ? graphData.timestamp : 'MISSING'}`);
      console.log(`nodes: ${Object.keys(graphData.nodes || {}).length} (${graphData.nodes ? 'present' : 'MISSING'})`);
      console.log(`edges: ${Object.keys(graphData.edges || {}).length} (${graphData.edges ? 'present' : 'MISSING'})`);
      console.log(`qa_history: ${Object.keys(graphData.qa_history || {}).length} (${graphData.qa_history ? 'present' : 'MISSING'})`);
      console.log(`stance_node_id: ${graphData.stance_node_id || 'MISSING'}`);
      console.log(`step: ${graphData.step || 'MISSING'}`);
      console.log(`anchor_queue: ${JSON.stringify(graphData.anchor_queue || [])} (${graphData.anchor_queue ? 'present' : 'MISSING'})`);
      console.log(`node_counter: ${graphData.node_counter !== undefined ? graphData.node_counter : 'MISSING'}`);
      console.log(`edge_counter: ${graphData.edge_counter !== undefined ? graphData.edge_counter : 'MISSING'}`);
      console.log(`qa_counter: ${graphData.qa_counter !== undefined ? graphData.qa_counter : 'MISSING'}`);
      console.log("==================================================");
      
      // Only ensure basic structures exist, no other modifications
      if (!graphData.nodes) graphData.nodes = {};
      if (!graphData.edges) graphData.edges = {};
      if (!graphData.qa_history) graphData.qa_history = {};
      if (!graphData.timestamp) graphData.timestamp = Date.now();
      
      // Log after ensuring basic structure
      console.log(`======= PROCESSED CAUSAL GRAPH BEFORE SENDING TO CLIENT =======`);
      console.log(`Session ID: ${graph.sessionId}, QA Pair ID: ${graph.qaPairId}`);
      console.log(`Final timestamp: ${graphData.timestamp}`);
      console.log("==================================================");
      
      // Return original object
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
    
    // Log incoming graph data
    console.log("======= RECEIVED CAUSAL GRAPH IN POST REQUEST =======");
    console.log(`Session ID: ${sessionId}, Prolific ID: ${prolificId}, QA Pair ID: ${qaPairId}`);
    if (graphData) {
      console.log(`timestamp: ${graphData.timestamp !== undefined ? graphData.timestamp : 'MISSING'}`);
      console.log(`nodes: ${Object.keys(graphData.nodes || {}).length} (${graphData.nodes ? 'present' : 'MISSING'})`);
      console.log(`edges: ${Object.keys(graphData.edges || {}).length} (${graphData.edges ? 'present' : 'MISSING'})`);
      console.log(`qa_history: ${Object.keys(graphData.qa_history || {}).length} (${graphData.qa_history ? 'present' : 'MISSING'})`);
      console.log(`stance_node_id: ${graphData.stance_node_id || 'MISSING'}`);
      console.log(`step: ${graphData.step || 'MISSING'}`);
      console.log(`anchor_queue: ${JSON.stringify(graphData.anchor_queue || [])} (${graphData.anchor_queue ? 'present' : 'MISSING'})`);
      console.log(`node_counter: ${graphData.node_counter !== undefined ? graphData.node_counter : 'MISSING'}`);
      console.log(`edge_counter: ${graphData.edge_counter !== undefined ? graphData.edge_counter : 'MISSING'}`);
      console.log(`qa_counter: ${graphData.qa_counter !== undefined ? graphData.qa_counter : 'MISSING'}`);
    } else {
      console.log("No graph data received");
    }
    console.log("==================================================");
    
    // Validate required fields
    if (!sessionId || !prolificId || !qaPairId || !graphData) {
      return NextResponse.json(
        { error: "Missing required fields: sessionId, prolificId, qaPairId, and graphData are required" }, 
        { status: 400 }
      );
    }
    
    // Ensure basic structures exist
    let processedGraphData = { ...graphData };
    if (!processedGraphData.nodes) processedGraphData.nodes = {};
    if (!processedGraphData.edges) processedGraphData.edges = {};
    if (!processedGraphData.qa_history) processedGraphData.qa_history = {};
    
    // Ensure timestamp exists
    if (!processedGraphData.timestamp) {
      processedGraphData.timestamp = Date.now();
    }
    
    // Log processed graph data before database save
    console.log("======= PROCESSED CAUSAL GRAPH BEFORE DATABASE SAVE (POST) =======");
    console.log(`Session ID: ${sessionId}, QA Pair ID: ${qaPairId}`);
    console.log(`Final timestamp: ${processedGraphData.timestamp}`);
    console.log(`Nodes count: ${Object.keys(processedGraphData.nodes).length}`);
    console.log(`Edges count: ${Object.keys(processedGraphData.edges).length}`);
    console.log(`QA history count: ${Object.keys(processedGraphData.qa_history).length}`);
    console.log(`Anchor queue: ${JSON.stringify(processedGraphData.anchor_queue || [])}`);
    console.log(`Step: ${processedGraphData.step || 'undefined'}`);
    console.log(`Node counter: ${processedGraphData.node_counter || 'undefined'}`);
    console.log(`Edge counter: ${processedGraphData.edge_counter || 'undefined'}`);
    console.log(`QA counter: ${processedGraphData.qa_counter || 'undefined'}`);
    console.log("==================================================");
    
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
      
      // Log after saving to database
      console.log("======= SAVED CAUSAL GRAPH TO DATABASE (POST/UPDATE) =======");
      console.log(`MongoDB document ID: ${existingGraph._id}`);
      console.log(`Updated timestamp: ${existingGraph.timestamp}`);
      console.log("==================================================");
      
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
      
      // Log after saving to database
      console.log("======= SAVED CAUSAL GRAPH TO DATABASE (POST/NEW) =======");
      console.log(`MongoDB document ID: ${newCausalGraph._id}`);
      console.log(`Created timestamp: ${newCausalGraph.timestamp}`);
      console.log("==================================================");
      
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