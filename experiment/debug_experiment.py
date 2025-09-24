#!/usr/bin/env python3
"""
Debug script to test single agent processing
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from run_synthetic_experiments import process_single_agent_topic

def test_single_agent():
    """Test processing a single agent-topic combination"""
    
    # Find first available agent
    agent_dir = Path("agent_data/synthetic_agents")
    agents = [d for d in agent_dir.iterdir() if d.is_dir() and not d.name.endswith('.json')]
    
    if not agents:
        print("No agents found!")
        return
    
    agent = agents[0]
    agent_id = agent.name
    
    print(f"Testing agent: {agent_id}")
    print(f"Agent path: {agent}")
    
    # Test with one topic
    topic = "zoning"
    args = (agent_id, topic, str(agent), 5, True)  # max_qa=5, verbose=True
    
    print(f"Testing: {agent_id} - {topic}")
    print("=" * 50)
    
    try:
        result = process_single_agent_topic(args)
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    try:
        from llm_agent import create_synthetic_agent
        print("✓ llm_agent import OK")
        
        from conversation_manager import ConversationManager
        print("✓ conversation_manager import OK")
        
        agent = create_synthetic_agent('test', 'agent_data/synthetic_agents/eb07fffc610d4786b2d5bad0')
        print("✓ Agent creation OK")
        
        cm = ConversationManager('zoning', 5)
        print("✓ ConversationManager creation OK")
        
        return True
    except Exception as e:
        print(f"Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("DEBUG: Experiment debugging")
    print("=" * 30)
    
    if test_imports():
        print("\nTesting single agent processing...")
        test_single_agent()
    else:
        print("Import test failed!")
