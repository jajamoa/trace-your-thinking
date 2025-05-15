import { NextResponse } from "next/server";
import connectToDatabase from "../../../lib/mongodb";
import Session from "../../../models/Session";
import CausalGraph from "../../../models/CausalGraph";
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

    // Try to get the latest causal graph from the database
    let existingCausalGraph = null;
    let databaseGraphTimestamp = 0;
    let requestGraphTimestamp = body.existingCausalGraph?.timestamp || 0;
    
    try {
      const latestGraph = await CausalGraph.findOne({ 
        sessionId, 
        prolificId 
      }).sort({ timestamp: -1 });  // Get the most recent graph
      
      if (latestGraph && latestGraph.graphData) {
        console.log(`Found existing causal graph for session ${sessionId}`);
        existingCausalGraph = latestGraph.graphData;
        databaseGraphTimestamp = existingCausalGraph.timestamp || 0;
        
        console.log(`Database graph timestamp: ${databaseGraphTimestamp}, Request graph timestamp: ${requestGraphTimestamp}`);
        
        // If the request has a newer graph, use that instead
        if (requestGraphTimestamp > databaseGraphTimestamp && body.existingCausalGraph) {
          console.log(`Request has a newer graph (${requestGraphTimestamp} > ${databaseGraphTimestamp}), using that instead`);
          existingCausalGraph = body.existingCausalGraph;
        } else if (databaseGraphTimestamp > requestGraphTimestamp) {
          console.log(`Database has a newer graph (${databaseGraphTimestamp} > ${requestGraphTimestamp}), using that instead`);
        }
      } else if (body.existingCausalGraph) {
        console.log(`No graph in database, using graph from request with timestamp: ${requestGraphTimestamp}`);
        existingCausalGraph = body.existingCausalGraph;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.warn(`Could not fetch existing causal graph: ${errorMessage}`);
      // If we couldn't fetch from database but have a graph in the request, use that
      if (body.existingCausalGraph) {
        console.log(`Using graph from request with timestamp: ${requestGraphTimestamp}`);
        existingCausalGraph = body.existingCausalGraph;
      }
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
        topic: body.topic || session.topic, // Include topic from request or session
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

    // Log received causal graph data
    if (data.causalGraph) {
      console.log("======= RECEIVED CAUSAL GRAPH FROM PYTHON BACKEND =======");
      console.log(`QA pair ID: ${qaPair.id}, Session ID: ${sessionId}`);
      console.log(`timestamp: ${data.causalGraph.timestamp !== undefined ? data.causalGraph.timestamp : 'MISSING'}`);
      console.log(`nodes: ${Object.keys(data.causalGraph.nodes || {}).length} (${data.causalGraph.nodes ? 'present' : 'MISSING'})`);
      console.log(`edges: ${Object.keys(data.causalGraph.edges || {}).length} (${data.causalGraph.edges ? 'present' : 'MISSING'})`);
      console.log(`qa_history: ${Object.keys(data.causalGraph.qa_history || {}).length} (${data.causalGraph.qa_history ? 'present' : 'MISSING'})`);
      console.log(`stance_node_id: ${data.causalGraph.stance_node_id || 'MISSING'}`);
      console.log(`step: ${data.causalGraph.step || 'MISSING'}`);
      console.log(`anchor_queue: ${JSON.stringify(data.causalGraph.anchor_queue || [])} (${data.causalGraph.anchor_queue ? 'present' : 'MISSING'})`);
      console.log(`node_counter: ${data.causalGraph.node_counter !== undefined ? data.causalGraph.node_counter : 'MISSING'}`);
      console.log(`edge_counter: ${data.causalGraph.edge_counter !== undefined ? data.causalGraph.edge_counter : 'MISSING'}`);
      console.log(`qa_counter: ${data.causalGraph.qa_counter !== undefined ? data.causalGraph.qa_counter : 'MISSING'}`);
      console.log("==================================================");
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
        
        // Ensure the graph has a timestamp
        if (!data.causalGraph.timestamp) {
          data.causalGraph.timestamp = Date.now();
          console.log(`Added timestamp to causal graph: ${data.causalGraph.timestamp}`);
        } else {
          console.log(`Using existing timestamp in causal graph: ${data.causalGraph.timestamp}`);
        }
        
        // Ensure basic object structures exist even if empty
        if (!data.causalGraph.nodes) data.causalGraph.nodes = {};
        if (!data.causalGraph.edges) data.causalGraph.edges = {};
        if (!data.causalGraph.qa_history) data.causalGraph.qa_history = {};
        
        // Log after ensuring basic structure
        console.log("======= PREPARED CAUSAL GRAPH BEFORE DATABASE SAVE =======");
        console.log(`QA pair ID: ${qaPair.id}, Session ID: ${sessionId}`);
        console.log(`timestamp: ${data.causalGraph.timestamp !== undefined ? data.causalGraph.timestamp : 'MISSING'}`);
        console.log(`nodes: ${Object.keys(data.causalGraph.nodes).length} (present)`);
        console.log(`edges: ${Object.keys(data.causalGraph.edges).length} (present)`);
        console.log(`qa_history: ${Object.keys(data.causalGraph.qa_history).length} (present)`);
        console.log(`stance_node_id: ${data.causalGraph.stance_node_id || 'MISSING'}`);
        console.log(`step: ${data.causalGraph.step || 'MISSING'}`);
        console.log(`anchor_queue: ${JSON.stringify(data.causalGraph.anchor_queue || [])} (${data.causalGraph.anchor_queue ? 'present' : 'MISSING'})`);
        console.log(`node_counter: ${data.causalGraph.node_counter !== undefined ? data.causalGraph.node_counter : 'MISSING'}`);
        console.log(`edge_counter: ${data.causalGraph.edge_counter !== undefined ? data.causalGraph.edge_counter : 'MISSING'}`);
        console.log(`qa_counter: ${data.causalGraph.qa_counter !== undefined ? data.causalGraph.qa_counter : 'MISSING'}`);
        console.log("==================================================");
        
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
          
          // Log after saving to database
          console.log("======= SAVED CAUSAL GRAPH TO DATABASE (UPDATE) =======");
          console.log(`MongoDB document ID: ${existingGraph._id}`);
          console.log(`Updated timestamp: ${existingGraph.timestamp}`);
          console.log("==================================================");
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
          
          // Log after saving to database
          console.log("======= SAVED CAUSAL GRAPH TO DATABASE (NEW) =======");
          console.log(`MongoDB document ID: ${savedGraph._id}`);
          console.log(`Created timestamp: ${savedGraph.timestamp}`);
          console.log("==================================================");
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