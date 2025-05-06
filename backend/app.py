from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import hashlib
import time
import os

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Fixed follow-up questions
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

@app.route('/api/process_answer', methods=['POST'])
def process_answer():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    session_id = data.get('sessionId')
    prolific_id = data.get('prolificId')
    qa_pair = data.get('qaPair')
    
    if not all([session_id, prolific_id, qa_pair]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Generate causal graph based on the answer
    causal_graph = generate_causal_graph(qa_pair.get('question', ''), qa_pair.get('answer', ''))
    
    # Return follow-up questions and causal graph for frontend to store
    return jsonify({
        "success": True,
        "sessionId": session_id,
        "prolificId": prolific_id,
        "qaPair": qa_pair,
        "followUpQuestions": FOLLOW_UP_QUESTIONS,
        "causalGraph": causal_graph,
        "timestamp": int(time.time())
    })

def generate_causal_graph(question, answer):
    """
    Generate a simple causal graph. In a real application, 
    this would likely use more complex NLP or rule-based logic.
    """
    # Create a deterministic ID based on input
    graph_id = hashlib.md5((question + answer).encode()).hexdigest()[:10]
    
    # Extract potential causes and effects (simplified version)
    # In a real implementation, this would use NLP to identify causal relationships
    causes = extract_causes(question, answer)
    effects = extract_effects(question, answer)
    
    # Create nodes for each cause and effect
    nodes = []
    edges = []
    
    # Add cause nodes
    for i, cause in enumerate(causes):
        nodes.append({
            "id": f"cause_{i}",
            "label": cause,
            "type": "cause"
        })
    
    # Add effect nodes and connect to causes
    for i, effect in enumerate(effects):
        effect_id = f"effect_{i}"
        nodes.append({
            "id": effect_id,
            "label": effect,
            "type": "effect"
        })
        
        # Connect each cause to this effect
        for j in range(len(causes)):
            edges.append({
                "source": f"cause_{j}",
                "target": effect_id,
                "label": "causes"
            })
    
    # If no nodes were created, create default ones
    if not nodes:
        nodes = [
            {"id": "cause", "label": f"Question: {question[:30]}...", "type": "cause"},
            {"id": "effect", "label": f"Answer: {answer[:30]}...", "type": "effect"}
        ]
        edges = [
            {"source": "cause", "target": "effect", "label": "causes"}
        ]
    
    return {
        "id": f"graph_{graph_id}",
        "nodes": nodes,
        "edges": edges
    }

def extract_causes(question, answer):
    """
    Extract potential causes from the answer.
    This is a simplified implementation - a real version would use NLP.
    """
    # Simple implementation - look for common cause indicators
    causes = []
    sentences = answer.split('.')
    
    cause_indicators = ["because", "since", "due to", "as a result of", "leads to"]
    
    for sentence in sentences:
        sentence = sentence.strip().lower()
        if any(indicator in sentence for indicator in cause_indicators):
            # Get a simplified version of the cause
            for indicator in cause_indicators:
                if indicator in sentence:
                    parts = sentence.split(indicator)
                    if len(parts) > 1:
                        cause = parts[1].strip()
                        if cause and len(cause) > 5:
                            causes.append(cause[:50] + ("..." if len(cause) > 50 else ""))
    
    # If no causes found, use a simplified approach
    if not causes and len(answer) > 10:
        words = answer.split()
        if len(words) > 5:
            causes = [" ".join(words[:5]) + "..."]
    
    return causes[:3]  # Limit to 3 causes

def extract_effects(question, answer):
    """
    Extract potential effects from the answer.
    This is a simplified implementation - a real version would use NLP.
    """
    # Simple implementation - look for common effect indicators
    effects = []
    sentences = answer.split('.')
    
    effect_indicators = ["therefore", "thus", "consequently", "as a result", "this means"]
    
    for sentence in sentences:
        sentence = sentence.strip().lower()
        if any(indicator in sentence for indicator in effect_indicators):
            # Get a simplified version of the effect
            for indicator in effect_indicators:
                if indicator in sentence:
                    parts = sentence.split(indicator)
                    if len(parts) > 1:
                        effect = parts[1].strip()
                        if effect and len(effect) > 5:
                            effects.append(effect[:50] + ("..." if len(effect) > 50 else ""))
    
    # If no effects found, use a simplified approach
    if not effects and len(answer) > 10:
        words = answer.split()
        if len(words) > 5:
            effects = [" ".join(words[-5:]) + "..."]
    
    return effects[:2]  # Limit to 2 effects

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port) 