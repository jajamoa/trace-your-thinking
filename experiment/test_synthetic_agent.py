#!/usr/bin/env python3
"""
Test script for synthetic agent functionality
"""
import json
from pathlib import Path
from synthetic_agent import SyntheticAgent


def test_synthetic_agent():
    """Test basic synthetic agent functionality"""
    print("Testing Synthetic Agent Implementation")
    print("="*60)
    
    # Get first available agent
    agent_dir = Path("agent_data/synthetic_agents")
    agent_dirs = [d for d in agent_dir.iterdir() 
                 if d.is_dir() and not d.name.endswith(".json")]
    
    if not agent_dirs:
        print("ERROR: No synthetic agents found!")
        return
        
    # Use first agent
    test_agent_dir = agent_dirs[0]
    agent_id = test_agent_dir.name
    
    print(f"\nTesting with agent: {agent_id}")
    
    # Create agent
    agent = SyntheticAgent(agent_id, test_agent_dir)
    
    # Test demographic loading
    print(f"\nDemographic data loaded: {bool(agent.demographic)}")
    if agent.demographic:
        print(f"  Housing status: {agent.demographic.get('housing_status', 'N/A')}")
        print(f"  Age: {agent.demographic.get('age', 'N/A')}")
    
    # Test each topic
    topics = ['zoning', 'healthcare', 'camera']
    
    for topic in topics:
        print(f"\n\nTesting topic: {topic}")
        print("-"*40)
        
        # Set topic
        agent.set_topic(topic)
        
        # Check if CBN prompt loaded
        if agent.current_cbn_prompt:
            print(f"✓ CBN prompt loaded successfully")
            nodes = agent.current_cbn_prompt.get('nodes', {})
            edges = agent.current_cbn_prompt.get('edges', [])
            print(f"  Nodes: {len(nodes)}")
            print(f"  Edges: {len(edges)}")
            
            # Test some questions
            test_questions = [
                {
                    "id": "q1",
                    "question": f"What are your thoughts on {topic}?",
                    "shortText": "Initial stance",
                    "type": "initial"
                },
                {
                    "id": "q2", 
                    "question": "What factors influence your view?",
                    "shortText": "Influencing factors",
                    "type": "factors"
                },
                {
                    "id": "q3",
                    "question": "What do you think is most important?",
                    "shortText": "Importance",
                    "type": "importance"
                }
            ]
            
            for q in test_questions:
                answer = agent.process_question(q)
                print(f"\nQ: {q['question']}")
                print(f"A: {answer[:100]}...")
        else:
            print(f"✗ Failed to load CBN prompt for {topic}")
    
    print("\n\nTest completed!")


if __name__ == "__main__":
    test_synthetic_agent()
