#!/usr/bin/env python3
"""
Debug parallel processing issues
"""
import sys
import os
import multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

def simple_task(task_id):
    """Simple test task"""
    time.sleep(1)  # Simulate work
    return f"Task {task_id} completed"

def test_basic_multiprocessing():
    """Test basic multiprocessing"""
    print("Testing basic multiprocessing...")
    
    tasks = list(range(5))
    
    print(f"Creating ProcessPoolExecutor with {multiprocessing.cpu_count()} workers")
    
    try:
        with ProcessPoolExecutor(max_workers=2) as executor:
            print("Submitting tasks...")
            futures = {executor.submit(simple_task, task_id): task_id for task_id in tasks}
            
            print("Waiting for results...")
            for future in as_completed(futures, timeout=30):
                task_id = futures[future]
                try:
                    result = future.result()
                    print(f"✓ {result}")
                except Exception as e:
                    print(f"✗ Task {task_id} failed: {e}")
        
        print("Basic multiprocessing test PASSED")
        return True
    except Exception as e:
        print(f"Basic multiprocessing test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_experiment_function():
    """Test the actual experiment function"""
    print("\nTesting experiment function...")
    
    try:
        from run_synthetic_experiments import process_single_agent_topic
        
        # Find first agent
        agent_dir = Path("agent_data/synthetic_agents")
        agents = [d for d in agent_dir.iterdir() if d.is_dir() and not d.name.endswith('.json')]
        
        if not agents:
            print("No agents found!")
            return False
        
        agent = agents[0]
        agent_id = agent.name
        
        task = (agent_id, "zoning", str(agent), 3, False)  # max_qa=3, verbose=False
        
        print(f"Testing task: {task}")
        
        # Test in main process first
        print("Testing in main process...")
        result = process_single_agent_topic(task)
        print(f"Main process result: {result}")
        
        # Test in subprocess
        print("Testing in subprocess...")
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(process_single_agent_topic, task)
            result = future.result(timeout=60)
            print(f"Subprocess result: {result}")
        
        print("Experiment function test PASSED")
        return True
        
    except Exception as e:
        print(f"Experiment function test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports_in_subprocess():
    """Test if imports work in subprocess"""
    print("\nTesting imports in subprocess...")
    
    def test_imports():
        try:
            import sys
            from pathlib import Path
            
            parent_dir = Path(__file__).parent.parent
            sys.path.append(str(parent_dir))
            
            from conversation_manager import ConversationManager
            from llm_agent import create_synthetic_agent
            
            return "Imports successful"
        except Exception as e:
            return f"Import failed: {e}"
    
    try:
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(test_imports)
            result = future.result(timeout=30)
            print(f"Import test result: {result}")
            
            if "successful" in result:
                print("Import test PASSED")
                return True
            else:
                print("Import test FAILED")
                return False
                
    except Exception as e:
        print(f"Import test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Debugging parallel processing issues")
    print("=" * 50)
    
    # Test 1: Basic multiprocessing
    test1 = test_basic_multiprocessing()
    
    # Test 2: Imports in subprocess
    test2 = test_imports_in_subprocess()
    
    # Test 3: Experiment function
    test3 = test_experiment_function()
    
    print("\n" + "=" * 50)
    print("Summary:")
    print(f"Basic multiprocessing: {'PASS' if test1 else 'FAIL'}")
    print(f"Imports in subprocess: {'PASS' if test2 else 'FAIL'}")
    print(f"Experiment function: {'PASS' if test3 else 'FAIL'}")
    
    if all([test1, test2, test3]):
        print("\n✓ All tests passed - parallel processing should work")
    else:
        print("\n✗ Some tests failed - investigating...")

