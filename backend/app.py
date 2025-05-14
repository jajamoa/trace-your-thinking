from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import hashlib
import time
import os
import uuid
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv
import traceback  # Add traceback for better error reporting

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from parent directory .env file or .env.local file
parent_env_path = Path(__file__).parent.parent / '.env'
parent_env_local_path = Path(__file__).parent.parent / '.env.local'

if parent_env_local_path.exists():
    load_dotenv(dotenv_path=parent_env_local_path)
    logger.info(f"Loaded environment variables from {parent_env_local_path}")
elif parent_env_path.exists():
    load_dotenv(dotenv_path=parent_env_path)
    logger.info(f"Loaded environment variables from {parent_env_path}")

# Import the necessary modules
from llm_extractor import QwenLLMExtractor
from cbn_manager import CBNManager
from question_generator import QuestionGenerator
from llm_logger import llm_logger, LLM_CALL_TYPES

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Initialize the components
extractor = QwenLLMExtractor(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="qwen-turbo",
    temperature=0.01  # Set temperature to lowest possible value for maximum consistency
)
cbn_manager = CBNManager()
question_generator = QuestionGenerator()

# Dictionary to store CBNs for each session/user
cbn_store = {}

# Log the configured LLM logging settings
llm_logger.log_settings()

# Enable more detailed logging for development
DEBUG_LLM_IO = os.getenv('DEBUG_LLM_IO', 'false').lower() == 'true'

