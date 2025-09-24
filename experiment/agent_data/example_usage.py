"""
Example usage of the unified agent generator
"""
from unified_agent_generator import UnifiedAgentGenerator
import json


def example_generate_agents_for_experiment():
    """Example: Generate agents for an experiment"""
    print("=== Example: Generating agents for experiment ===\n")
    
    # Create generator with custom output directory
    generator = UnifiedAgentGenerator(
        base_output_dir="experiment_agents_batch1"
    )
    
    # Generate 100 agents with all topics
    print("Generating 100 agents...")
    agents = generator.generate_batch_agents(
        num_agents=100
    )
    
    print(f"\nSuccessfully generated {len(agents)} agents!")
    print("Agent data saved in: experiment_agents_batch1/")
    

def example_generate_multiple_batches():
    """Example: Generate multiple batches of agents"""
    print("\n=== Example: Generating multiple batches ===\n")
    
    generator = UnifiedAgentGenerator(
        base_output_dir="multi_batch_agents"
    )
    
    batch_sizes = [20, 30, 50]
    all_agents = []
    
    for i, size in enumerate(batch_sizes):
        print(f"\nGenerating batch {i+1}: {size} agents...")
        agents = generator.generate_batch_agents(
            num_agents=size
        )
        all_agents.extend(agents)
    
    print(f"\nTotal agents generated: {len(all_agents)}")
    print(f"Each agent has GT CBNs for topics: {', '.join(all_agents[0]['topics'])}")


def example_access_agent_data():
    """Example: Access and use generated agent data"""
    print("\n=== Example: Accessing agent data ===\n")
    
    # First generate a few agents
    generator = UnifiedAgentGenerator(base_output_dir="demo_agents")
    agents = generator.generate_batch_agents(num_agents=3)
    
    # Access the first agent's data
    first_agent = agents[0]
    agent_id = first_agent['agent_id']
    agent_path = first_agent['path']
    
    print(f"Accessing data for agent: {agent_id}")
    
    # Read demographic data
    with open(f"{agent_path}/demographic/demographic.json", 'r') as f:
        demographic = json.load(f)
    print(f"\nDemographic data:")
    print(f"  Age: {demographic[agent_id]['age']}")
    print(f"  Income: {demographic[agent_id]['household_income']}")
    print(f"  Housing: {demographic[agent_id]['housing_status']}")
    
    # Read GT CBNs
    print(f"\nGT CBN summaries:")
    for topic in ['zoning', 'healthcare', 'camera']:
        with open(f"{agent_path}/gt_cbn_{topic}.json", 'r') as f:
            cbn = json.load(f)
        print(f"  {topic}: {len(cbn['nodes'])} nodes, {len(cbn['edges'])} edges")


def example_custom_generation():
    """Example: Custom agent generation with specific parameters"""
    print("\n=== Example: Custom generation ===\n")
    
    generator = UnifiedAgentGenerator(base_output_dir="custom_agents")
    
    # Generate a single agent with specific ID
    custom_id = "experiment_001_agent_01"
    
    # Override the generate_agent_id method for this example
    original_method = generator.generate_agent_id
    generator.generate_agent_id = lambda: custom_id
    
    # Generate the agent
    agent_dir = generator.create_agent_structure(custom_id)
    
    # Restore original method
    generator.generate_agent_id = original_method
    
    print(f"Generated custom agent: {custom_id}")
    print(f"Location: {agent_dir}")


if __name__ == "__main__":
    # Run all examples
    print("Unified Agent Generator - Usage Examples\n")
    print("=" * 50)
    
    # Example 1: Basic experiment generation
    example_generate_agents_for_experiment()
    
    # Example 2: Multiple batches
    # example_generate_multiple_batches()  # Uncomment to run
    
    # Example 3: Accessing agent data
    # example_access_agent_data()  # Uncomment to run
    
    # Example 4: Custom generation
    # example_custom_generation()  # Uncomment to run
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nNote: Uncomment other examples in the main block to run them.")
