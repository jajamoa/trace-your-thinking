"""
Run CBN similarity analysis between synthetic and real data
"""

from cbn_similarity_analyzer import CBNSimilarityAnalyzer
from unified_agent_generator import UnifiedAgentGenerator
import os
from pathlib import Path


def generate_test_agents(num_agents=50):
    """Generate test agents for analysis"""
    print(f"Generating {num_agents} test agents...")
    generator = UnifiedAgentGenerator(base_output_dir="test_analysis_agents")
    agents = generator.generate_batch_agents(num_agents)
    print(f"Generated {len(agents)} agents in test_analysis_agents/")
    return "test_analysis_agents"


def run_analysis_for_topic(topic='zoning', synthetic_dir='test_analysis_agents'):
    """Run similarity analysis for a specific topic"""
    print(f"\n{'='*80}")
    print(f"ANALYZING TOPIC: {topic.upper()}")
    print(f"{'='*80}\n")
    
    # Create analyzer
    analyzer = CBNSimilarityAnalyzer()
    
    # Set paths
    real_cbns_dir = "ref_data/cbns"
    output_dir = f"similarity_analysis/{topic}"
    
    # Load data
    analyzer.load_real_cbns(real_cbns_dir, topic)
    analyzer.load_synthetic_cbns(synthetic_dir, topic)
    
    # Check if we have data
    if len(analyzer.real_cbns) == 0:
        print(f"Warning: No real CBNs found for topic {topic}")
        return None
        
    if len(analyzer.synthetic_cbns) == 0:
        print(f"Warning: No synthetic CBNs found for topic {topic}")
        return None
    
    # Generate report
    overall_score = analyzer.generate_report(output_dir)
    
    return overall_score


def main():
    """Main function"""
    print("CBN Similarity Analysis Tool")
    print("="*80)
    
    # Check if we need to generate test agents
    synthetic_dir = "test_analysis_agents"
    if not Path(synthetic_dir).exists():
        print("No synthetic agents found. Generating test agents...")
        synthetic_dir = generate_test_agents(50)
    else:
        # Count existing agents
        agent_dirs = [d for d in Path(synthetic_dir).iterdir() if d.is_dir() and not d.name.startswith('.')]
        print(f"Found {len(agent_dirs)} existing agents in {synthetic_dir}")
    
    # Run analysis for each topic
    topics = ['zoning', 'healthcare', 'camera']
    results = {}
    
    for topic in topics:
        score = run_analysis_for_topic(topic, synthetic_dir)
        if score is not None:
            results[topic] = score
    
    # Print summary
    print(f"\n{'='*80}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*80}\n")
    
    for topic, score in results.items():
        print(f"{topic.capitalize()}: {score:.2%} overall similarity")
    
    print(f"\nDetailed reports saved in: similarity_analysis/")
    
    # Print insights about real data distribution
    print(f"\n{'='*80}")
    print("INSIGHTS ABOUT REAL DATA")
    print(f"{'='*80}\n")
    
    print("Why some CBNs have many nodes:")
    print("- Real CBNs show high variability in complexity")
    print("- Node count ranges from 1 to 253 (!) with mean ~52")
    print("- This reflects different levels of user engagement and thinking depth")
    print("- Some users create very detailed mental models with many connections")
    print("- Others focus on key concepts with fewer nodes")
    print("\nThe synthetic generator captures this variability by:")
    print("- Using the real distribution statistics (mean, std)")
    print("- Allowing for similar range of complexity")
    print("- Maintaining realistic node-to-edge ratios")


if __name__ == "__main__":
    main()
