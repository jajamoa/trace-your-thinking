"""
Enhanced Unified Agent Data Generator
Generates richer prompt CBNs with more nodes and edges
"""
import json
import random
import os
import uuid
from datetime import datetime
from pathlib import Path
import numpy as np
from collections import deque

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
    
    def extract_rich_subgraph(self, full_cbn, target_nodes=15, max_nodes=20):
        """Extract a rich subgraph centered around stance node using BFS"""
        stance_node_id = full_cbn.get('stance_node_id', 'n1')
        nodes = full_cbn.get('nodes', {})
        edges = full_cbn.get('edges', {})
        
        # Start with stance node
        selected_nodes = {stance_node_id}
        selected_edges = set()
        
        # Build adjacency map
        adjacency = {node_id: set() for node_id in nodes}
        edge_map = {}
        
        for edge_id, edge in edges.items():
            source = edge['source']
            target = edge['target']
            if source in nodes and target in nodes:
                adjacency[source].add(target)
                adjacency[target].add(source)
                edge_map[(source, target)] = edge_id
                edge_map[(target, source)] = edge_id
        
        # BFS to find nodes within 2-3 hops from stance
        queue = deque([(stance_node_id, 0)])
        distances = {stance_node_id: 0}
        
        while queue and len(selected_nodes) < max_nodes:
            current_node, distance = queue.popleft()
            
            # Add nodes within 2 hops
            if distance <= 2:
                for neighbor in adjacency[current_node]:
                    if neighbor not in distances:
                        distances[neighbor] = distance + 1
                        queue.append((neighbor, distance + 1))
                        if len(selected_nodes) < max_nodes:
                            selected_nodes.add(neighbor)
        
        # If we need more nodes, add high-importance nodes
        if len(selected_nodes) < target_nodes:
            # Calculate node scores
            node_scores = []
            for node_id, node in nodes.items():
                if node_id not in selected_nodes:
                    score = node.get('importance', 0.5) * node.get('aggregate_confidence', 0.5)
                    # Bonus for nodes with many connections
                    score += len(adjacency[node_id]) * 0.1
                    node_scores.append((node_id, score))
            
            # Sort by score and add top nodes
            node_scores.sort(key=lambda x: x[1], reverse=True)
            for node_id, _ in node_scores:
                if len(selected_nodes) >= target_nodes:
                    break
                selected_nodes.add(node_id)
                
                # Try to connect this node to existing subgraph
                for existing_node in list(selected_nodes):
                    if existing_node in adjacency[node_id]:
                        break
        
        # Find all edges between selected nodes
        for edge_id, edge in edges.items():
            source = edge['source']
            target = edge['target']
            if source in selected_nodes and target in selected_nodes:
                selected_edges.add(edge_id)
        
        return selected_nodes, selected_edges
    
    def generate_prompt_cbn(self, full_cbn):
        """Generate richer prompt CBN with more nodes and edges"""
        # Extract rich subgraph
        selected_nodes, selected_edges = self.extract_rich_subgraph(full_cbn, target_nodes=15, max_nodes=20)
        
        # Build simplified nodes
        simplified_nodes = {}
        for node_id in selected_nodes:
            if node_id in full_cbn['nodes']:
                node = full_cbn['nodes'][node_id]
                simplified_nodes[node_id] = {
                    'label': node['label'],
                    'is_stance': node.get('is_stance', False)
                }
        
        # Build simplified edges
        simplified_edges = []
        edges_seen = set()
        
        for edge_id in selected_edges:
            if edge_id in full_cbn['edges']:
                edge = full_cbn['edges'][edge_id]
                source = edge['source']
                target = edge['target']
                
                # Avoid duplicates
                edge_pair = (min(source, target), max(source, target))
                if edge_pair not in edges_seen:
                    edges_seen.add(edge_pair)
                    
                    correlation = edge.get('correlation', 0.5)
                    direction = 'positive' if correlation >= 0.5 else 'negative'
                    
                    simplified_edges.append({
                        'source': source,
                        'target': target,
                        'direction': direction
                    })
        
        # Ensure stance node has connections if needed
        stance_node_id = full_cbn.get('stance_node_id', 'n1')
        stance_connections = sum(1 for e in simplified_edges if e['source'] == stance_node_id or e['target'] == stance_node_id)
        
        if stance_connections < 2 and len(simplified_nodes) > 3:
            # Add some strategic connections to stance
            node_list = list(simplified_nodes.keys())
            node_list.remove(stance_node_id)
            random.shuffle(node_list)
            
            for node in node_list[:2]:
                if stance_connections >= 2:
                    break
                # Check if connection already exists
                exists = any((e['source'] == stance_node_id and e['target'] == node) or 
                           (e['source'] == node and e['target'] == stance_node_id) 
                           for e in simplified_edges)
                if not exists:
                    simplified_edges.append({
                        'source': node,
                        'target': stance_node_id,
                        'direction': random.choice(['positive', 'negative'])
                    })
                    stance_connections += 1
        
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
            
            # Report richer statistics
            print(f"  Generated GT CBN and prompt CBN for {topic} (nodes: {len(prompt_cbn['nodes'])}, edges: {len(prompt_cbn['edges'])})")
            
            with open(agent_dir / f"prompt_cbn_{topic}.json", 'w') as f:
                json.dump(prompt_cbn, f, indent=2)
        
        # Create survey reaction files with proper format
        for t in self.topics:
            reaction_data = {
                agent_id: {
                    "opinions": {},
                    "reasons": {},
                    "timestamp": datetime.now().isoformat()
                }
            }
            with open(survey_dir / f"{t}_reaction.json", 'w') as f:
                json.dump(reaction_data, f, indent=2)
        
        # Create proper transcript CSV files with reference format
        for t in self.topics:
            csv_path = transcript_raw_dir / f"{t}.csv"
            with open(csv_path, 'w') as f:
                # Generate session metadata
                session_id = f"session_{int(datetime.now().timestamp() * 1000)}_{agent_id[:8]}"
                created_at = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
                
                # Write session metadata
                f.write(f"Session ID,{session_id}\n")
                f.write(f"Prolific ID,{agent_id}\n")
                f.write("Status,pending\n")
                f.write("Progress,0/0\n")
                f.write(f"Created At,\"{created_at}\"\n")
                f.write(f"Updated At,\"{created_at}\"\n")
                f.write("Completed At,\n")
                f.write("\n")
                f.write("Question Number,Question,Answer\n")
        
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
            'note': 'Enhanced version with richer prompt CBNs (15-20 nodes)'
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