# Add a function to get the default topic from the server or configuration
def get_default_topic():
    """
    Get the default topic from server settings or fallback to default.
    
    Returns:
        str: The default topic for stance nodes
    """
    default_topic = "climate change"  # Default fallback topic
    
    try:
        # Try to fetch from an API endpoint or configuration
        api_url = os.getenv('API_BASE_URL', 'http://localhost:3000')
        settings_url = f"{api_url}/api/admin/settings"
        
        try:
            response = requests.get(settings_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("settings") and data["settings"].get("defaultTopic"):
                    topic = data["settings"]["defaultTopic"]
                    # Sanitize topic
                    if topic and isinstance(topic, str) and topic.lower() != "none" and topic.strip() != "":
                        default_topic = topic
                        logger.info(f"Using topic from server settings: {default_topic}")
                        return default_topic
        except Exception as e:
            logger.warning(f"Could not fetch topic from server: {str(e)}")
        
        # Try to get from environment variable
        env_topic = os.getenv('DEFAULT_TOPIC')
        if env_topic and env_topic.strip() and env_topic.lower() != "none":
            default_topic = env_topic
            logger.info(f"Using topic from environment variable: {default_topic}")
            return default_topic
            
        logger.info(f"Using default fallback topic: {default_topic}")
        return default_topic
    
    except Exception as e:
        logger.error(f"Error getting default topic: {str(e)}")
        return default_topic

# Helper function to safely convert objects to string for logging
def safe_dump_for_log(obj, max_len=1000):
    """
    Safely convert an object to string for logging, with length limit.
    
    Args:
        obj: Any Python object to log
        max_len: Maximum string length to log
        
    Returns:
        str: String representation of the object
    """
    try:
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            result = str(obj)
        elif isinstance(obj, (list, tuple)):
            result = f"[List with {len(obj)} items] " + str(obj)
        elif isinstance(obj, dict):
            result = f"[Dict with {len(obj)} keys] " + str(obj)
        else:
            result = f"[Object of type {type(obj).__name__}] " + str(obj)
            
        if len(result) > max_len:
            return result[:max_len] + "... [truncated]"
        return result
    except Exception as e:
        return f"[Error dumping object: {str(e)}]"

# Helper function to log full objects when debug is enabled
def debug_dump(prefix, obj):
    """
    Dump an object to log if debug is enabled.
    
    Args:
        prefix: Label for the dump
        obj: The object to dump
    """
    if DEBUG_LLM_IO:
        try:
            logger.debug(f"{prefix}: {safe_dump_for_log(obj, max_len=5000)}")
        except Exception as e:
            logger.debug(f"Error dumping {prefix}: {str(e)}")

# Add global error handler to log all exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    """Log any uncaught exceptions and return appropriate error response"""
    # Log the stack trace
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    
    # Return JSON response
    return jsonify({
        "error": "Internal server error",
        "message": str(e),
        "success": False
    }), 500

# Health check endpoint
@app.route('/healthz', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring service status
    """
    return jsonify({
        "status": "healthy",
        "timestamp": int(time.time())
    })

# API status endpoint for admin dashboard
@app.route('/api/status', methods=['GET'])
def api_status():
    """
    API status endpoint that provides detailed status information for the admin dashboard
    """
    return jsonify({
        "status": "Running",
        "version": "1.0.0",
        "uptime": int(time.time()),
        "environment": os.environ.get("FLASK_ENV", "development"),
        "timestamp": int(time.time())
    })

# Main API endpoint - CBN implementation
@app.route('/api/process_answer', methods=['POST'])
def process_answer():
    """
    Process answer API - Implementing CBN construction from QA pairs
    """
    try:
        data = request.json
        if not data:
            logger.warning("No data received")
            return jsonify({"error": "No data received"}), 400
        
        # Dump incoming request data for debugging
        debug_dump("Incoming request data", data)
        
        # Extract required parameters
        session_id = data.get('sessionId')
        prolific_id = data.get('prolificId')
        qa_pair = data.get('qaPair')  # Current QA pair being processed
        qa_pairs = data.get('qaPairs', [])  # All QA pairs in the session
        current_index = data.get('currentQuestionIndex', 0)  # Current question index
        existing_causal_graph = data.get('existingCausalGraph')
        
        if not all([session_id, prolific_id, qa_pair]):
            logger.warning("Missing required parameters")
            missing_params = []
            if not session_id: missing_params.append("sessionId")
            if not prolific_id: missing_params.append("prolificId")
            if not qa_pair: missing_params.append("qaPair")
            return jsonify({"error": f"Missing required parameters: {', '.join(missing_params)}"}), 400
        
        # Log the question and answer summary
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        
        logger.info(f"Session: {session_id}, User: {prolific_id}")
        logger.info(f"Processing answer for question {current_index + 1}/{len(qa_pairs)}: {question[:50]}...")
        logger.info(f"Answer summary: {answer[:50]}...")
        llm_logger.log_separator(f"REQUEST START - Session {session_id}_{current_index}")
        
        # Get texts from all existing questions to avoid duplicating follow-up questions
        current_question_texts = []
        
        # Add the current question
        if qa_pair.get('question'):
            current_question_texts.append(qa_pair.get('question'))
        
        # Add all questions from the session's qaPairs
        for pair in qa_pairs:
            if pair.get('question') and pair.get('question') not in current_question_texts:
                current_question_texts.append(pair.get('question'))
        
        # Get or create the CBN for this user/session
        cbn_key = f"{session_id}_{prolific_id}"
        
        # Flag to track which source was used for the CBN
        cbn_source = "new"
        
        # Initialize variables to track timestamps
        memory_timestamp = 0
        request_timestamp = 0
        
        # Check if the CBN exists in memory
        if cbn_key in cbn_store:
            memory_timestamp = cbn_store[cbn_key].get("timestamp", 0)
            logger.info(f"Found CBN in memory store with timestamp: {memory_timestamp}")
        
        # Check if a CBN was provided in the request
        if existing_causal_graph and isinstance(existing_causal_graph, dict):
            request_timestamp = existing_causal_graph.get("timestamp", 0)
            logger.info(f"Found CBN in request with timestamp: {request_timestamp}")
        
        # Choose the most recent CBN based on timestamp
        if memory_timestamp > 0 and request_timestamp > 0:
            # Both sources have a CBN, compare timestamps
            if memory_timestamp >= request_timestamp:
                agent_cbn = cbn_store[cbn_key]
                cbn_source = "memory"
                logger.info(f"Using CBN from memory (more recent): memory={memory_timestamp}, request={request_timestamp}")
            else:
                agent_cbn = existing_causal_graph
                cbn_source = "request"
                logger.info(f"Using CBN from request (more recent): memory={memory_timestamp}, request={request_timestamp}")
        elif memory_timestamp > 0:
            # Only memory has a CBN
            agent_cbn = cbn_store[cbn_key]
            cbn_source = "memory"
            logger.info(f"Using CBN from memory (no valid request CBN)")
        elif existing_causal_graph and isinstance(existing_causal_graph, dict):
            # Only request has a CBN
            agent_cbn = existing_causal_graph
            cbn_source = "request"
            logger.info(f"Using CBN from request (no memory CBN)")
        else:
            # No existing CBN, create a new one
            cbn_source = "new"
            logger.info(f"No existing causal graph found, creating new CBN")
            
            # Get the default topic for stance node
            default_topic = get_default_topic()
            
            # Create a stance node with simple ID
            stance_node_id = "n1"  # First node is always n1 (stance node)
            stance_label = f"Support for {default_topic}"
            
            # Create new CBN with stance node
            agent_cbn = {
                "agent_id": prolific_id,
                "timestamp": int(time.time() * 1000),  # Use millisecond timestamp for better precision
                "nodes": {
                    stance_node_id: {
                        "label": stance_label,
                        "confidence": 1.0,
                        "evidence": [{"qa_id": "system", "confidence": 1.0, "importance": 1.0}],
                        "aggregate_confidence": 1.0,
                        "importance": 1.0,
                        "source_qa": [],
                        "incoming_edges": [],
                        "outgoing_edges": [],
                        "status": "anchor",  # Mark as anchor node
                        "is_stance": True    # Mark as stance node
                    }
                },
                "edges": {},
                "qa_history": {},
                "stance_node_id": stance_node_id,  # Track stance node
                "step": "node_discovery",     # Start with node discovery step
                "anchor_queue": [stance_node_id],  # Add stance node to anchor queue
                "node_counter": 1,           # Node counter starts at 1
                "edge_counter": 0,           # Track edge ID counter (start from 1)
                "qa_counter": 0              # Track QA ID counter (start from 1)
            }
            
            logger.info(f"Created new CBN for user {prolific_id} with stance node: {stance_label}")
        
        # Ensure required fields exist
        if "nodes" not in agent_cbn:
            agent_cbn["nodes"] = {}
        if "edges" not in agent_cbn:
            agent_cbn["edges"] = {}
        if "qa_history" not in agent_cbn:
            agent_cbn['qa_history'] = {}
        if "anchor_queue" not in agent_cbn:
            agent_cbn["anchor_queue"] = []
        
        # Get previous questions from qa_history
        for qa_id, qa_entry in agent_cbn.get('qa_history', {}).items():
            if 'question' in qa_entry and qa_entry['question'] not in current_question_texts:
                current_question_texts.append(qa_entry['question'])
        
        logger.info(f"Using CBN from {cbn_source} with {len(agent_cbn.get('nodes', {}))} nodes and {len(agent_cbn.get('edges', {}))} edges")
        
        llm_logger.log_separator("CBN PREPARATION COMPLETE")
        
        # Process the current QA pair to update the CBN
        updated_cbn = update_cbn_with_qa(agent_cbn, qa_pair)
        
        # Update timestamp before storing
        updated_cbn["timestamp"] = int(time.time() * 1000)
        
        # Store the updated CBN
        cbn_store[cbn_key] = updated_cbn
        
        # Log the updated timestamp
        logger.info(f"Updated CBN timestamp: {updated_cbn['timestamp']}")
        
        # Determine step and generate follow-up questions
        current_step = cbn_manager.get_next_step(updated_cbn)
        logger.info(f"Current CBN step: {current_step}")
        llm_logger.log_separator(f"FOLLOW-UP QUESTION GENERATION - Step {current_step}")
        
        # Generate follow-up questions based on CBN state
        follow_up_questions = question_generator.generate_follow_up_questions(
            updated_cbn, 
            current_step, 
            cbn_manager.anchor_queue, 
            current_question_texts
        )
        
        # Log the raw follow_up_questions for debugging
        logger.info(f"Raw follow_up_questions type: {type(follow_up_questions)}")
        if isinstance(follow_up_questions, list):
            logger.info(f"Follow-up questions list length: {len(follow_up_questions)}")
            # Log first few items to see their structure
            for i, q in enumerate(follow_up_questions[:2]):
                logger.info(f"Question {i} type: {type(q)}, content: {q}")
        elif isinstance(follow_up_questions, str):
            logger.error(f"follow_up_questions is a string, not a list: '{follow_up_questions}'")
            # Convert to a proper list to prevent errors
            follow_up_questions = []
        else:
            logger.error(f"Unexpected follow_up_questions type: {type(follow_up_questions)}")
            # Handle invalid type by defaulting to empty list
            follow_up_questions = []
        
        # Check total QA count and anchor nodes before deciding on follow-ups
        total_qa_count = len(qa_pairs)
        anchor_count = len(updated_cbn.get('anchor_queue', []))
        
        logger.info(f"Current QA count: {total_qa_count}, Anchor nodes: {anchor_count}")
        
        llm_logger.log_separator("QUESTION VALIDATION AND FILTERING")
        
        # Modified logic to ensure minimum QA pairs and anchor nodes
        if total_qa_count < 30:
            # If we haven't reached 30 QAs yet, ensure we have follow-ups
            if not follow_up_questions:
                # If no follow-ups were generated but we need more QAs, force create some
                logger.info("Forcing follow-up question generation to reach minimum QA count")
                try:
                    follow_up_questions = question_generator.generate_additional_questions(
                        updated_cbn, 
                        current_step, 
                        current_question_texts,
                        force_generate=True  # Force generation flag
                    )
                    
                    # Verify the response is a valid list
                    if not isinstance(follow_up_questions, list):
                        logger.error(f"generate_additional_questions returned non-list: {type(follow_up_questions)}")
                        follow_up_questions = []
                    
                    logger.info(f"Generated {len(follow_up_questions)} forced follow-up questions")
                except Exception as e:
                    logger.error(f"Error generating additional questions: {str(e)}")
                    follow_up_questions = []  # Default to empty list on error
                
            logger.info(f"Generated {len(follow_up_questions)} follow-up questions (QA count: {total_qa_count}/30)")
        elif anchor_count < 3:
            # If we have enough QAs but not enough anchor nodes, focus on node discovery
            logger.info(f"Not enough anchor nodes ({anchor_count}/3). Continuing with node discovery.")
            if not follow_up_questions:
                # Generate node discovery focused questions
                try:
                    follow_up_questions = question_generator.generate_additional_questions(
                        updated_cbn, 
                        "node_discovery",  # Force node discovery step
                        current_question_texts,
                        focus_on_nodes=True  # Focus on discovering more nodes
                    )
                    
                    # Verify the response is a valid list
                    if not isinstance(follow_up_questions, list):
                        logger.error(f"generate_additional_questions returned non-list: {type(follow_up_questions)}")
                        follow_up_questions = []
                    
                    logger.info(f"Generated {len(follow_up_questions)} node-focused questions")
                except Exception as e:
                    logger.error(f"Error generating node-focused questions: {str(e)}")
                    follow_up_questions = []  # Default to empty list on error
            
            logger.info(f"Generated {len(follow_up_questions)} node-focused questions")
        else:
            # We have enough QAs and anchor nodes, proceed normally
            # Limit follow-ups only if near the end AND we have enough anchors and QAs
            remaining_questions = len(qa_pairs) - current_index - 1
            if remaining_questions <= 3 and total_qa_count >= 30 and anchor_count >= 3:
                follow_up_questions = []  # No more follow-ups near the end when requirements are met
                logger.info("Near end of interview with sufficient QAs and anchors, no follow-up questions generated")
            elif remaining_questions <= 5:
                follow_up_questions = follow_up_questions[:1]  # Just one follow-up for near-end questions
                logger.info(f"Near end of interview, limited to 1 follow-up question")
            else:
                logger.info(f"Generated {len(follow_up_questions)} follow-up questions")
        
        # Filter out empty or meaningless questions before returning
        try:
            meaningful_questions = []
            logger.info(f"Starting to filter questions, total count: {len(follow_up_questions)}")
            
            for i, q in enumerate(follow_up_questions):
                try:
                    # Check if q is a dictionary (expected structure)
                    if isinstance(q, dict):
                        question_text = q.get('question', '').strip()
                        node_id = q.get('node_id')
                        node_label = None
                        
                        # If we have a node_id, try to get the node label from the CBN
                        if node_id and node_id in updated_cbn.get('nodes', {}):
                            node_label = updated_cbn['nodes'][node_id].get('label')
                        
                        # Check if both question content and reference node information are valid
                        has_valid_content = (len(question_text) > 15 and 
                                            not question_text.startswith("placeholder") and
                                            not question_text.startswith("TODO"))
                        
                        has_node_reference = node_id is not None or node_label is not None
                        
                        # If node info is missing but question is valid, try to add node reference
                        if has_valid_content and not has_node_reference:
                            # Extract main topic or specific issue from question if not already present
                            if not question_text.lower().find("about") >= 0:
                                # Set a default topic based on current step
                                if current_step == 1:
                                    q['shortText'] = f"About a new factor"
                                elif current_step == 2:
                                    q['shortText'] = f"About connections and relationships"
                                else:
                                    q['shortText'] = f"Additional question"
                        
                        # Only include questions that have both valid content and specific topic references
                        if has_valid_content:
                            if node_label:
                                # Ensure shortText includes the node reference if available
                                if not q.get('shortText'):
                                    q['shortText'] = f"About {node_label}"
                                # If the question doesn't explicitly reference the node, add it
                                if node_label.lower() not in question_text.lower():
                                    q['question'] = f"Regarding {node_label}: {question_text}"
                            
                            meaningful_questions.append(q)
                            logger.info(f"Keeping valid question {i}: {question_text[:50]}... [Node: {node_label or 'None'}]")
                        else:
                            logger.warning(f"Filtered out invalid question {i}: {question_text} - Missing node reference: {not has_node_reference}")
                    elif isinstance(q, str):
                        # Handle unexpected string type
                        logger.warning(f"Question {i} is a string, not a dict: '{q[:50]}...'")
                    else:
                        # Handle unexpected object types
                        logger.warning(f"Question {i} has unexpected type: {type(q)}")
                except Exception as question_error:
                    # Log detailed error for this specific question
                    logger.error(f"Error processing question {i}: {str(question_error)}")
                    logger.error(f"Problematic question object: {q}")
            
            logger.info(f"After filtering: {len(meaningful_questions)} meaningful questions from {len(follow_up_questions)} total")
        except Exception as e:
            # Handle any unexpected errors in the filtering process
            logger.error(f"Critical error during question filtering: {str(e)}")
            # Prevent the API from failing completely by returning an empty list
            meaningful_questions = []
            logger.info("Defaulting to empty questions list due to error")
        
        # Only return meaningful questions
        follow_up_questions = meaningful_questions
        
        # Return follow-up questions and causal graph
        llm_logger.log_separator(f"REQUEST COMPLETED - Session {session_id}_{current_index}")
        return jsonify({
            "success": True,
            "sessionId": session_id,
            "prolificId": prolific_id,
            "qaPair": qa_pair,
            "followUpQuestions": follow_up_questions,
            "causalGraph": updated_cbn,
            "timestamp": int(time.time())
        })
        
    except Exception as e:
        # Handle any unexpected errors in the main process
        logger.error(f"Critical error in process_answer: {str(e)}")
        logger.error(traceback.format_exc())
        llm_logger.log_separator(f"REQUEST ERROR - Critical exception")
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "success": False
        }), 500

def update_cbn_with_qa(agent_cbn, qa_pair):
    """
    Update the Causal Belief Network with information from a QA pair.
    
    Implements a two-step approach:
    1. Node Discovery & Confirmation step
    2. Edge Construction & Relationship Qualification step (combines previous edge construction and function fitting)
    
    Args:
        agent_cbn (dict): The existing CBN
        qa_pair (dict): The QA pair to process
        
    Returns:
        dict: Updated CBN
    """
    logger.info("Updating CBN with QA pair")
    llm_logger.log_separator("CBN UPDATE START")
    
    # Initialize CBN structures if they don't exist
    if 'nodes' not in agent_cbn:
        agent_cbn['nodes'] = {}
    if 'edges' not in agent_cbn:
        agent_cbn['edges'] = {}
    if 'qa_history' not in agent_cbn:
        agent_cbn['qa_history'] = {}
    
    # Ensure timestamp field exists
    if 'timestamp' not in agent_cbn:
        agent_cbn['timestamp'] = int(time.time() * 1000)
    
    # Determine current step based on CBN state
    if 'step' not in agent_cbn:
        agent_cbn['step'] = "node_discovery"  # Default to node discovery
    
    current_step = agent_cbn['step']
    logger.info(f"Current CBN step: {current_step}")
    
    # Generate a new QA ID - sequential from qa1
    qa_counter = agent_cbn.get('qa_counter', 0) + 1
    agent_cbn['qa_counter'] = qa_counter
    qa_id = f"qa{qa_counter}"
    logger.info(f"Assigned QA ID: {qa_id}")
    
    # If this is the first QA, ensure we create a stance node
    first_qa = len(agent_cbn.get('qa_history', {})) == 0
    
    # Track anchor queue if not already present
    if 'anchor_queue' not in agent_cbn:
        agent_cbn['anchor_queue'] = []  # Store confirmed anchor nodes
    
    # 1. Extract nodes from the QA pair using LLM
    llm_logger.log_separator("STEP 1: NODE EXTRACTION")
    new_nodes = extractor.extract_nodes(qa_pair, ensure_stance_node=False)  # Never create new stance nodes during QA processing
    
    # Process new nodes
    if new_nodes:
        logger.info(f"Extracted {len(new_nodes)} nodes")
        
        # Add new nodes to CBN with "candidate" status
        for node_id, node in new_nodes.items():
            node_label = node.get('label', '')
            
            # Check if similar node already exists
            existing_node_id = None
            for existing_id, existing_node in agent_cbn['nodes'].items():
                if existing_node.get('label', '').lower() == node_label.lower():
                    existing_node_id = existing_id
                    break
            
            # If node exists, update its frequency and other properties
            if existing_node_id:
                existing_node = agent_cbn['nodes'][existing_node_id]
                existing_node['frequency'] = existing_node.get('frequency', 1) + 1
                
                # Update importance and confidence if new values are higher
                if node.get('importance', 0) > existing_node.get('importance', 0):
                    existing_node['importance'] = node.get('importance')
                if node.get('confidence', 0) > existing_node.get('confidence', 0):
                    existing_node['confidence'] = node.get('confidence')
                    existing_node['aggregate_confidence'] = node.get('confidence')  # 同时更新aggregate_confidence
                
                # Add QA to sources if not already present
                if qa_id not in existing_node.get('source_qa', []):
                    existing_node['source_qa'].append(qa_id)
            else:
                # Create new node in CBN with candidate status and sequential ID
                if 'node_counter' not in agent_cbn:
                    agent_cbn['node_counter'] = 1  # Start at 1
                
                agent_cbn['node_counter'] += 1
                new_node_id = f"n{agent_cbn['node_counter']}"
                
                agent_cbn['nodes'][new_node_id] = {
                    "label": node_label,
                    "confidence": node.get('confidence', 0.5),
                    "aggregate_confidence": node.get('confidence', 0.5),
                    "importance": node.get('importance', 0.5),
                    "source_qa": [qa_id],
                    "incoming_edges": [],
                    "outgoing_edges": [],
                    "status": "candidate",  # All new nodes (except initial stance node) start as candidates
                    "frequency": 1,         # Track frequency directly in the node
                    "is_stance": False      # Regular node, not a stance node
                }
        
        # Remove logic that tries to set stance node from extracted nodes
        # Stance node should only be created during CBN initialization
    else:
        logger.warning("No nodes extracted from QA pair")
    
    # 2. Extract edge from the QA pair using LLM (including modifier information)
    # Note: Nodes are handled the same way in both steps 1 and 2 - all start as candidates
    # and are only promoted to anchors based on specific criteria
    llm_logger.log_separator("STEP 2: EDGE & MODIFIER EXTRACTION")
    edge = extractor.extract_edge(qa_pair)

    # 3. Add or update edge if found
    if edge:
        logger.info(f"Extracted edge: {edge.get('from_label', '')} → {edge.get('to_label', '')} " +
                    f"(direction: {edge.get('direction', '')}, strength: {edge.get('strength', 0.7)})")
        
        # Update function parameters directly from the edge extraction results
        if edge.get('strength'):
            # Create function params from edge strength
            function_params = {
                "confidence": edge.get('confidence', 0.7),
                "strength": edge.get('strength', 0.7)
            }
            logger.info(f"Using combined edge and modifier parameters: {function_params}")
        else:
            function_params = None
        
        # Add or update the edge with the combined information
        agent_cbn, edge_id = cbn_manager.add_or_update_edge(agent_cbn, edge)
        
        # No need for separate function parameter extraction
        # Update function parameters if edge found and parameters extracted
        if edge_id and function_params:
            logger.info(f"Updating function parameters for edge {edge_id}")
            agent_cbn = cbn_manager.update_function_params(agent_cbn, edge_id, function_params)

        llm_logger.log_separator("EDGE PROCESSING COMPLETE")
    
    # 4. Create parsed belief for QA using LLM
    # Find edge ID (if it exists) for creating parsed belief
    edge_id = None
    for eid, e in agent_cbn.get('edges', {}).items():
        from_node_id = e.get('source')
        to_node_id = e.get('target')
        
        if from_node_id and to_node_id:
            from_node = agent_cbn['nodes'].get(from_node_id, {})
            to_node = agent_cbn['nodes'].get(to_node_id, {})
            
            if (from_node.get('label', '').lower() == edge['from_label'].lower() and 
                to_node.get('label', '').lower() == edge['to_label'].lower()):
                edge_id = eid
                break
    
    # 5. Extract beliefs and add QA to graph
    llm_logger.log_separator("BELIEF EXTRACTION & QA RECORDING")
    
    if edge_id:
        from_node_id = agent_cbn['edges'][edge_id]['source']
        to_node_id = agent_cbn['edges'][edge_id]['target']
        
        parsed_belief = extractor.extract_parsed_belief(qa_pair, from_node_id, to_node_id)
        
        # Add QA with parsed belief to the graph
        if parsed_belief:
            logger.info(f"Adding QA with parsed belief to graph")
            qa_pair['id'] = qa_id  # Assign the generated qa_id to the qa_pair
            agent_cbn = cbn_manager.add_qa_to_graph(agent_cbn, qa_pair, parsed_belief, new_nodes)
        else:
            # Add QA with empty parsed belief
            logger.info(f"Adding QA with empty parsed belief to graph")
            qa_pair['id'] = qa_id  # Assign the generated qa_id to the qa_pair
            agent_cbn = cbn_manager.add_qa_to_graph(agent_cbn, qa_pair, None, new_nodes)
    else:
        # Add QA with empty parsed belief
        logger.info(f"Adding QA with empty parsed belief (no valid edge ID)")
        qa_pair['id'] = qa_id  # Assign the generated qa_id to the qa_pair
        agent_cbn = cbn_manager.add_qa_to_graph(agent_cbn, qa_pair, None, new_nodes)
    
    # 6. Check for nodes that should be promoted based on frequency
    cbn_manager._check_node_promotion(agent_cbn)
    logger.info(f"Checked node promotion using CBNManager, current anchor queue: {agent_cbn.get('anchor_queue', [])}")
    
    # Output detailed information about nodes by status
    logger.info("Candidate nodes:")
    for node_id, node in agent_cbn['nodes'].items():
        if node.get('status') == "candidate":
            logger.info(f"  - {node.get('label', 'unknown')}: freq={node.get('frequency', 1)}, importance={node.get('importance', 0)}")
    
    logger.info("Anchor nodes:")
    for node_id in agent_cbn['anchor_queue']:
        if node_id in agent_cbn['nodes']:
            node = agent_cbn['nodes'][node_id]
            logger.info(f"  - {node.get('label', 'unknown')}: confidence={node.get('confidence', 0)}, connections={len(node.get('incoming_edges', [])) + len(node.get('outgoing_edges', []))}")
    
    if current_step == "edge_construction":
        # For edge construction step, check for structure convergence
        if cbn_manager.check_termination(agent_cbn):
            logger.info("CBN termination criteria met")
    
    # Log current state
    logger.info(f"Updated CBN now has {len(agent_cbn['nodes'])} nodes and {len(agent_cbn.get('edges', {}))} edges")
    
    # Count candidate and anchor nodes
    candidate_count = sum(1 for node in agent_cbn['nodes'].values() if node.get('status') == 'candidate')
    logger.info(f"Node candidates: {candidate_count}, Anchor nodes: {len(agent_cbn['anchor_queue'])}")
    
    if agent_cbn.get('stance_node_id'):
        stance_node = agent_cbn['nodes'].get(agent_cbn['stance_node_id'], {})
        logger.info(f"Stance node: {stance_node.get('label', 'None')}")
    
    llm_logger.log_separator("CBN UPDATE COMPLETE")
    return agent_cbn

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    llm_logger.log_separator("SERVER STARTUP")
    logger.info(f"Starting server on port {port}")
    logger.info(f"LLM logging status: Check individual call type settings with llm_logger.log_settings()")
    app.run(host='0.0.0.0', port=port, debug=False) 