"""
Batch experiment runner for testing multiple agent configurations
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env files
parent_dir = Path(__file__).parent.parent
env_path = parent_dir / '.env'
env_local_path = parent_dir / '.env.local'

if env_local_path.exists():
    load_dotenv(dotenv_path=env_local_path)
elif env_path.exists():
    load_dotenv(dotenv_path=env_path)

sys.path.append(str(parent_dir))

from experiment.run_experiment import ExperimentRunner
from experiment.custom_agent_example import CustomAgent
from experiment.agent_interface import SimpleAgent


def run_batch_experiments(experiments, output_dir="experiment/batch_results"):
    """
    Run multiple experiments with different configurations
    
    Args:
        experiments: List of experiment configurations
        output_dir: Directory to save batch results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Summary results
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*60}")
    print(f"Running Batch Experiments")
    print(f"Total experiments: {len(experiments)}")
    print(f"{'='*60}\n")
    
    for i, exp_config in enumerate(experiments, 1):
        print(f"\n--- Experiment {i}/{len(experiments)} ---")
        print(f"Name: {exp_config['name']}")
        print(f"Agent: {exp_config['agent_type']}")
        print(f"Topic: {exp_config.get('topic', 'climate change')}")
        
        try:
            # Create agent based on configuration
            if exp_config['agent_type'] == 'simple':
                agent = SimpleAgent()
            elif exp_config['agent_type'] == 'custom':
                stance = exp_config.get('stance', 'neutral')
                agent = CustomAgent(
                    agent_id=f"custom_{stance}",
                    stance=stance
                )
            else:
                print(f"Unknown agent type: {exp_config['agent_type']}")
                continue
                
            # Run experiment
            runner = ExperimentRunner(
                agent=agent,
                topic=exp_config.get('topic', 'climate change'),
                max_qa_count=exp_config.get('max_qa_count', 10),
                verbose=exp_config.get('verbose', False)
            )
            
            conv_file, graph_file = runner.run()
            
            # Load results for summary
            with open(graph_file, 'r') as f:
                graph = json.load(f)
                
            result = {
                'name': exp_config['name'],
                'status': 'success',
                'conversation_file': conv_file,
                'graph_file': graph_file,
                'stats': {
                    'total_nodes': len(graph.get('nodes', {})),
                    'total_edges': len(graph.get('edges', {})),
                    'anchor_nodes': len(graph.get('anchor_queue', [])),
                    'qa_count': graph.get('qa_counter', 0)
                }
            }
            
            results.append(result)
            print(f"✓ Experiment completed successfully")
            
        except Exception as e:
            print(f"✗ Experiment failed: {str(e)}")
            results.append({
                'name': exp_config['name'],
                'status': 'failed',
                'error': str(e)
            })
            
    # Save batch summary
    summary_file = f"{output_dir}/batch_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total_experiments': len(experiments),
            'successful': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'results': results
        }, f, indent=2)
        
    # Print summary
    print(f"\n{'='*60}")
    print("BATCH EXPERIMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {len(experiments)}")
    print(f"Success: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"Failed: {sum(1 for r in results if r['status'] == 'failed')}")
    print(f"\nSummary saved to: {summary_file}")
    
    # Print detailed results
    print("\nDetailed Results:")
    for result in results:
        if result['status'] == 'success':
            stats = result['stats']
            print(f"\n{result['name']}:")
            print(f"  Nodes: {stats['total_nodes']} (Anchors: {stats['anchor_nodes']})")
            print(f"  Edges: {stats['total_edges']}")
            print(f"  QA Pairs: {stats['qa_count']}")
        else:
            print(f"\n{result['name']}: FAILED - {result.get('error', 'Unknown error')}")


def main():
    """Run predefined batch experiments"""
    
    # Check API key
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("ERROR: DASHSCOPE_API_KEY environment variable not set")
        sys.exit(1)
        
    # Define experiments
    experiments = [
        # Test different stances on same topic
        {
            'name': 'Climate_Supportive',
            'agent_type': 'custom',
            'stance': 'supportive',
            'topic': 'climate change',
            'max_qa_count': 10,
            'verbose': False
        },
        {
            'name': 'Climate_Opposed',
            'agent_type': 'custom',
            'stance': 'opposed',
            'topic': 'climate change',
            'max_qa_count': 10,
            'verbose': False
        },
        {
            'name': 'Climate_Neutral',
            'agent_type': 'custom',
            'stance': 'neutral',
            'topic': 'climate change',
            'max_qa_count': 10,
            'verbose': False
        },
        
        # Test different topics
        {
            'name': 'AI_Ethics_Simple',
            'agent_type': 'simple',
            'topic': 'artificial intelligence ethics',
            'max_qa_count': 8,
            'verbose': False
        },
        {
            'name': 'Healthcare_Neutral',
            'agent_type': 'custom',
            'stance': 'neutral',
            'topic': 'universal healthcare',
            'max_qa_count': 8,
            'verbose': False
        }
    ]
    
    # Run experiments
    run_batch_experiments(experiments)


if __name__ == "__main__":
    main()
