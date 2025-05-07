from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import hashlib
import time
import os
import uuid

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Simplified follow-up questions - placeholder
FOLLOW_UP_QUESTIONS = [
    {
        "id": None,  # Will be dynamically generated when needed
        "question": "Could you further explain the main factors you mentioned in your previous answer?",
        "shortText": "Explain main factors",
        "answer": ""
    },
    {
        "id": None,  # Will be dynamically generated when needed
        "question": "How do these factors influence each other?",
        "shortText": "Factor relationships",
        "answer": ""
    },
    {
        "id": None,  # Will be dynamically generated when needed
        "question": "Which factor do you think has the greatest impact, and why?",
        "shortText": "Most influential factor",
        "answer": ""
    }
]

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

# Main API endpoint - simplified as placeholder
@app.route('/api/process_answer', methods=['POST'])
def process_answer():
    """
    Process answer API - placeholder version
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    # Extract required parameters
    session_id = data.get('sessionId')
    prolific_id = data.get('prolificId')
    qa_pair = data.get('qaPair')  # Current QA pair being processed
    qa_pairs = data.get('qaPairs', [])  # All QA pairs in the session
    current_index = data.get('currentQuestionIndex', 0)  # Current question index
    existing_causal_graph = data.get('existingCausalGraph')
    
    if not all([session_id, prolific_id, qa_pair]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    print(f"Processing answer for question {current_index + 1}/{len(qa_pairs)}: {qa_pair.get('question', '')[:50]}...")
    
    # Get texts from all existing questions to avoid duplicating follow-up questions
    current_question_texts = []
    
    # Add the current question
    if qa_pair.get('question'):
        current_question_texts.append(qa_pair.get('question'))
    
    # Add all questions from the session's qaPairs
    for pair in qa_pairs:
        if pair.get('question') and pair.get('question') not in current_question_texts:
            current_question_texts.append(pair.get('question'))
    
    # Check if any existing QA pairs were provided in the causal graph
    if existing_causal_graph and 'qas' in existing_causal_graph:
        # Extract existing question texts to avoid duplicates
        for qa in existing_causal_graph.get('qas', []):
            if 'question' in qa and qa['question'] not in current_question_texts:
                current_question_texts.append(qa['question'])
    
    # Filter follow-up questions to exclude similar questions
    filtered_follow_ups = []
    for q in FOLLOW_UP_QUESTIONS:
        # Simple content comparison - if question text is not already asked
        if q['question'] not in current_question_texts:
            # Create a deep copy of the question to avoid modifying the original
            follow_up = q.copy()
            # Generate a unique ID using timestamp and a random component
            follow_up['id'] = f"followup_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            filtered_follow_ups.append(follow_up)
    
    # Limit number of follow-up questions based on current position in the session
    # If we're near the end (last 3 questions), don't add more follow-ups
    remaining_questions = len(qa_pairs) - current_index - 1
    if remaining_questions <= 3:
        filtered_follow_ups = []  # No more follow-ups near the end
    elif remaining_questions <= 5:
        filtered_follow_ups = filtered_follow_ups[:1]  # Just one follow-up for near-end questions
    else:
        filtered_follow_ups = filtered_follow_ups[:2]  # Regular limit
    
    print(f"Added {len(filtered_follow_ups)} follow-up questions")
    
    # Simplified causal graph generation - placeholder
    causal_graph = generate_placeholder_graph(
        prolific_id,
        qa_pair.get('id', ''),
        qa_pair.get('question', ''), 
        qa_pair.get('answer', ''),
        existing_causal_graph
    )
    
    # Return follow-up questions and causal graph
    return jsonify({
        "success": True,
        "sessionId": session_id,
        "prolificId": prolific_id,
        "qaPair": qa_pair,
        "followUpQuestions": filtered_follow_ups,
        "causalGraph": causal_graph,
        "timestamp": int(time.time())
    })

def generate_placeholder_graph(agent_id, qa_id, question, answer, existing_graph=None):
    """
    Generate a causal graph following the data schema format
    
    Args:
        agent_id (str): User's ID (prolificId)
        qa_id (str): Current QA pair ID
        question (str): Current question text
        answer (str): Current answer text
        existing_graph (dict): Existing causal graph to update, if any
        
    Returns:
        dict: A causal graph conforming to the data schema format
    """
    # Create a deterministic ID based on input, adding timestamp for uniqueness if needed
    if not qa_id.startswith("qa_"):
        # Add timestamp to ensure uniqueness
        time_component = int(time.time())
        qa_id_clean = f"qa_{qa_id}_{time_component}"
    else:
        qa_id_clean = qa_id
    
    # Initialize with existing graph or create new one
    if existing_graph and isinstance(existing_graph, dict):
        graph = existing_graph
        # Ensure the required top-level structures exist
        graph.setdefault('agent_id', agent_id)
        graph.setdefault('nodes', {})
        graph.setdefault('edges', {})
        graph.setdefault('qas', [])
    else:
        # Create new graph structure following the schema
        graph = {
            "agent_id": agent_id,
            "nodes": {},
            "edges": {},
            "qas": []
        }
    
    # If this is a new QA pair, add nodes and edges
    if not any(qa['qa_id'] == qa_id_clean for qa in graph['qas']):
        # Create two simple nodes to represent the key concepts
        # Use node IDs based on the number of existing nodes
        next_node_id = 1 + len(graph['nodes'])
        
        # Create first node (external state)
        n1_id = f"n{next_node_id}"
        graph['nodes'][n1_id] = {
            "id": n1_id,
            "label": f"Factor 1 from {qa_id_clean}",
            "type": "binary",
            "values": [True, False],
            "semantic_role": "external_state",
            "appearance": {
                "qa_ids": [qa_id_clean],
                "frequency": 1
            },
            "incoming_edges": [],
            "outgoing_edges": []
        }
        
        # Create second node (internal affect)
        n2_id = f"n{next_node_id + 1}"
        graph['nodes'][n2_id] = {
            "id": n2_id,
            "label": f"Factor 2 from {qa_id_clean}",
            "type": "binary",
            "values": [True, False],
            "semantic_role": "internal_affect",
            "appearance": {
                "qa_ids": [qa_id_clean],
                "frequency": 1
            },
            "incoming_edges": [],
            "outgoing_edges": []
        }
        
        # Create an edge connecting the nodes
        next_edge_id = 1 + len(graph['edges'])
        edge_id = f"e{next_edge_id}"
        
        # Update node edge references
        graph['nodes'][n1_id]["outgoing_edges"].append(edge_id)
        graph['nodes'][n2_id]["incoming_edges"].append(edge_id)
        
        # Create the edge with sigmoid function
        graph['edges'][edge_id] = {
            "from": n1_id,
            "to": n2_id,
            "function": {
                "target": n2_id,
                "inputs": [n1_id],
                "function_type": "sigmoid",
                "parameters": {
                    "weights": [0.8],
                    "bias": 0.2
                },
                "noise_std": 0.1,
                "support_qas": [qa_id_clean],
                "confidence": 0.7
            },
            "support_qas": [qa_id_clean]
        }
        
        # Add the QA pair with parsed belief
        graph['qas'].append({
            "qa_id": qa_id_clean,
            "question": question,
            "answer": answer,
            "parsed_belief": {
                "belief_structure": {
                    "from": n1_id,
                    "to": n2_id,
                    "direction": "positive"
                },
                "belief_strength": {
                    "estimated_probability": 0.7,
                    "confidence_rating": 0.6
                },
                "counterfactual": f"If {graph['nodes'][n1_id]['label']} were different, {graph['nodes'][n2_id]['label']} would change."
            }
        })
    
    return graph

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port) 