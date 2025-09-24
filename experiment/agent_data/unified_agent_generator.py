"""
Unified Agent Data Generator
Generates complete agent data including demographics, GT CBN, and folder structure
"""
import json
import random
import os
import uuid
from datetime import datetime
from pathlib import Path
import numpy as np

try:
    from .balanced_synthetic_cbn_generator import BalancedSyntheticCBNGenerator
    from .edge_aware_synthetic_cbn_generator import EdgeAwareSyntheticCBNGenerator
    from .cbn_statistics_analyzer import CBNStatisticsAnalyzer
except ImportError:
    from balanced_synthetic_cbn_generator import BalancedSyntheticCBNGenerator
    from edge_aware_synthetic_cbn_generator import EdgeAwareSyntheticCBNGenerator
    from cbn_statistics_analyzer import CBNStatisticsAnalyzer


class UnifiedAgentGenerator:
    """Generates complete agent data with demographics and GT CBN"""
    
    def __init__(self, base_output_dir="synthetic_agents"):
        self.base_output_dir = base_output_dir
        self.load_demographic_schema()
        self.topics = ['zoning', 'healthcare', 'camera']  # Available topics for GT CBN generation
        
    def load_demographic_schema(self):
        """Load the demographic survey schema"""
        schema_path = Path(__file__).parent / "ref_data" / "survey_demographicQ.json"
        with open(schema_path, 'r') as f:
            self.demographic_schema = json.load(f)
    
    def generate_agent_id(self):
        """Generate unique agent ID similar to existing format"""
        # Using hex format similar to existing IDs
        return uuid.uuid4().hex[:24]
    
    def sample_demographic_value(self, field_name, field_config):
        """Sample a value for a demographic field based on its configuration"""
        field_type = field_config.get('type')
        options = field_config.get('options')
        
        if field_name == 'housing_experience':
            # Generate realistic housing experience text
            templates = [
                "I have been renting for {years} years. The rent has increased {increase}% over the last few years. {sentiment}",
                "I moved {times} times in the past five years due to {reason}. {sentiment}",
                "I've been living in the same {housing_type} for {years} years. {sentiment}",
                "Recently {change} my living situation. {reason_detail}. {sentiment}"
            ]
            
            template = random.choice(templates)
            experience = template.format(
                years=random.randint(1, 10),
                increase=random.randint(10, 50),
                times=random.randint(1, 4),
                housing_type=random.choice(['apartment', 'house', 'condo', 'townhouse']),
                change=random.choice(['changed', 'upgraded', 'downsized']),
                reason=random.choice(['rent increases', 'job relocation', 'family changes', 'landlord issues']),
                reason_detail=random.choice([
                    'The landlord decided to sell the property',
                    'I found a better location closer to work',
                    'Family circumstances changed',
                    'The neighborhood became too expensive'
                ]),
                sentiment=random.choice([
                    'I am satisfied with my current housing situation.',
                    'Housing affordability is a major concern for me.',
                    'I feel stable in my current home.',
                    'I worry about future rent increases.'
                ])
            )
            return experience
            
        elif field_name == 'age':
            # Generate age between 18-80
            return str(random.randint(18, 80))
            
        elif field_name == 'zipcode':
            # Generate valid US zipcode format
            return f"{random.randint(10000, 99999)}"
            
        elif field_type == 'string' and options:
            # Single choice from options
            return random.choice(options)
            
        elif field_type == 'array':
            # Multiple choice - select 1-3 items
            if field_name == 'transportation':
                # Most people have 1-2 modes of transport
                num_choices = random.choices([1, 2, 3], weights=[0.5, 0.4, 0.1])[0]
            elif field_name == 'race_ethnicity':
                # Most people select 1 race/ethnicity
                num_choices = random.choices([1, 2], weights=[0.85, 0.15])[0]
            elif field_name == 'children_age':
                # Handle special case for children
                if random.random() < 0.6:  # 60% have no children
                    return ["No Children"]
                else:
                    num_choices = random.randint(1, 2)
                    choices = random.sample(
                        [item for item in field_config['items']['enum'] if item != "No Children"],
                        num_choices
                    )
                    return choices
            else:
                num_choices = random.randint(1, min(3, len(field_config['items']['enum'])))
            
            choices = random.sample(field_config['items']['enum'], num_choices)
            return choices
            
        else:
            # Default for unknown types
            return "Not specified"
    
    def generate_demographic_data(self, agent_id):
        """Generate complete demographic data for an agent"""
        demographic_data = {}
        
        # Generate each field based on schema
        for field_name, field_config in self.demographic_schema['properties'].items():
            value = self.sample_demographic_value(field_name, field_config)
            
            # Special handling for array fields that should be single values in output
            if field_name == 'transportation' and isinstance(value, list):
                value = value[0] if len(value) == 1 else ' / '.join(value)
            elif field_name == 'race_ethnicity' and isinstance(value, list):
                value = value[0] if len(value) == 1 else ', '.join(value)
            elif field_name == 'children_age' and isinstance(value, list):
                value = value[0] if len(value) == 1 else ', '.join(value)
            
            demographic_data[field_name] = value
        
        # Ensure logical consistency
        if demographic_data.get('has_children') == 'No':
            demographic_data['children_age'] = 'No Children'
        
        if demographic_data.get('housing_status') != 'Renter':
            demographic_data['rent_income_ratio'] = 'Not computed'
        
        return {agent_id: demographic_data}
    
    def generate_gt_cbn(self, agent_id, topic='zoning'):
        """Generate ground truth CBN for the agent"""
        # Load statistics for the topic
        analyzer = CBNStatisticsAnalyzer()
        cbns_root = Path(__file__).parent / "ref_data" / "cbns"
        statistics = analyzer.get_topic_statistics(str(cbns_root), topic)
        
        # Generate CBN using appropriate generator
        if topic == 'camera':
            # Use edge-aware generator for camera topic
            edge_pattern_file = cbns_root / topic / f"{topic}_edge_patterns.json"
            edge_patterns = None
            if edge_pattern_file.exists():
                with open(edge_pattern_file, 'r') as f:
                    edge_patterns = json.load(f)
            generator = EdgeAwareSyntheticCBNGenerator(statistics, edge_patterns)
        else:
            # Use balanced generator for other topics
            generator = BalancedSyntheticCBNGenerator(statistics)
        
        cbn = generator.generate_cbn(agent_id=agent_id, topic=topic)
        
        # Validate CBN
        if not generator.validate_cbn(cbn):
            print(f"Warning: CBN validation failed for agent {agent_id}, regenerating...")
            # Try again
            cbn = generator.generate_cbn(agent_id=agent_id, topic=topic)
        
        return cbn
    
    def generate_prompt_cbn(self, full_cbn):
        """Generate simplified CBN for prompting - only connected nodes with stance"""
        # Start with stance node
        stance_node_id = full_cbn.get('stance_node_id', 'n1')
        
        # Find all connected nodes
        connected_nodes = set([stance_node_id])
        edges_to_include = []
        
        # Get all edges and track connected nodes
        for edge_id, edge in full_cbn.get('edges', {}).items():
            source = edge['source']
            target = edge['target']
            connected_nodes.add(source)
            connected_nodes.add(target)
            edges_to_include.append((edge_id, edge))
        
        # Build simplified nodes - only include connected nodes
        simplified_nodes = {}
        for node_id in connected_nodes:
            if node_id in full_cbn['nodes']:
                node = full_cbn['nodes'][node_id]
                # Only keep essential info
                simplified_nodes[node_id] = {
                    'label': node['label'],
                    'is_stance': node.get('is_stance', False)
                }
        
        # Build simplified edges - only direction matters
        simplified_edges = []
        for edge_id, edge in edges_to_include:
            correlation = edge.get('correlation', 0.5)
            # Determine if positive or negative relationship
            direction = 'positive' if correlation >= 0.5 else 'negative'
            
            simplified_edges.append({
                'source': edge['source'],
                'target': edge['target'],
                'direction': direction
            })
        
        # Create prompt CBN structure
        prompt_cbn = {
            'stance_node': stance_node_id,
            'nodes': simplified_nodes,
            'edges': simplified_edges
        }
        
        return prompt_cbn
    
    def create_agent_structure(self, agent_id):
        """Create complete agent folder structure with all data"""
        # Create base agent directory
        agent_dir = Path(self.base_output_dir) / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        demographic_dir = agent_dir / "demographic"
        survey_dir = agent_dir / "survey"
        transcript_dir = agent_dir / "transcript"
        transcript_raw_dir = transcript_dir / "raw"
        cbn_dir = agent_dir / "cbn"  # New directory for CBNs
        
        demographic_dir.mkdir(exist_ok=True)
        survey_dir.mkdir(exist_ok=True)
        transcript_dir.mkdir(exist_ok=True)
        transcript_raw_dir.mkdir(exist_ok=True)
        cbn_dir.mkdir(exist_ok=True)
        
        # Generate and save demographic data
        demographic_data = self.generate_demographic_data(agent_id)
        with open(demographic_dir / "demographic.json", 'w') as f:
            json.dump(demographic_data, f, indent=2)
        
        # Generate and save GT CBN for each topic
        for topic in self.topics:
            gt_cbn = self.generate_gt_cbn(agent_id, topic)
            
            # Save full GT CBN in cbn folder
            with open(cbn_dir / f"gt_cbn_{topic}.json", 'w') as f:
                json.dump(gt_cbn, f, indent=2)
            
            # Generate and save simplified prompt CBN
            prompt_cbn = self.generate_prompt_cbn(gt_cbn)
            with open(agent_dir / f"prompt_cbn_{topic}.json", 'w') as f:
                json.dump(prompt_cbn, f, indent=2)
            
            print(f"  Generated GT CBN and prompt CBN for {topic}")
        
        # Create empty survey reaction files
        for t in self.topics:
            reaction_data = {
                agent_id: {
                    "reaction": "",
                    "timestamp": datetime.now().isoformat()
                }
            }
            with open(survey_dir / f"{t}_reaction.json", 'w') as f:
                json.dump(reaction_data, f, indent=2)
        
        # Create empty transcript CSV files
        for t in self.topics:
            csv_path = transcript_raw_dir / f"{t}.csv"
            with open(csv_path, 'w') as f:
                # Write CSV header
                f.write("timestamp,speaker,content\n")
        
        print(f"Created agent structure for {agent_id}")
        return agent_dir
    
    def generate_batch_agents(self, num_agents):
        """Generate multiple agents with complete data structures"""
        generated_agents = []
        
        for i in range(num_agents):
            agent_id = self.generate_agent_id()
            agent_dir = self.create_agent_structure(agent_id)
            generated_agents.append({
                'agent_id': agent_id,
                'path': str(agent_dir),
                'topics': self.topics  # All agents have GT CBNs for all topics
            })
            print(f"Generated agent {i+1}/{num_agents}: {agent_id}")
        
        # Save summary
        summary_path = Path(self.base_output_dir) / "generation_summary.json"
        summary = {
            'generated_at': datetime.now().isoformat(),
            'num_agents': num_agents,
            'topics_per_agent': self.topics,
            'agents': generated_agents
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nGeneration complete! Generated {num_agents} agents in {self.base_output_dir}")
        print(f"Summary saved to: {summary_path}")
        
        return generated_agents


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate synthetic agent data')
    parser.add_argument('--num_agents', type=int, default=10, 
                       help='Number of agents to generate (default: 10)')
    parser.add_argument('--output_dir', type=str, 
                       default='synthetic_agents',
                       help='Output directory for generated agents (default: synthetic_agents)')
    
    args = parser.parse_args()
    
    # Create generator and generate agents
    generator = UnifiedAgentGenerator(base_output_dir=args.output_dir)
    generator.generate_batch_agents(args.num_agents)


if __name__ == "__main__":
    main()
