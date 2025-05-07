"""
Simplified usage example for QwenLLMExtractor
This script demonstrates how to use the QwenLLMExtractor to extract nodes from question-answer pairs,
with a focus on ensuring that a stance node is always created as a starting point.
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from llm_extractor import QwenLLMExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main function to demonstrate simplified QwenLLMExtractor usage
    """
    # Load environment variables from parent directory .env or .env.local file
    parent_env_path = Path(__file__).parent.parent / '.env'
    parent_env_local_path = Path(__file__).parent.parent / '.env.local'
    
    if parent_env_local_path.exists():
        load_dotenv(dotenv_path=parent_env_local_path)
        logger.info(f"Loaded environment variables from {parent_env_local_path}")
    elif parent_env_path.exists():
        load_dotenv(dotenv_path=parent_env_path)
        logger.info(f"Loaded environment variables from {parent_env_path}")
    else:
        logger.warning(f"No environment file found at {parent_env_path} or {parent_env_local_path}")
    
    # Initialize the extractor with API key from environment variable
    try:
        extractor = QwenLLMExtractor(
            api_key=os.getenv('DASHSCOPE_API_KEY'),
            model="qwen-plus"
        )
        logger.info("Extractor initialized successfully")
    except ValueError as e:
        logger.error(f"Failed to initialize extractor: {e}")
        return
    
    # Create a storage for nodes
    node_store = {
        "user_id": "example_user",
        "nodes": {},
        "stance_node_id": None,
        "qa_history": []
    }
    
    # Example QA pairs for testing
    qa_pairs = [
        {
            "id": "qa_1",
            "question": "What do you think about increasing housing density in urban areas?",
            "answer": "I think increasing housing density is generally good for affordability, but it can lead to more traffic congestion and noise if not properly planned. Public transportation needs to be expanded alongside density increases."
        },
        {
            "id": "qa_2",
            "question": "How would improved public transportation affect your concerns about increased housing density?",
            "answer": "If public transportation was significantly improved, I would be much more supportive of increased housing density. Good transit reduces the need for cars, which helps with both traffic congestion and parking issues."
        },
        {
            "id": "qa_3",
            "question": "Do you think the government should subsidize affordable housing in high-density areas?",
            "answer": "Yes, I believe government subsidies for affordable housing are essential in high-density areas. Without subsidies, only luxury housing tends to get built, which doesn't help solve the housing crisis for middle and lower-income residents."
        }
    ]
    
    # Process each QA pair
    for i, qa_pair in enumerate(qa_pairs):
        logger.info(f"\n\nProcessing QA pair {i+1}/{len(qa_pairs)}")
        logger.info(f"Question: {qa_pair['question']}")
        logger.info(f"Answer: {qa_pair['answer'][:50]}...")
        
        # For the first QA pair, ensure we create a stance node
        ensure_stance = i == 0
        extracted_nodes = extractor.extract_nodes(qa_pair, ensure_stance_node=ensure_stance)
        
        # Update node store
        if extracted_nodes:
            logger.info(f"Extracted {len(extracted_nodes)} nodes")
            
            # Check for stance nodes
            stance_nodes = [node_id for node_id, node in extracted_nodes.items() 
                         if node.get('is_stance') or node.get('semantic_role') == 'behavioral_intention']
            
            # If we found a stance node and don't have one yet, set it
            if stance_nodes and not node_store.get('stance_node_id'):
                node_store['stance_node_id'] = stance_nodes[0]
                logger.info(f"Set stance node: {extracted_nodes[stance_nodes[0]]['label']}")
            
            # Add or update nodes
            for node_id, node in extracted_nodes.items():
                if node_id in node_store['nodes']:
                    # Update existing node
                    node_store['nodes'][node_id]['appearance']['frequency'] += 1
                    if qa_pair['id'] not in node_store['nodes'][node_id]['appearance']['qa_ids']:
                        node_store['nodes'][node_id]['appearance']['qa_ids'].append(qa_pair['id'])
                    logger.info(f"Updated existing node: {node['label']}")
                else:
                    # Add new node
                    node_store['nodes'][node_id] = node
                    logger.info(f"Added new node: {node['label']}")
        else:
            logger.warning(f"No nodes extracted from QA pair {i+1}")
        
        # Add QA pair to history
        node_store['qa_history'].append({
            'id': qa_pair['id'],
            'question': qa_pair['question'],
            'answer': qa_pair['answer']
        })
        
        # Print current state
        logger.info(f"Current node count: {len(node_store['nodes'])}")
        if node_store.get('stance_node_id'):
            stance_node = node_store['nodes'].get(node_store['stance_node_id'], {})
            logger.info(f"Stance node: {stance_node.get('label', 'None')}")
    
    # Save the final node store to a file
    with open('example_node_store.json', 'w') as f:
        json.dump(node_store, f, indent=2)
    
    logger.info("\nNode store saved to example_node_store.json")
    
    # Print summary of all extracted nodes
    logger.info("\nAll extracted nodes:")
    for node_id, node in node_store['nodes'].items():
        logger.info(f"- {node['label']} (role: {node.get('semantic_role', 'unknown')}, stance: {node.get('is_stance', False)})")

if __name__ == '__main__':
    main() 