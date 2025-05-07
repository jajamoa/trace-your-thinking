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
    model="qwen-turbo"
)
scm_manager = SCMManager()
question_generator = QuestionGenerator()

# Dictionary to store SCMs for each session/user
scm_store = {}

# Enable more detailed logging for development
DEBUG_LLM_IO = os.getenv('DEBUG_LLM_IO', 'false').lower() == 'true'

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
    data = request.json
    if not data:
        logger.warning("No data received")
        return jsonify({"error": "No data received"}), 400
    
    # Extract required parameters
    session_id = data.get('sessionId')
    prolific_id = data.get('prolificId')
    qa_pair = data.get('qaPair')  # Current QA pair being processed
    qa_pairs = data.get('qaPairs', [])  # All QA pairs in the session
    current_index = data.get('currentQuestionIndex', 0)  # Current question index
    existing_causal_graph = data.get('existingCausalGraph')
    
    if not all([session_id, prolific_id, qa_pair]):
        logger.warning("Missing required parameters")
        return jsonify({"error": "Missing required parameters"}), 400
    
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
    
    # Check if we're near the end of the interview and should limit follow-ups
    remaining_questions = len(qa_pairs) - current_index - 1
    if remaining_questions <= 3:
        follow_up_questions = []  # No more follow-ups near the end
        logger.info("Near end of interview, no follow-up questions generated")
    elif remaining_questions <= 5:
        follow_up_questions = follow_up_questions[:1]  # Just one follow-up for near-end questions
        logger.info(f"Near end of interview, limited to 1 follow-up question")
    else:
        logger.info(f"Generated {len(follow_up_questions)} follow-up questions")
    
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

def update_scm_with_qa(agent_scm, qa_pair):
    """
    Update the Structural Causal Model with information from a QA pair.
    
    Args:
        agent_scm (dict): The existing SCM
        qa_pair (dict): The QA pair to process
        
    Returns:
        dict: Updated SCM
    """
    logger.info("Updating SCM with QA pair")
    
    # 1. Extract nodes from the QA pair using Qwen LLM
    # If this is the first QA, ensure we create a stance node
    first_qa = len(agent_scm.get('qas', [])) == 0
    
    # Log more details about inputs to LLM
    if DEBUG_LLM_IO:
        logger.info(f"LLM INPUT (extract_nodes): Question: {qa_pair.get('question', '')[:100]}...")
        logger.info(f"LLM INPUT (extract_nodes): Answer: {qa_pair.get('answer', '')[:100]}...")
    
    new_nodes = extractor.extract_nodes(qa_pair, ensure_stance_node=first_qa)
    
    # Log more details about LLM outputs
    if DEBUG_LLM_IO and new_nodes:
        logger.info(f"LLM OUTPUT (extract_nodes): {json.dumps(new_nodes, indent=2)[:500]}...")
    
    if new_nodes:
        logger.info(f"Extracted {len(new_nodes)} nodes")
        
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
            logger.info(f"Adding QA with empty parsed belief (no function params)")
            empty_parsed_belief = {}
            agent_scm = scm_manager.add_qa_to_graph(agent_scm, qa_pair, empty_parsed_belief)
    else:
        logger.info("No edge extracted from QA pair")
        # Add QA with empty parsed belief
        logger.info(f"Adding QA with empty parsed belief (no edge)")
        empty_parsed_belief = {}
        agent_scm = scm_manager.add_qa_to_graph(agent_scm, qa_pair, empty_parsed_belief)
    
    # 9. Check if interview should be terminated
    if scm_manager.check_termination(agent_scm):
        logger.info("SCM termination criteria met")
    
    # Log current state
    logger.info(f"Updated SCM now has {len(agent_scm['nodes'])} nodes and {len(agent_scm.get('edges', {}))} edges")
    if agent_scm.get('stance_node_id'):
        stance_node = agent_scm['nodes'].get(agent_scm['stance_node_id'], {})
        logger.info(f"Stance node: {stance_node.get('label', 'None')}")
    
    return agent_scm

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"Starting server on port {port}")
    logger.info(f"LLM I/O debug mode is {'ENABLED' if DEBUG_LLM_IO else 'DISABLED'}. Set DEBUG_LLM_IO=true to enable detailed LLM logging.")
    app.run(host='0.0.0.0', port=port) 