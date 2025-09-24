#!/usr/bin/env python3
"""
Simplified experiment runner without parallel processing
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from run_synthetic_experiments import process_single_agent_topic

def main():
    parser = argparse.ArgumentParser(description='Run synthetic agent experiments (sequential)')
    parser.add_argument('--topics', nargs='+', 
                      choices=['zoning', 'healthcare', 'surveillance'],
                      default=['zoning', 'healthcare', 'surveillance'],
                      help='Topics to run')
    parser.add_argument('--max-qa', type=int, default=20,
                      help='Maximum QA pairs per conversation')
    parser.add_argument('--agent-dir', default='agent_data/synthetic_agents',
                      help='Directory containing synthetic agent data')
    
    args = parser.parse_args()
    
    agent_data_dir = Path(args.agent_dir)
    topics = args.topics
    max_qa_count = args.max_qa
    
    # Get all agent directories
    agent_dirs = [d for d in agent_data_dir.iterdir() 
                 if d.is_dir() and not d.name.endswith('.json')]
    
    if not agent_dirs:
        print("No synthetic agents found!")
        return
    
    print(f"Found {len(agent_dirs)} synthetic agents")
    print(f"Topics to process: {', '.join(topics)}")
    print(f"Max QA pairs per conversation: {max_qa_count}")
    print("Running in SEQUENTIAL mode (no parallelization)")
    print("=" * 60)
    
    # Prepare all agent-topic combinations
    tasks = []
    for agent_dir in agent_dirs:
        agent_id = agent_dir.name
        for topic in topics:
            tasks.append((agent_id, topic, str(agent_dir), max_qa_count, False))
    
    print(f"\nProcessing {len(tasks)} agent-topic combinations sequentially...")
    print("-" * 60)
    
    # Process sequentially
    results = []
    successful = 0
    failed = 0
    skipped = 0
    
    for i, task in enumerate(tasks):
        agent_id, topic = task[0], task[1]
        progress = f"[{i+1}/{len(tasks)} {((i+1)/len(tasks)*100):.1f}%]"
        
        print(f"\nProcessing: {agent_id} - {topic} {progress}")
        
        try:
            result = process_single_agent_topic(task)
            results.append(result)
            
            if result["status"] == "success":
                successful += 1
                print(f"SUCCESS: {agent_id} - {topic} (QA: {result['qa_count']}) {progress}")
            elif result["status"] == "skipped":
                skipped += 1
                print(f"SKIP: {agent_id} - {topic} (already processed) {progress}")
            else:
                failed += 1
                error_msg = result.get('error', 'Unknown error')
                print(f"ERROR: {agent_id} - {topic}: {error_msg} {progress}")
                
        except Exception as e:
            failed += 1
            print(f"ERROR: {agent_id} - {topic}: {str(e)} {progress}")
            results.append({
                "agent_id": agent_id,
                "topic": topic,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    print("\n" + "=" * 60)
    print(f"Completed: {successful} successful, {failed} failed, {skipped} skipped")
    print(f"Total tasks: {len(tasks)}")
    
    return results

if __name__ == "__main__":
    main()

