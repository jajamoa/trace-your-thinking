"""
Synthetic CBN Generator
Generates synthetic Causal Belief Networks based on statistical patterns from real data
"""
import json
import random
import numpy as np
import uuid
from datetime import datetime
import os
from pathlib import Path

try:
    from .cbn_statistics_analyzer import CBNStatisticsAnalyzer
except ImportError:
    from cbn_statistics_analyzer import CBNStatisticsAnalyzer


class SyntheticCBNGenerator:
    """Generates synthetic CBNs based on statistical patterns"""
    
    def __init__(self, statistics):
        self.stats = statistics
        self.common_words = [word for word, _ in statistics.get('top_words', [])[:50]]
        
        # Topic-specific vocabulary templates
        self.topic_templates = {
            'zoning': [
                'housing', 'development', 'density', 'affordable', 'neighborhood',
                'community', 'upzoning', 'residential', 'commercial', 'mixed-use',
                'transit', 'walkability', 'gentrification', 'property', 'values',
                'planning', 'zoning', 'building', 'permits', 'regulations'
            ],
            'healthcare': [
                'medical', 'insurance', 'coverage', 'access', 'cost', 'quality',
                'universal', 'private', 'public', 'option', 'treatment', 'care',
                'patient', 'doctor', 'hospital', 'prescription', 'preventive',
                'healthcare', 'medicine', 'clinic', 'emergency', 'surgery'
            ],
            'camera': [
                'surveillance', 'privacy', 'security', 'monitoring', 'cameras',
                'safety', 'crime', 'prevention', 'public', 'spaces', 'civil',
                'liberties', 'protection', 'recording', 'observation', 'tracking',
                'technology', 'facial', 'recognition', 'data', 'collection'
            ],
            'climate': [
                'climate', 'change', 'environment', 'carbon', 'emission', 'renewable',
                'energy', 'sustainability', 'green', 'policy', 'regulation', 'future',
                'technology', 'innovation', 'responsibility', 'action', 'warming',
                'pollution', 'conservation', 'ecosystem', 'biodiversity'
            ]
        }
        
    def generate_node_label(self, topic='zoning', is_stance=False):
        """Generate node label based on topic"""
        # Get topic words
        topic_words = self.topic_templates.get(topic, self.topic_templates['zoning'])
        
        if is_stance:
            # Stance node should be clear support/opposition
            stance_patterns = [
                f"Support for {random.choice(topic_words)}",
                f"Opposition to {random.choice(topic_words)}",
                f"Concerns about {random.choice(topic_words)}",
                f"Benefits of {random.choice(topic_words)}"
            ]
            return random.choice(stance_patterns)
        
        # Regular node label patterns
        patterns = [
            lambda: f"{random.choice(topic_words).capitalize()}",
            lambda: f"{random.choice(topic_words).capitalize()} {random.choice(['concerns', 'benefits', 'issues', 'impact', 'effects'])}",
            lambda: f"{random.choice(['Support for', 'Opposition to', 'Concerns about', 'Benefits of'])} {random.choice(topic_words)}",
            lambda: f"{random.choice(topic_words).capitalize()} and {random.choice(topic_words)}",
            lambda: f"{random.choice(['Economic', 'Social', 'Environmental', 'Political'])} {random.choice(['factors', 'considerations', 'impacts'])}",
            lambda: f"{random.choice(topic_words).capitalize()} {random.choice(['quality', 'access', 'availability', 'implementation'])}",
        ]
        
        return random.choice(patterns)()
        
    def generate_confidence(self):
        """Generate confidence value based on statistics"""
        mean = self.stats['confidence']['mean']
        std = self.stats['confidence']['std']
        value = np.random.normal(mean, std)
        return max(0.1, min(1.0, value))
        
    def generate_importance(self):
        """Generate importance value based on statistics"""
        mean = self.stats['importance']['mean']
        std = self.stats['importance']['std']
        value = np.random.normal(mean, std)
        return max(0.1, min(1.0, value))
        
    def generate_weight(self):
        """Generate edge weight based on statistics"""
        mean = self.stats['weight']['mean']
        std = self.stats['weight']['std']
        value = abs(np.random.normal(mean, std))
        return max(0.1, min(1.0, value))
        
    def generate_correlation(self):
        """Generate edge correlation based on statistics"""
        mean = self.stats['correlation']['mean']
        std = self.stats['correlation']['std']
        value = np.random.normal(mean, std)
        return max(-1.0, min(1.0, value))
        
    def generate_cbn(self, agent_id=None, topic='zoning'):
        """
        Generate a synthetic CBN with exactly one stance node
        
        Args:
            agent_id: Unique identifier for the agent
            topic: Topic for the CBN (zoning, healthcare, camera, climate)
            
        Returns:
            dict: Complete CBN structure
        """
        if agent_id is None:
            agent_id = f"synth_{uuid.uuid4().hex[:8]}"
            
        # Generate node count based on statistics
        node_count = int(np.random.normal(
            self.stats['node_count']['mean'],
            self.stats['node_count']['std']
        ))
        node_count = max(2, min(100, node_count))  # Reasonable bounds
        
        # Generate edge count
        max_possible_edges = node_count * (node_count - 1) // 2
        edge_count = int(np.random.normal(
            self.stats['edge_count']['mean'],
            self.stats['edge_count']['std']
        ))
        edge_count = max(1, min(max_possible_edges, edge_count))
        
        # Create CBN structure
        cbn = {
            "agent_id": agent_id,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "nodes": {},
            "edges": {},
            "qa_history": {},
            "stance_node_id": "n1",  # Always the first node
            "step": "completed",
            "anchor_queue": [],
            "node_counter": node_count,
            "edge_counter": edge_count,
            "qa_counter": random.randint(8, 15)
        }
        
        # CRITICAL: Generate exactly ONE stance node (always n1)
        stance_confidence = 0.8 + random.uniform(-0.1, 0.15)  # High confidence for stance
        cbn["nodes"]["n1"] = {
            "label": self.generate_node_label(topic, is_stance=True),
            "aggregate_confidence": stance_confidence,
            "evidence": [
                {"qa_id": "system", "confidence": 1.0, "importance": 1.0}
            ],
            "importance": 1.0,
            "incoming_edges": [],
            "outgoing_edges": [],
            "status": "anchor",
            "frequency": 1,
            "is_stance": True  # CRITICAL: Only this node is stance
        }
        cbn["anchor_queue"].append("n1")
        
        # Generate other nodes (all non-stance)
        anchor_ratio = self.stats['anchor_ratio']['mean']
        
        for i in range(2, node_count + 1):
            node_id = f"n{i}"
            
            # Generate evidence count
            evidence_count = max(1, int(np.random.normal(
                self.stats['evidence_count']['mean'],
                self.stats['evidence_count']['std']
            )))
            evidence_count = min(evidence_count, 5)  # Reasonable limit
            
            # Generate evidence
            evidence = []
            for j in range(evidence_count):
                evidence.append({
                    "qa_id": f"qa{random.randint(1, 15)}",
                    "confidence": self.generate_confidence(),
                    "importance": self.generate_importance()
                })
            
            # Calculate aggregate confidence
            if evidence:
                # Weighted average by importance
                total_weight = sum(e['importance'] for e in evidence)
                if total_weight > 0:
                    aggregate_confidence = sum(e['confidence'] * e['importance'] for e in evidence) / total_weight
                else:
                    aggregate_confidence = sum(e['confidence'] for e in evidence) / len(evidence)
            else:
                aggregate_confidence = self.generate_confidence()
                
            # Calculate importance
            if evidence:
                importance = sum(e['importance'] for e in evidence) / len(evidence)
            else:
                importance = self.generate_importance()
            
            # Determine node status
            is_anchor = random.random() < anchor_ratio
            
            node = {
                "label": self.generate_node_label(topic, is_stance=False),  # CRITICAL: Never stance
                "aggregate_confidence": aggregate_confidence,
                "evidence": evidence,
                "importance": importance,
                "incoming_edges": [],
                "outgoing_edges": [],
                "status": "anchor" if is_anchor else "candidate",
                "frequency": 1,
                "is_stance": False  # CRITICAL: Only n1 can be stance
            }
            
            cbn["nodes"][node_id] = node
            
            # Add to anchor queue if it's an anchor
            if is_anchor:
                cbn["anchor_queue"].append(node_id)
        
        # Generate edges
        node_ids = list(cbn["nodes"].keys())
        edges_created = 0
        edge_id = 1
        
        # Ensure stance node has some connections (2-4 connections)
        stance_connections = min(random.randint(2, 4), node_count - 1)
        connected_to_stance = set()
        
        for _ in range(stance_connections):
            if edges_created >= edge_count:
                break
                
            # Choose target node that isn't already connected to stance
            available_targets = [n for n in node_ids if n != "n1" and n not in connected_to_stance]
            if not available_targets:
                break
                
            target = random.choice(available_targets)
            connected_to_stance.add(target)
            
            # Randomly choose direction
            if random.random() < 0.5:
                # From stance to target
                source, target_node = "n1", target
            else:
                # From target to stance
                source, target_node = target, "n1"
            
            edge_key = f"e{edge_id}"
            cbn["edges"][edge_key] = {
                "source": source,
                "target": target_node,
                "weight": self.generate_weight(),
                "correlation": self.generate_correlation()
            }
            
            cbn["nodes"][source]["outgoing_edges"].append(edge_key)
            cbn["nodes"][target_node]["incoming_edges"].append(edge_key)
            
            edge_id += 1
            edges_created += 1
        
        # Generate remaining edges between other nodes
        max_attempts = edge_count * 3  # Avoid infinite loops
        attempts = 0
        
        while edges_created < edge_count and attempts < max_attempts:
            attempts += 1
            
            source = random.choice(node_ids)
            target = random.choice([n for n in node_ids if n != source])
            
            # Check if edge already exists
            edge_exists = any(
                e["source"] == source and e["target"] == target
                for e in cbn["edges"].values()
            )
            
            if not edge_exists:
                edge_key = f"e{edge_id}"
                cbn["edges"][edge_key] = {
                    "source": source,
                    "target": target,
                    "weight": self.generate_weight(),
                    "correlation": self.generate_correlation()
                }
                
                cbn["nodes"][source]["outgoing_edges"].append(edge_key)
                cbn["nodes"][target]["incoming_edges"].append(edge_key)
                
                edge_id += 1
                edges_created += 1
        
        return cbn
    
    def validate_cbn(self, cbn):
        """
        Validate that the CBN meets requirements
        
        Returns:
            bool: True if valid, False otherwise
        """
        # Check that there's exactly one stance node
        stance_nodes = [node for node in cbn["nodes"].values() if node.get("is_stance", False)]
        if len(stance_nodes) != 1:
            return False
            
        # Check that the stance node is n1
        if not cbn["nodes"].get("n1", {}).get("is_stance", False):
            return False
            
        # Check that all other nodes are not stance
        for node_id, node in cbn["nodes"].items():
            if node_id != "n1" and node.get("is_stance", False):
                return False
                
        return True


