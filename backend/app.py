from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import hashlib
import time
import os
import uuid
import logging
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
from scm_manager import SCMManager
from question_generator import QuestionGenerator

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Initialize the components
extractor = QwenLLMExtractor(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="qwen-turbo",
    temperature=0.01  # Set temperature to lowest possible value for maximum consistency
)
scm_manager = SCMManager()
question_generator = QuestionGenerator()

# Dictionary to store SCMs for each session/user
scm_store = {}

# Enable more detailed logging for development
DEBUG_LLM_IO = os.getenv('DEBUG_LLM_IO', 'false').lower() == 'true'

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

# Main API endpoint - SCM implementation
@app.route('/api/process_answer', methods=['POST'])
def process_answer():
    """
    Process answer API - Implementing SCM construction from QA pairs
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
        
        # Get texts from all existing questions to avoid duplicating follow-up questions
        current_question_texts = []
        
        # Add the current question
        if qa_pair.get('question'):
            current_question_texts.append(qa_pair.get('question'))
        
        # Add all questions from the session's qaPairs
        for pair in qa_pairs:
            if pair.get('question') and pair.get('question') not in current_question_texts:
                current_question_texts.append(pair.get('question'))
        
        # Get or create the SCM for this user/session
        scm_key = f"{session_id}_{prolific_id}"
        
        if scm_key in scm_store:
            # Use existing SCM from global store
            agent_scm = scm_store[scm_key]
            logger.info(f"Using existing SCM from memory store with {len(agent_scm.get('nodes', {}))} nodes and {len(agent_scm.get('edges', {}))} edges")
        elif existing_causal_graph and isinstance(existing_causal_graph, dict):
            # Use provided causal graph from API request
            agent_scm = existing_causal_graph
            
            # Ensure agent_id is set
            if 'agent_id' not in agent_scm or not agent_scm['agent_id']:
                agent_scm['agent_id'] = prolific_id
                
            # Check for previous questions from causal graph
            if 'qas' in existing_causal_graph:
                for qa in existing_causal_graph.get('qas', []):
                    if 'question' in qa and qa['question'] not in current_question_texts:
                        current_question_texts.append(qa['question'])
            
            logger.info(f"Using causal graph from API request with {len(agent_scm.get('nodes', {}))} nodes and {len(agent_scm.get('edges', {}))} edges")
        else:
            # No SCM found in memory or API request, create new one
            logger.info(f"No existing causal graph found in memory or API request, creating new SCM")
            # Create new SCM
            agent_scm = {
                "agent_id": prolific_id,
                "nodes": {},
                "edges": {},
                "qas": [],
                "stance_node_id": None,  # Track stance node
                "phase": "node_discovery"  # Start with node discovery phase
            }
            logger.info(f"Created new SCM for user {prolific_id}")
        
        # Process the current QA pair to update the SCM
        updated_scm = update_scm_with_qa(agent_scm, qa_pair)
        
        # Store the updated SCM
        scm_store[scm_key] = updated_scm
        
        # Determine phase and generate follow-up questions
        current_phase = scm_manager.get_next_phase(updated_scm)
        logger.info(f"Current SCM phase: {current_phase}")
        
        # Generate follow-up questions based on SCM state
        follow_up_questions = question_generator.generate_follow_up_questions(
            updated_scm, 
            current_phase, 
            scm_manager.anchor_queue, 
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
        anchor_count = len(updated_scm.get('anchor_queue', []))
        
        logger.info(f"Current QA count: {total_qa_count}, Anchor nodes: {anchor_count}")
        
        # Modified logic to ensure minimum QA pairs and anchor nodes
        if total_qa_count < 30:
            # If we haven't reached 30 QAs yet, ensure we have follow-ups
            if not follow_up_questions:
                # If no follow-ups were generated but we need more QAs, force create some
                logger.info("Forcing follow-up question generation to reach minimum QA count")
                try:
                    follow_up_questions = question_generator.generate_additional_questions(
                        updated_scm, 
                        current_phase, 
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
                        updated_scm, 
                        "node_discovery",  # Force node discovery phase
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
                        
                        # If we have a node_id, try to get the node label from the SCM
                        if node_id and node_id in updated_scm.get('nodes', {}):
                            node_label = updated_scm['nodes'][node_id].get('label')
                        
                        # Check if both question content and reference node information are valid
                        has_valid_content = (len(question_text) > 15 and 
                                            not question_text.startswith("placeholder") and
                                            not question_text.startswith("TODO"))
                        
                        has_node_reference = node_id is not None or node_label is not None
                        
                        # If node info is missing but question is valid, try to add node reference
                        if has_valid_content and not has_node_reference:
                            # Extract main topic or specific issue from question if not already present
                            if not question_text.lower().find("about") >= 0:
                                # Set a default topic based on current phase
                                if current_phase == 1:
                                    q['shortText'] = f"About a new factor"
                                elif current_phase == 2:
                                    q['shortText'] = f"About connections between factors"
                                elif current_phase == 3:
                                    q['shortText'] = f"About factor relationships"
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
        return jsonify({
            "success": True,
            "sessionId": session_id,
            "prolificId": prolific_id,
            "qaPair": qa_pair,
            "followUpQuestions": follow_up_questions,
            "causalGraph": updated_scm,
            "timestamp": int(time.time())
        })
        
    except Exception as e:
        # Handle any unexpected errors in the main process
        logger.error(f"Critical error in process_answer: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "success": False
        }), 500

def update_scm_with_qa(agent_scm, qa_pair):
    """
    Update the Structural Causal Model with information from a QA pair.
    
    Implements a two-phase approach:
    1. Node Discovery & Confirmation phase
    2. Edge Construction & Function Fitting phase
    
    Args:
        agent_scm (dict): The existing SCM
        qa_pair (dict): The QA pair to process
        
    Returns:
        dict: Updated SCM
    """
    logger.info("Updating SCM with QA pair")
    
    # Determine current phase based on SCM state
    if 'phase' not in agent_scm:
        agent_scm['phase'] = "node_discovery"  # Default to node discovery
    
    current_phase = agent_scm['phase']
    logger.info(f"Current SCM phase: {current_phase}")
    
    # If this is the first QA, ensure we create a stance node
    first_qa = len(agent_scm.get('qas', [])) == 0
    
    # Track node queues if not already present
    if 'node_candidate_queue' not in agent_scm:
        agent_scm['node_candidate_queue'] = {}  # Store node candidates with frequency
    
    if 'anchor_queue' not in agent_scm:
        agent_scm['anchor_queue'] = []  # Store confirmed anchor nodes
    
    # 1. Extract nodes from the QA pair using Qwen LLM
    if DEBUG_LLM_IO:
        logger.info(f"LLM INPUT (extract_nodes): Question: {qa_pair.get('question', '')[:100]}...")
        logger.info(f"LLM INPUT (extract_nodes): Answer: {qa_pair.get('answer', '')[:100]}...")
    
    new_nodes = extractor.extract_nodes(qa_pair, ensure_stance_node=first_qa)
    
    # Log more details about LLM outputs
    if DEBUG_LLM_IO and new_nodes:
        logger.info(f"LLM OUTPUT (extract_nodes): {json.dumps(new_nodes, indent=2)[:500]}...")
    
    # Process new nodes according to phase
    if new_nodes:
        logger.info(f"Extracted {len(new_nodes)} nodes")
        
        # Update node candidate queue with frequency
        for node_id, node in new_nodes.items():
            node_label = node.get('label', '').lower()
            if node_label in agent_scm['node_candidate_queue']:
                agent_scm['node_candidate_queue'][node_label]['frequency'] += 1
            else:
                agent_scm['node_candidate_queue'][node_label] = {
                    'node_id': node_id,
                    'frequency': 1,
                    'semantic_role': node.get('semantic_role', 'unknown'),
                    'first_seen_in_qa': len(agent_scm.get('qas', [])),
                }
        
        # Promote candidate nodes to anchor status if they meet criteria
        for node_label, info in list(agent_scm['node_candidate_queue'].items()):
            if (info['frequency'] >= 2 and 
                node_label not in [n.lower() for n in agent_scm['anchor_queue']]):
                # Promote to anchor queue
                agent_scm['anchor_queue'].append(node_label)
                logger.info(f"Promoted node '{node_label}' to anchor status (frequency: {info['frequency']})")
        
        # If we have a stance node in the extracted nodes, set it in the SCM
        stance_nodes = [node_id for node_id, node in new_nodes.items() 
                      if node.get('is_stance') or node.get('semantic_role') == 'behavioral_intention']
        
        if stance_nodes and not agent_scm.get('stance_node_id'):
            agent_scm['stance_node_id'] = stance_nodes[0]
            logger.info(f"Set stance node: {new_nodes[stance_nodes[0]]['label']}")
    else:
        logger.warning("No nodes extracted from QA pair")
    
    # 2. Merge and tag nodes
    agent_scm = scm_manager.merge_and_tag_nodes(agent_scm, new_nodes)
    
    # Check for phase transition (Node Discovery -> Edge Construction)
    num_anchors = len(agent_scm['anchor_queue'])
    if current_phase == "node_discovery" and num_anchors >= 5:
        logger.info(f"Phase transition: Node Discovery -> Edge Construction (found {num_anchors} anchor nodes)")
        agent_scm['phase'] = "edge_construction"
        current_phase = "edge_construction"
    
    # 3. Extract edge from the QA pair using Qwen LLM
    if DEBUG_LLM_IO:
        logger.info(f"LLM INPUT (extract_edge): Question: {qa_pair.get('question', '')[:100]}...")
        logger.info(f"LLM INPUT (extract_edge): Answer: {qa_pair.get('answer', '')[:100]}...")
        
    edge = extractor.extract_edge(qa_pair)
    
    if DEBUG_LLM_IO and edge:
        logger.info(f"LLM OUTPUT (extract_edge): {json.dumps(edge, indent=2)}")
    
    # 4. Add or update edge if found
    if edge:
        logger.info(f"Extracted edge: {edge.get('from_label', '')} → {edge.get('to_label', '')}")
        agent_scm = scm_manager.add_or_update_edge(agent_scm, edge)
        
        # 5. If we have an edge, extract function parameters using Qwen LLM
        # This is primarily for the Edge Construction phase
        if current_phase == "edge_construction":
            if DEBUG_LLM_IO:
                logger.info(f"LLM INPUT (extract_function_params): Question: {qa_pair.get('question', '')[:100]}...")
                logger.info(f"LLM INPUT (extract_function_params): Answer: {qa_pair.get('answer', '')[:100]}...")
                
            function_params = extractor.extract_function_params(qa_pair)
            
            if DEBUG_LLM_IO and function_params:
                logger.info(f"LLM OUTPUT (extract_function_params): {json.dumps(function_params, indent=2)}")
            
            # Find the edge ID for the newly added/updated edge
            edge_id = None
            for eid, e in agent_scm.get('edges', {}).items():
                from_node_id = e.get('from')
                to_node_id = e.get('to')
                
                if from_node_id and to_node_id:
                    from_node = agent_scm['nodes'].get(from_node_id, {})
                    to_node = agent_scm['nodes'].get(to_node_id, {})
                    
                    if (from_node.get('label', '').lower() == edge['from_label'].lower() and 
                        to_node.get('label', '').lower() == edge['to_label'].lower()):
                        edge_id = eid
                        break
            
            # 6. Update function parameters if edge found and parameters extracted
            if edge_id and function_params:
                logger.info(f"Updating function parameters for edge {edge_id}")
                agent_scm = scm_manager.update_function_params(agent_scm, edge_id, function_params)
        
        # 7. Create parsed belief for QA using Qwen LLM
        # Find edge ID (if it exists) for creating parsed belief
        edge_id = None
        for eid, e in agent_scm.get('edges', {}).items():
            from_node_id = e.get('from')
            to_node_id = e.get('to')
            
            if from_node_id and to_node_id:
                from_node = agent_scm['nodes'].get(from_node_id, {})
                to_node = agent_scm['nodes'].get(to_node_id, {})
                
                if (from_node.get('label', '').lower() == edge['from_label'].lower() and 
                    to_node.get('label', '').lower() == edge['to_label'].lower()):
                    edge_id = eid
                    break
        
        if edge_id:
            from_node_id = agent_scm['edges'][edge_id]['from']
            to_node_id = agent_scm['edges'][edge_id]['to']
            
            if DEBUG_LLM_IO:
                logger.info(f"LLM INPUT (extract_parsed_belief): Question: {qa_pair.get('question', '')[:100]}...")
                logger.info(f"LLM INPUT (extract_parsed_belief): Answer: {qa_pair.get('answer', '')[:100]}...")
                logger.info(f"LLM INPUT (extract_parsed_belief): from_node_id: {from_node_id}, to_node_id: {to_node_id}")
                
            parsed_belief = extractor.extract_parsed_belief(qa_pair, from_node_id, to_node_id)
            
            if DEBUG_LLM_IO and parsed_belief:
                logger.info(f"LLM OUTPUT (extract_parsed_belief): {json.dumps(parsed_belief, indent=2)}")
            
            # 8. Add QA with parsed belief to the graph
            if parsed_belief:
                logger.info(f"Adding QA with parsed belief to graph")
                agent_scm = scm_manager.add_qa_to_graph(agent_scm, qa_pair, parsed_belief)
            else:
                # Add QA with empty parsed belief to comply with schema
                logger.info(f"Adding QA with empty parsed belief to graph")
                empty_parsed_belief = {}
                agent_scm = scm_manager.add_qa_to_graph(agent_scm, qa_pair, empty_parsed_belief)
        else:
            # Add QA with empty parsed belief
            logger.info(f"Adding QA with empty parsed belief (no valid edge ID)")
            empty_parsed_belief = {}
            agent_scm = scm_manager.add_qa_to_graph(agent_scm, qa_pair, empty_parsed_belief)
    else:
        logger.info("No edge extracted from QA pair")
        # Add QA with empty parsed belief
        logger.info(f"Adding QA with empty parsed belief (no edge)")
        empty_parsed_belief = {}
        agent_scm = scm_manager.add_qa_to_graph(agent_scm, qa_pair, empty_parsed_belief)
    
    # 9. Check if interview should be terminated based on phase-specific criteria
    if current_phase == "edge_construction":
        # For edge construction phase, check for structure convergence
        if scm_manager.check_termination(agent_scm):
            logger.info("SCM termination criteria met")
    
    # Log current state
    logger.info(f"Updated SCM now has {len(agent_scm['nodes'])} nodes and {len(agent_scm.get('edges', {}))} edges")
    logger.info(f"Node candidates: {len(agent_scm['node_candidate_queue'])}, Anchor nodes: {len(agent_scm['anchor_queue'])}")
    
    if agent_scm.get('stance_node_id'):
        stance_node = agent_scm['nodes'].get(agent_scm['stance_node_id'], {})
        logger.info(f"Stance node: {stance_node.get('label', 'None')}")
    
    return agent_scm

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"Starting server on port {port}")
    logger.info(f"LLM I/O debug mode is {'ENABLED' if DEBUG_LLM_IO else 'DISABLED'}. Set DEBUG_LLM_IO=true to enable detailed LLM logging.")
    app.run(host='0.0.0.0', port=port) 