"""
Test script to verify the experiment environment is working correctly
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env files
parent_dir = Path(__file__).parent.parent
env_path = parent_dir / '.env'
env_local_path = parent_dir / '.env.local'

if env_local_path.exists():
    load_dotenv(dotenv_path=env_local_path)
elif env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Add parent directory to path
sys.path.append(str(parent_dir))

from experiment.conversation_manager import ConversationManager
from experiment.agent_interface import SimpleAgent
from experiment.run_experiment import ExperimentRunner


def test_basic_functionality():
    """Test basic conversation functionality"""
    print("Testing basic functionality...")
    
    # Check API key
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("WARNING: DASHSCOPE_API_KEY not set. Using mock mode.")
        # For testing without API key, we'll need to mock the LLM calls
        return False
    
    # Create simple agent
    agent = SimpleAgent()
    
    # Test question processing
    test_question = {
        "id": "test_1",
        "question": "What are your thoughts on climate change?",
        "shortText": "Initial thoughts",
        "type": "initial"
    }
    
    answer = agent.process_question(test_question)
    print(f"Agent response: {answer[:50]}...")
    
    return True


def test_mini_conversation():
    """Run a mini conversation (3 QA pairs)"""
    print("\nTesting mini conversation...")
    
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("Skipping: Requires DASHSCOPE_API_KEY")
        return
        
    # Create runner with small QA count
    agent = SimpleAgent()
    runner = ExperimentRunner(
        agent=agent,
        topic="climate change",
        max_qa_count=3,
        verbose=True
    )
    
    # Run experiment
    try:
        conversation_file, graph_file = runner.run()
        print(f"\nSuccess! Files created:")
        print(f"  - {conversation_file}")
        print(f"  - {graph_file}")
        
        # Check if files exist
        if os.path.exists(conversation_file) and os.path.exists(graph_file):
            print("Files verified to exist.")
            return True
        else:
            print("ERROR: Files not found!")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False


def test_custom_agent():
    """Test custom agent functionality"""
    print("\nTesting custom agent...")
    
    # Import custom agent
    from experiment.custom_agent_example import CustomAgent
    
    # Create agents with different stances
    agents = {
        "supportive": CustomAgent(stance="supportive"),
        "opposed": CustomAgent(stance="opposed"),
        "neutral": CustomAgent(stance="neutral")
    }
    
    # Test question
    test_q = {
        "id": "test_custom",
        "question": "What factors influence this issue?",
        "shortText": "Influencing factors",
        "type": "node_discovery"
    }
    
    print("\nDifferent agent responses to same question:")
    for stance, agent in agents.items():
        response = agent.process_question(test_q)
        print(f"\n{stance.capitalize()} agent: {response}")
        
    return True


def main():
    """Run all tests"""
    print("="*60)
    print("Testing Chatbot-Agent Experiment Environment")
    print("="*60)
    
    # Test 1: Basic functionality
    if test_basic_functionality():
        print("✓ Basic functionality test passed")
    else:
        print("✗ Basic functionality test failed")
        
    # Test 2: Custom agents
    if test_custom_agent():
        print("✓ Custom agent test passed")
    else:
        print("✗ Custom agent test failed")
        
    # Test 3: Mini conversation (requires API key)
    if os.getenv('DASHSCOPE_API_KEY'):
        if test_mini_conversation():
            print("✓ Mini conversation test passed")
        else:
            print("✗ Mini conversation test failed")
    else:
        print("⚠ Mini conversation test skipped (no API key)")
        
    print("\n" + "="*60)
    print("Testing complete!")
    
    # Instructions for running full experiment
    print("\nTo run a full experiment:")
    print("1. Set DASHSCOPE_API_KEY environment variable")
    print("2. Run: python experiment/run_experiment.py")
    print("\nFor custom agents:")
    print("1. Extend BaseAgent class")
    print("2. Implement process_question() method")
    print("3. Use ExperimentRunner with your agent")


if __name__ == "__main__":
    main()
