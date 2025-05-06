from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import hashlib
import time
import os

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Simplified follow-up questions - placeholder
FOLLOW_UP_QUESTIONS = [
    {
        "id": "followup1",
        "question": "Could you further explain the main factors you mentioned in your previous answer?",
        "shortText": "Explain main factors",
        "answer": ""
    },
    {
        "id": "followup2",
        "question": "How do these factors influence each other?",
        "shortText": "Factor relationships",
        "answer": ""
    },
    {
        "id": "followup3",
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
    qa_pair = data.get('qaPair')
    existing_causal_graph = data.get('existingCausalGraph')
    
    if not all([session_id, prolific_id, qa_pair]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Simplified causal graph generation - placeholder
    causal_graph = generate_placeholder_graph(
        qa_pair.get('question', ''), 
        qa_pair.get('answer', '')
    )
    
    # Return follow-up questions and causal graph
    return jsonify({
        "success": True,
        "sessionId": session_id,
        "prolificId": prolific_id,
        "qaPair": qa_pair,
        "followUpQuestions": FOLLOW_UP_QUESTIONS,
        "causalGraph": causal_graph,
        "timestamp": int(time.time())
    })

def generate_placeholder_graph(question, answer):
    """
    Generate simplified placeholder causal graph
    """
    # Create a deterministic ID based on input
    graph_id = hashlib.md5((question + answer).encode()).hexdigest()[:10]
    
    # Simplified fixed nodes and edges
    nodes = [
        {"id": "cause_1", "label": "Cause 1 (placeholder)", "type": "cause"},
        {"id": "cause_2", "label": "Cause 2 (placeholder)", "type": "cause"},
        {"id": "effect_1", "label": "Effect 1 (placeholder)", "type": "effect"},
    ]
    
    edges = [
        {"source": "cause_1", "target": "effect_1", "label": "causes"},
        {"source": "cause_2", "target": "effect_1", "label": "causes"}
    ]
    
    return {
        "id": f"graph_{graph_id}",
        "nodes": nodes,
        "edges": edges
    }

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port) 