def generate_batch_synthetic_cbns(topic, num_cbns, output_dir):
    """
    Generate a batch of synthetic CBNs for a specific topic using topic-specific statistics
    
    Args:
        topic: Topic name (zoning, healthcare, camera, climate)
        num_cbns: Number of CBNs to generate
        output_dir: Output directory path
        
    Returns:
        str: Path to generated file
    """
    # Get topic-specific statistics with intelligent caching
    analyzer = CBNStatisticsAnalyzer()
    cbns_root = "/Users/chanceli/MIT/tyt-synth-agent/experiment/agent_data/ref_data/cbns"
    
    print(f"Loading statistics for topic: {topic}")
    statistics = analyzer.get_topic_statistics(cbns_root, topic)
    
    # Generate CBNs
    generator = SyntheticCBNGenerator(statistics)
    
    synthetic_cbns = []
    validation_failures = 0
    
    for i in range(num_cbns):
        agent_id = f"{topic}_synth_agent_{i:04d}"
        cbn = generator.generate_cbn(agent_id=agent_id, topic=topic)
        
        # Validate CBN
        if not generator.validate_cbn(cbn):
            print(f"Warning: CBN {i} failed validation")
            validation_failures += 1
            # Regenerate or fix...
            continue
        
        # Create full structure
        synth_data = {
            "sessionId": f"{topic}_synth_session_{i:04d}",
            "prolificId": agent_id,
            "status": "completed",
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "graphs": [{
                "_id": f"{topic}_graph_{i:04d}",
                "sessionId": f"{topic}_synth_session_{i:04d}",
                "prolificId": agent_id,
                "qaPairId": f"{topic}_synth_qa_{i:04d}",
                "graphData": cbn
            }]
        }
        
        synthetic_cbns.append(synth_data)
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    output_file = os.path.join(output_dir, f"{topic}_synthetic_cbns_{timestamp}.json")
    
    with open(output_file, 'w') as f:
        json.dump(synthetic_cbns, f, indent=2)
    
    print(f"Generated {len(synthetic_cbns)} synthetic CBNs for {topic}")
    print(f"Validation failures: {validation_failures}")
    print(f"Saved to: {output_file}")
    
    return output_file


def main():
    """Main function for testing"""
    # Test generation
    output_dir = "/Users/chanceli/MIT/tyt-synth-agent/experiment/agent_data/synthetic_data"
    
    topics = ['zoning', 'healthcare', 'camera', 'climate']
    
    for topic in topics:
        print(f"\nGenerating synthetic CBNs for topic: {topic}")
        generate_batch_synthetic_cbns(topic, 50, output_dir)


if __name__ == "__main__":
    main()
