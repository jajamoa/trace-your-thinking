"""
Balanced Synthetic CBN Generator
Final optimized version based on similarity analysis
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


class BalancedSyntheticCBNGenerator:
    """Balanced generator combining best of both approaches"""
    
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
        """Generate evidence count matching real distribution more closely"""
        # Based on real data: mean=1.238, most nodes have 1 evidence
        if random.random() < 0.85:  # 85% of nodes
            return random.choices([1, 2], weights=[0.7, 0.3])[0]
        else:  # 15% have more
            return random.choices([3, 4, 5, 6], weights=[0.5, 0.3, 0.15, 0.05])[0]
    
    def generate_confidence(self):
        """Generate confidence with realistic variance"""
        mean = self.stats['confidence']['mean']
        std = self.stats['confidence']['std']
        
        # Mostly normal distribution
        value = np.random.normal(mean, std)
        return max(0.1, min(1.0, value))
    
    def generate_importance(self):
        """Generate importance with realistic distribution"""
        mean = self.stats['importance']['mean']
        std = self.stats['importance']['std']
        
        value = np.random.normal(mean, std)
        return max(0.1, min(1.0, value))
    
    def generate_edge_count(self, node_count):
        """Generate edge count based on real statistics"""
        edge_mean = self.stats['edge_count']['mean']
        edge_std = self.stats['edge_count']['std']
        
        # Use normal distribution
        edge_count = int(np.random.normal(edge_mean, edge_std))
        
        # Ensure reasonable bounds
        max_edges = node_count * (node_count - 1) // 2
        edge_count = max(0, min(max_edges, edge_count))
        
        return edge_count
    
    def generate_cbn(self, agent_id=None, topic='zoning'):
        """Generate balanced synthetic CBN"""
        if agent_id is None:
            agent_id = f"synth_{uuid.uuid4().hex[:8]}"
        
        # Node count with real distribution
        node_mean = self.stats['node_count']['mean']
        node_std = self.stats['node_count']['std']
        node_count = int(np.random.normal(node_mean, node_std))
        node_count = max(2, min(200, node_count))
        
        # Edge count based on real distribution
        edge_count = self.generate_edge_count(node_count)
        
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
        stance_confidence = np.random.normal(0.8, 0.1)
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
        anchor_ratio_mean = self.stats['anchor_ratio']['mean']
        anchor_ratio_std = self.stats['anchor_ratio']['std']
        
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
            
            # Determine anchor status
            anchor_ratio = np.random.normal(anchor_ratio_mean, anchor_ratio_std * 0.3)
            is_anchor = random.random() < anchor_ratio
            
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
        
        # Generate edges more carefully
        node_ids = list(cbn["nodes"].keys())
        edges_created = 0
        edge_id = 1
        attempts = 0
        max_attempts = edge_count * 5
        
        # Ensure stance node has some connections
        stance_connections = min(random.randint(2, 4), node_count - 1, edge_count)
        
        # Connect stance node first
        for _ in range(stance_connections):
            if edges_created >= edge_count:
                break
            
            other_node = random.choice([n for n in node_ids if n != "n1"])
            
            # Randomly choose direction
            if random.random() < 0.5:
                source, target = "n1", other_node
            else:
                source, target = other_node, "n1"
            
            edge_key = f"e{edge_id}"
            cbn["edges"][edge_key] = {
                "source": source,
                "target": target,
                "weight": 0.5,  # Fixed as in real data
                "correlation": 0.5  # Fixed as in real data
            }
            
            cbn["nodes"][source]["outgoing_edges"].append(edge_key)
            cbn["nodes"][target]["incoming_edges"].append(edge_key)
            
            edge_id += 1
            edges_created += 1
        
        # Generate remaining edges
        while edges_created < edge_count and attempts < max_attempts:
            attempts += 1
            
            source = random.choice(node_ids)
            target = random.choice([n for n in node_ids if n != source])
            
            # Check if edge already exists
            edge_exists = any(
                (e["source"] == source and e["target"] == target) or
                (e["source"] == target and e["target"] == source)
                for e in cbn["edges"].values()
            )
            
            if not edge_exists:
                edge_key = f"e{edge_id}"
                cbn["edges"][edge_key] = {
                    "source": source,
                    "target": target,
                    "weight": 0.5,  # Fixed
                    "correlation": 0.5  # Fixed
                }
                
                cbn["nodes"][source]["outgoing_edges"].append(edge_key)
                cbn["nodes"][target]["incoming_edges"].append(edge_key)
                
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


if __name__ == "__main__":
    # Test
    from cbn_statistics_analyzer import CBNStatisticsAnalyzer
    analyzer = CBNStatisticsAnalyzer()
    cbns_root = "ref_data/cbns"
    statistics = analyzer.get_topic_statistics(cbns_root, 'zoning')
    
    generator = BalancedSyntheticCBNGenerator(statistics)
    cbn = generator.generate_cbn(topic='zoning')
    
    print(f"Nodes: {len(cbn['nodes'])}")
    print(f"Edges: {len(cbn['edges'])}")
    print(f"Valid: {generator.validate_cbn(cbn)}")
