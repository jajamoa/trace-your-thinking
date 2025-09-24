#!/usr/bin/env python3
"""
Test single experiment without parallel processing
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from run_synthetic_experiments import process_single_agent_topic

def main():
    # Find first agent
    agent_dir = Path("agent_data/synthetic_agents")
    agents = [d for d in agent_dir.iterdir() if d.is_dir() and not d.name.endswith('.json')]
    
    if not agents:
        print("No agents found!")
        return
    
    agent = agents[0]
    agent_id = agent.name
    
    print(f"Testing single agent: {agent_id}")
    print(f"Topic: zoning")
    print("=" * 50)
    
    # Create task
    task = (agent_id, "zoning", str(agent), 3, True)  # max_qa=3, verbose=True
    
    print("Starting task...")
    try:
        result = process_single_agent_topic(task)
        print("Task completed!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Task failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
