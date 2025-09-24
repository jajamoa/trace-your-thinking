"""
Optimized Synthetic CBN Generator
Improved version based on similarity analysis results
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


class OptimizedSyntheticCBNGenerator:
    """Optimized generator based on real data analysis"""
    
    def __init__(self, statistics):
        self.stats = statistics
        # Use actual top words from real data
        self.top_words = [word for word, count in statistics.get('top_words', [])[:100]]
        
        # Enhanced topic vocabularies from real data analysis
        self.topic_templates = {
            'zoning': {
                'core': ['housing', 'upzoning', 'density', 'zoning', 'affordability'],
                'effect': ['effect', 'impact', 'influence', 'result', 'consequence'],
                'prepositions': ['of', 'for', 'to', 'in', 'on'],
                'concepts': ['traffic', 'neighborhood', 'residents', 'urban', 'development'],
                'modifiers': ['increased', 'negative', 'positive', 'local', 'higher'],
                'actions': ['support', 'opposition', 'concerns', 'changes', 'policies']
            },
            'healthcare': {
                'core': ['medical', 'insurance', 'coverage', 'healthcare', 'treatment'],
                'effect': ['access', 'cost', 'quality', 'availability', 'effectiveness'],
                'prepositions': ['of', 'for', 'to', 'in', 'with'],
                'concepts': ['patient', 'doctor', 'hospital', 'medicine', 'care'],
                'modifiers': ['universal', 'private', 'public', 'affordable', 'emergency'],
                'actions': ['support', 'opposition', 'implementation', 'reform', 'coverage']
            },
            'camera': {
                'core': ['surveillance', 'cameras', 'security', 'privacy', 'monitoring'],
                'effect': ['safety', 'protection', 'prevention', 'tracking', 'control'],
                'prepositions': ['of', 'for', 'in', 'on', 'with'],
                'concepts': ['public', 'spaces', 'crime', 'technology', 'data'],
                'modifiers': ['civil', 'facial', 'digital', 'public', 'private'],
                'actions': ['recording', 'observation', 'collection', 'recognition', 'enforcement']
            }
        }
        
    def generate_node_label(self, topic='zoning', is_stance=False):
        """Generate more realistic node labels based on real data patterns"""
        vocab = self.topic_templates.get(topic, self.topic_templates['zoning'])
        
        if is_stance:
            # Stance nodes - use patterns from real data
            stance_word = random.choice(vocab['core'])
            if topic == 'zoning':
                patterns = [
                    f"Support for {stance_word}",
                    f"Opposition to {stance_word}",
                    f"{stance_word.capitalize()} support",
                    f"Against {stance_word}"
                ]
            else:
                patterns = [
                    f"Support for {stance_word}",
                    f"Opposition to {stance_word}",
                    f"{random.choice(vocab['modifiers']).capitalize()} {stance_word}",
                    f"{stance_word.capitalize()} {random.choice(vocab['actions'])}"
                ]
            return random.choice(patterns)
        
        # Regular nodes - use real data patterns
        pattern_weights = [0.2, 0.25, 0.15, 0.2, 0.1, 0.1]  # Weighted selection
        pattern_choice = random.choices(range(6), weights=pattern_weights)[0]
        
        if pattern_choice == 0:
            # Single concept (20%)
            return random.choice(vocab['core'] + vocab['concepts']).capitalize()
        elif pattern_choice == 1:
            # Concept + effect (25%)
            return f"{random.choice(vocab['concepts']).capitalize()} {random.choice(vocab['effect'])}"
        elif pattern_choice == 2:
            # Effect of concept (15%)
            return f"{random.choice(vocab['effect']).capitalize()} {random.choice(vocab['prepositions'])} {random.choice(vocab['core'])}"
        elif pattern_choice == 3:
            # Modified concept (20%)
            return f"{random.choice(vocab['modifiers']).capitalize()} {random.choice(vocab['concepts'])}"
        elif pattern_choice == 4:
            # Two concepts connected (10%)
            c1, c2 = random.sample(vocab['concepts'], 2)
            return f"{c1.capitalize()} and {c2}"
        else:
            # Action-based (10%)
            return f"{random.choice(vocab['actions']).capitalize()} {random.choice(vocab['prepositions'])} {random.choice(vocab['core'])}"
    
    def generate_evidence_count(self):
        """Generate evidence count with more realistic distribution"""
        # Use mixture model to capture bimodal distribution
        if random.random() < 0.7:
            # Most nodes have 1-2 evidence
            return random.choices([1, 2], weights=[0.6, 0.4])[0]
        else:
            # Some nodes have more evidence (long tail)
            return int(np.random.exponential(2.5) + 2)
    
    def generate_confidence(self):
        """Generate confidence with more realistic variance"""
        mean = self.stats['confidence']['mean']
        std = self.stats['confidence']['std']
        
        # Add occasional outliers
        if random.random() < 0.1:
            # 10% chance of outlier
            value = random.choice([
                np.random.uniform(0.1, 0.4),  # Low confidence
                np.random.uniform(0.9, 1.0)   # High confidence
            ])
        else:
            value = np.random.normal(mean, std * 1.2)  # Slightly increase variance
        
        return max(0.1, min(1.0, value))
    
    def generate_importance(self):
        """Generate importance with more realistic distribution"""
        mean = self.stats['importance']['mean']
        std = self.stats['importance']['std']
        
        # Importance tends to cluster around certain values
        if random.random() < 0.3:
            # 30% cluster around 0.7-0.8
            value = np.random.normal(0.75, 0.05)
        else:
            value = np.random.normal(mean, std * 1.1)
        
        return max(0.1, min(1.0, value))
    
    def generate_node_degree_distribution(self, num_nodes):
        """Generate more realistic degree distribution"""
        # Real networks often follow power-law or scale-free distribution
        degrees = []
        
        # Ensure stance node has reasonable connectivity
        stance_degree = random.choices(
            [2, 3, 4, 5, 6],
            weights=[0.2, 0.3, 0.25, 0.15, 0.1]
        )[0]
        degrees.append(stance_degree)
        
        # Other nodes - use exponential distribution with occasional hubs
        for i in range(1, num_nodes):
            if random.random() < 0.1:  # 10% chance of hub
                degree = random.randint(4, 8)
            else:
                degree = int(np.random.exponential(1.5) + 1)
            degrees.append(min(degree, num_nodes - 1))
        
        return degrees
    
    def generate_cbn(self, agent_id=None, topic='zoning'):
        """Generate optimized synthetic CBN"""
        if agent_id is None:
            agent_id = f"synth_{uuid.uuid4().hex[:8]}"
        
        # Node count with higher variance
        node_mean = self.stats['node_count']['mean']
        node_std = self.stats['node_count']['std']
        
        # Use mixture model for node count
        if random.random() < 0.8:
            # Normal distribution (80%)
            node_count = int(np.random.normal(node_mean, node_std))
        else:
            # Occasional very large or small graphs (20%)
            if random.random() < 0.5:
                node_count = random.randint(5, 20)  # Small
            else:
                node_count = random.randint(80, 150)  # Large
        
        node_count = max(2, min(200, node_count))
        
        # Generate degree distribution first
        degree_dist = self.generate_node_degree_distribution(node_count)
        total_degree = sum(degree_dist)
        edge_count = total_degree // 2  # Each edge contributes to 2 degrees
        
        # Create CBN structure
        cbn = {
            "agent_id": agent_id,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "nodes": {},
            "edges": {},
            "qa_history": {},
            "stance_node_id": "n1",
            "step": "completed",
            "anchor_queue": [],
            "node_counter": node_count,
            "edge_counter": edge_count,
            "qa_counter": random.randint(8, 15)
        }
        
        # Generate stance node
        stance_confidence = np.random.normal(0.85, 0.1)
        stance_confidence = max(0.6, min(1.0, stance_confidence))
        
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
            "is_stance": True
        }
        cbn["anchor_queue"].append("n1")
        
        # Generate other nodes
        anchor_ratio = self.stats['anchor_ratio']['mean']
        anchor_std = self.stats['anchor_ratio']['std']
        
        for i in range(2, node_count + 1):
            node_id = f"n{i}"
            
            # Generate evidence with realistic distribution
            evidence_count = self.generate_evidence_count()
            evidence = []
            
            for j in range(evidence_count):
                evidence.append({
                    "qa_id": f"qa{random.randint(1, 15)}",
                    "confidence": self.generate_confidence(),
                    "importance": self.generate_importance()
                })
            
            # Calculate aggregate confidence
            if evidence:
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
            
            # Vary anchor ratio
            is_anchor = random.random() < np.random.normal(anchor_ratio, anchor_std * 0.5)
            
            node = {
                "label": self.generate_node_label(topic, is_stance=False),
                "aggregate_confidence": aggregate_confidence,
                "evidence": evidence,
                "importance": importance,
                "incoming_edges": [],
                "outgoing_edges": [],
                "status": "anchor" if is_anchor else "candidate",
                "frequency": 1,
                "is_stance": False
            }
            
            cbn["nodes"][node_id] = node
            
            if is_anchor:
                cbn["anchor_queue"].append(node_id)
        
        # Generate edges based on degree distribution
        node_ids = list(cbn["nodes"].keys())
        current_degrees = {nid: 0 for nid in node_ids}
        target_degrees = {f"n{i+1}": degree_dist[i] for i in range(node_count)}
        
        edges_created = 0
        edge_id = 1
        attempts = 0
        max_attempts = edge_count * 10
        
        while edges_created < edge_count and attempts < max_attempts:
            attempts += 1
            
            # Select nodes that need more connections
            available_sources = [nid for nid in node_ids 
                               if current_degrees[nid] < target_degrees[nid]]
            available_targets = [nid for nid in node_ids 
                               if current_degrees[nid] < target_degrees[nid]]
            
            if not available_sources or not available_targets:
                break
            
            source = random.choice(available_sources)
            valid_targets = [t for t in available_targets if t != source]
            if not valid_targets:
                continue
            target = random.choice(valid_targets)
            
            # Check if edge already exists
            edge_exists = any(
                (e["source"] == source and e["target"] == target) or
                (e["source"] == target and e["target"] == source)
                for e in cbn["edges"].values()
            )
            
            if not edge_exists:
                edge_key = f"e{edge_id}"
                
                # More varied correlations
                if random.random() < 0.7:
                    correlation = 0.5  # Neutral (most common)
                else:
                    correlation = random.choice([0.3, 0.7])  # Negative or positive
                
                cbn["edges"][edge_key] = {
                    "source": source,
                    "target": target,
                    "weight": 0.5,  # Fixed as in real data
                    "correlation": correlation
                }
                
                cbn["nodes"][source]["outgoing_edges"].append(edge_key)
                cbn["nodes"][target]["incoming_edges"].append(edge_key)
                
                current_degrees[source] += 1
                current_degrees[target] += 1
                
                edge_id += 1
                edges_created += 1
        
        return cbn
    
    def validate_cbn(self, cbn):
        """Validate CBN structure"""
        # Check exactly one stance node
        stance_nodes = [node for node in cbn["nodes"].values() if node.get("is_stance", False)]
        if len(stance_nodes) != 1:
            return False
        
        # Check stance node is n1
        if not cbn["nodes"].get("n1", {}).get("is_stance", False):
            return False
        
        # Check all other nodes are not stance
        for node_id, node in cbn["nodes"].items():
            if node_id != "n1" and node.get("is_stance", False):
                return False
        
        return True


def generate_optimized_batch_cbns(topic, num_cbns, output_dir):
    """Generate optimized synthetic CBNs"""
    # Load statistics
    analyzer = CBNStatisticsAnalyzer()
    cbns_root = Path(__file__).parent / "ref_data" / "cbns"
    
    print(f"Loading statistics for topic: {topic}")
    statistics = analyzer.get_topic_statistics(str(cbns_root), topic)
    
    # Use optimized generator
    generator = OptimizedSyntheticCBNGenerator(statistics)
    
    synthetic_cbns = []
    validation_failures = 0
    
    for i in range(num_cbns):
        agent_id = f"{topic}_opt_agent_{i:04d}"
        cbn = generator.generate_cbn(agent_id=agent_id, topic=topic)
        
        if not generator.validate_cbn(cbn):
            print(f"Warning: CBN {i} failed validation")
            validation_failures += 1
            continue
        
        # Create full structure
        synth_data = {
            "sessionId": f"{topic}_opt_session_{i:04d}",
            "prolificId": agent_id,
            "status": "completed",
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "graphs": [{
                "_id": f"{topic}_graph_{i:04d}",
                "sessionId": f"{topic}_opt_session_{i:04d}",
                "prolificId": agent_id,
                "qaPairId": f"{topic}_opt_qa_{i:04d}",
                "graphData": cbn
            }]
        }
        
        synthetic_cbns.append(synth_data)
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    output_file = os.path.join(output_dir, f"{topic}_optimized_cbns_{timestamp}.json")
    
    with open(output_file, 'w') as f:
        json.dump(synthetic_cbns, f, indent=2)
    
    print(f"Generated {len(synthetic_cbns)} optimized CBNs for {topic}")
    print(f"Validation failures: {validation_failures}")
    print(f"Saved to: {output_file}")
    
    return output_file


if __name__ == "__main__":
    # Test optimized generation
    output_dir = "optimized_synthetic_data"
    generate_optimized_batch_cbns('zoning', 50, output_dir)
