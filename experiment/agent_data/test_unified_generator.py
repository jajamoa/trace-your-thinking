"""
Test script for the unified agent generator
"""
from unified_agent_generator import UnifiedAgentGenerator
import sys


def test_single_agent():
    """Test generating a single agent"""
    print("Testing single agent generation...")
    generator = UnifiedAgentGenerator(base_output_dir="test_synthetic_agents")
    
    # Generate one agent
    agent_id = generator.generate_agent_id()
    agent_dir = generator.create_agent_structure(agent_id)
    print(f"Generated agent at: {agent_dir}")


def test_batch_generation(num_agents=5):
    """Test batch generation of agents"""
    print(f"\nTesting batch generation of {num_agents} agents...")
    generator = UnifiedAgentGenerator(base_output_dir="test_synthetic_agents")
    
    # Generate multiple agents
    agents = generator.generate_batch_agents(num_agents)
    
    print(f"\nGenerated {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent['agent_id']} (topics: {', '.join(agent['topics'])})")


if __name__ == "__main__":
    # Run tests
    test_single_agent()
    
    # Get number of agents from command line or use default
    num_agents = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    test_batch_generation(num_agents)
