#!/usr/bin/env python3
"""
Quick start script for chatbot-agent experiments
Run this to get started immediately
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

# Check for API key
if not os.getenv('DASHSCOPE_API_KEY'):
    print("="*60)
    print("ERROR: DASHSCOPE_API_KEY not set")
    print("="*60)
    print("\nTo use this experiment environment, you need to set the DASHSCOPE_API_KEY.")
    print("\nRecommended setup:")
    print("1. Copy the example file:")
    print("   cp experiment/env.example .env.local")
    print("\n2. Edit .env.local with your API key:")
    print("   DASHSCOPE_API_KEY=your_actual_api_key_here")
    print("\n3. Alternative - export in shell:")
    print("   export DASHSCOPE_API_KEY='your-api-key'")
    print("\nThen run this script again.")
    sys.exit(1)

print("="*60)
print("Chatbot-Agent Experiment - Quick Start")
print("="*60)

print("\nWhat would you like to do?")
print("1. Run a simple test conversation")
print("2. Run with interactive agent (you provide responses)")
print("3. Test different agent stances")
print("4. Run batch experiments")
print("5. Visualize existing results")

choice = input("\nEnter your choice (1-5): ").strip()

if choice == "1":
    print("\nRunning simple test conversation...")
    os.system("python experiment/run_experiment.py --agent simple --max-qa 5")
    
elif choice == "2":
    print("\nRunning with interactive agent...")
    print("You will be prompted to provide responses for the agent.")
    os.system("python experiment/run_experiment.py --agent interactive --max-qa 5")
    
elif choice == "3":
    print("\nTesting different agent stances...")
    from experiment.run_experiment import ExperimentRunner
    from experiment.custom_agent_example import CustomAgent
    
    for stance in ["supportive", "neutral", "opposed"]:
        print(f"\n--- Testing {stance} agent ---")
        agent = CustomAgent(stance=stance)
        runner = ExperimentRunner(agent, max_qa_count=5, verbose=False)
        conv_file, graph_file = runner.run()
        print(f"Results saved: {graph_file}")
        
elif choice == "4":
    print("\nRunning batch experiments...")
    os.system("python experiment/batch_experiments.py")
    
elif choice == "5":
    # List available results
    export_dir = Path("experiment/exports")
    if export_dir.exists():
        graph_files = list(export_dir.glob("causal_graph_*.json"))
        
        if graph_files:
            print(f"\nFound {len(graph_files)} graph files:")
            for i, f in enumerate(graph_files[:10], 1):
                print(f"{i}. {f.name}")
                
            if len(graph_files) > 10:
                print(f"... and {len(graph_files) - 10} more")
                
            choice = input("\nEnter number to visualize (or press Enter for latest): ").strip()
            
            if choice.isdigit() and 1 <= int(choice) <= len(graph_files):
                selected = graph_files[int(choice) - 1]
            else:
                selected = sorted(graph_files)[-1]  # Latest file
                
            print(f"\nVisualizing: {selected.name}")
            os.system(f"python experiment/visualize_graph.py {selected}")
        else:
            print("\nNo results found. Run an experiment first!")
    else:
        print("\nNo exports directory found. Run an experiment first!")
        
else:
    print("\nInvalid choice. Please run the script again.")

print("\n" + "="*60)
print("For more options, see experiment/README.md")
print("="*60)
