import { NextResponse } from "next/server";
import connectToDatabase from "../../../lib/mongodb";
import CausalGraph from "../../../models/CausalGraph";

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
    
    return NextResponse.json({
      success: true,
      causalGraphs
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
    
    // Validate required fields
    if (!sessionId || !prolificId || !qaPairId || !graphData) {
      return NextResponse.json(
        { error: "Missing required fields: sessionId, prolificId, qaPairId, and graphData are required" }, 
        { status: 400 }
      );
    }
    
    // Check if a graph already exists for this QA pair
    const existingGraph = await CausalGraph.findOne({
      sessionId,
      prolificId,
      qaPairId
    });
    
    if (existingGraph) {
      // Update existing graph
      existingGraph.graphData = graphData;
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
        graphData
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