"""
Fixed Unified Agent Data Generator
Ensures no empty CBNs by guaranteeing stance node connectivity
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
    
    def validate_cbn_connectivity(self, cbn):
        """Ensure stance node has at least one connection"""
        stance_node_id = cbn.get('stance_node_id', 'n1')
        stance_node = cbn['nodes'].get(stance_node_id, {})
        
        # Check if stance node has any edges
        if not stance_node.get('incoming_edges') and not stance_node.get('outgoing_edges'):
            return False
        return True
    
    def generate_gt_cbn(self, agent_id, topic='zoning'):
        """Generate ground truth CBN for the agent with guaranteed connectivity"""
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
        
        # Generate CBN with retry logic to ensure connectivity
        max_attempts = 10
        for attempt in range(max_attempts):
            cbn = generator.generate_cbn(agent_id=agent_id, topic=topic)
            
            # Validate CBN structure
            if not generator.validate_cbn(cbn):
                if attempt < max_attempts - 1:
                    continue
                else:
                    print(f"Warning: CBN validation failed for agent {agent_id} after {max_attempts} attempts")
            
            # Check connectivity
            if self.validate_cbn_connectivity(cbn):
                return cbn
            
            # If not connected, add edges to stance node
            if attempt == max_attempts - 1:
                # Force connectivity as last resort
                stance_node_id = cbn.get('stance_node_id', 'n1')
                nodes = list(cbn['nodes'].keys())
                if len(nodes) > 1:
                    # Add at least 2 edges to stance node
                    other_nodes = [n for n in nodes if n != stance_node_id]
                    if other_nodes:
                        # Add incoming edge
                        source_node = random.choice(other_nodes)
                        edge_id = f"e{len(cbn['edges']) + 1}"
                        cbn['edges'][edge_id] = {
                            "source": source_node,
                            "target": stance_node_id,
                            "weight": 0.5,
                            "correlation": 0.5
                        }
                        cbn['nodes'][source_node]['outgoing_edges'].append(edge_id)
                        cbn['nodes'][stance_node_id]['incoming_edges'].append(edge_id)
                        
                        # Add outgoing edge if possible
                        remaining_nodes = [n for n in other_nodes if n != source_node]
                        if remaining_nodes:
                            target_node = random.choice(remaining_nodes)
                            edge_id = f"e{len(cbn['edges']) + 1}"
                            cbn['edges'][edge_id] = {
                                "source": stance_node_id,
                                "target": target_node,
                                "weight": 0.5,
                                "correlation": 0.5
                            }
                            cbn['nodes'][stance_node_id]['outgoing_edges'].append(edge_id)
                            cbn['nodes'][target_node]['incoming_edges'].append(edge_id)
                
                return cbn
        
        return cbn
    
    def generate_prompt_cbn(self, full_cbn):
        """Generate simplified CBN for prompting - only connected nodes with stance"""
        # Start with stance node
        stance_node_id = full_cbn.get('stance_node_id', 'n1')
        
        # Find all nodes connected to stance node (direct connections)
        connected_nodes = set([stance_node_id])
        edges_to_include = []
        
        # Get direct connections to stance node
        stance_node = full_cbn['nodes'].get(stance_node_id, {})
        
        # Process incoming edges to stance
        for edge_id in stance_node.get('incoming_edges', []):
            if edge_id in full_cbn['edges']:
                edge = full_cbn['edges'][edge_id]
                connected_nodes.add(edge['source'])
                edges_to_include.append((edge_id, edge))
        
        # Process outgoing edges from stance
        for edge_id in stance_node.get('outgoing_edges', []):
            if edge_id in full_cbn['edges']:
                edge = full_cbn['edges'][edge_id]
                connected_nodes.add(edge['target'])
                edges_to_include.append((edge_id, edge))
        
        # If still no connections, include closest nodes
        if len(connected_nodes) == 1:
            # Find nodes with highest importance/confidence
            node_scores = []
            for node_id, node in full_cbn['nodes'].items():
                if node_id != stance_node_id:
                    score = node.get('importance', 0.5) * node.get('aggregate_confidence', 0.5)
                    node_scores.append((node_id, score))
            
            # Sort by score and take top 2-3 nodes
            node_scores.sort(key=lambda x: x[1], reverse=True)
            for node_id, _ in node_scores[:3]:
                connected_nodes.add(node_id)
                # Create artificial edges for prompt
                edges_to_include.append((None, {
                    'source': node_id,
                    'target': stance_node_id,
                    'correlation': 0.5
                }))
        
        # Build simplified nodes
        simplified_nodes = {}
        for node_id in connected_nodes:
            if node_id in full_cbn['nodes']:
                node = full_cbn['nodes'][node_id]
                simplified_nodes[node_id] = {
                    'label': node['label'],
                    'is_stance': node.get('is_stance', False)
                }
        
        # Build simplified edges
        simplified_edges = []
        for edge_id, edge in edges_to_include:
            correlation = edge.get('correlation', 0.5)
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
            
            # Validate prompt CBN is not empty
            if len(prompt_cbn['nodes']) > 1 and len(prompt_cbn['edges']) > 0:
                print(f"  Generated GT CBN and prompt CBN for {topic} (nodes: {len(prompt_cbn['nodes'])}, edges: {len(prompt_cbn['edges'])})")
            else:
                print(f"  WARNING: Generated minimal prompt CBN for {topic} (nodes: {len(prompt_cbn['nodes'])}, edges: {len(prompt_cbn['edges'])})")
            
            with open(agent_dir / f"prompt_cbn_{topic}.json", 'w') as f:
                json.dump(prompt_cbn, f, indent=2)
        
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
            'agents': generated_agents,
            'note': 'Fixed version ensures no empty prompt CBNs'
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
