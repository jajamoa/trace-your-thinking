"""
Edge-Aware Synthetic CBN Generator
Uses learned edge patterns for more realistic generation
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


class EdgeAwareSyntheticCBNGenerator:
    """Generator that uses edge pattern statistics"""
    
    def __init__(self, statistics, edge_patterns=None):
        self.stats = statistics
        self.edge_patterns = edge_patterns
        self.top_words = [word for word, count in statistics.get('top_words', [])[:100]]
        
        # Load edge patterns if not provided
        if edge_patterns is None:
            self.load_edge_patterns()
        
        # Topic-specific vocabularies with real data emphasis
        self.topic_templates = {
            'camera': {
                'core': ['surveillance', 'cameras', 'camera', 'monitoring', 'security'],
                'effect': ['effect', 'impact', 'influence', 'positive', 'negative'],
                'privacy': ['privacy', 'personal', 'data', 'invasion', 'liberties'],
                'safety': ['safety', 'crime', 'prevention', 'protection', 'deterrence'],
                'trust': ['trust', 'reliability', 'confidence', 'government', 'misuse'],
                'community': ['public', 'community', 'social', 'spaces', 'people'],
                'technology': ['technology', 'systems', 'infrastructure', 'accuracy', 'technologies'],
                'government': ['government', 'law', 'enforcement', 'police', 'regulation'],
                'rights': ['rights', 'freedom', 'liberties', 'civil', 'individual'],
                'economic': ['economic', 'cost', 'costs', 'infrastructure'],
                'accountability': ['accountability', 'transparency', 'oversight', 'control'],
                'prepositions': ['of', 'in', 'for', 'on', 'to'],
                'modifiers': ['strong', 'positive', 'negative', 'increased', 'reduced']
            },
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
            }
        }
        
        # Extract pattern probabilities
        self.pattern_probabilities = self._extract_pattern_probabilities()
        
    def load_edge_patterns(self, topic='camera'):
        """Load pre-computed edge patterns"""
        pattern_file = Path(__file__).parent / "ref_data" / "cbns" / topic / f"{topic}_edge_patterns.json"
        if pattern_file.exists():
            with open(pattern_file, 'r') as f:
                self.edge_patterns = json.load(f)
            print(f"Loaded edge patterns for {topic}")
    
    def _extract_pattern_probabilities(self):
        """Extract pattern probabilities from edge patterns"""
        if not self.edge_patterns:
            return {}
        
        connections = self.edge_patterns.get('category_connections', {})
        
        # Normalize to probabilities
        probs = {}
        for pattern, stats in connections.items():
            probs[pattern] = stats['frequency']
        
        return probs
    
    def categorize_node_label(self, label):
        """Categorize a node label"""
        label_lower = label.lower()
        
        # Categories based on real data patterns
        categories = {
            'stance': ['support', 'opposition', 'against', 'favor', 'oppose'],
            'effect': ['effect', 'impact', 'influence', 'result', 'consequence'],
            'privacy': ['privacy', 'personal', 'data', 'information', 'invasion'],
            'safety': ['safety', 'security', 'protection', 'crime', 'prevention'],
            'trust': ['trust', 'confidence', 'reliability', 'credibility', 'misuse'],
            'technology': ['technology', 'surveillance', 'camera', 'monitoring', 'system'],
            'community': ['community', 'public', 'social', 'people', 'spaces'],
            'government': ['government', 'policy', 'regulation', 'law', 'enforcement'],
            'rights': ['rights', 'freedom', 'liberties', 'civil'],
            'economic': ['economic', 'cost', 'budget', 'financial'],
            'accountability': ['accountability', 'transparency', 'oversight', 'control']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in label_lower:
                    return category
        
        if any(word in label_lower for word in ['positive', 'negative', 'strong', 'weak']):
            return 'modifier'
        
        return 'general'
    
    def generate_node_label(self, topic='camera', is_stance=False, target_category=None):
        """Generate node label, optionally for a specific category"""
        vocab = self.topic_templates.get(topic, self.topic_templates['camera'])
        
        if is_stance:
            # Stance nodes
            stance_word = random.choice(vocab.get('core', ['surveillance']))
            patterns = [
                f"Support for {stance_word}",
                f"Opposition to {stance_word}",
                f"Against {stance_word}",
                f"{stance_word.capitalize()} support"
            ]
            return random.choice(patterns)
        
        # If target category specified, generate for that category
        if target_category and target_category != 'general':
            if target_category == 'technology':
                base_words = vocab.get('technology', vocab.get('core', ['technology']))
            elif target_category == 'safety':
                base_words = vocab.get('safety', ['safety', 'security', 'crime'])
            elif target_category == 'privacy':
                base_words = vocab.get('privacy', ['privacy', 'data'])
            elif target_category == 'effect':
                return f"{random.choice(vocab.get('effect', ['effect']))} {random.choice(vocab.get('prepositions', ['of']))} {random.choice(vocab.get('core', ['surveillance']))}"
            elif target_category == 'trust':
                base_words = ['trust', 'reliability', 'confidence', 'credibility']
            elif target_category == 'community':
                base_words = vocab.get('community', ['public', 'community'])
            else:
                base_words = vocab.get('core', ['surveillance'])
            
            # Generate appropriate label
            if random.random() < 0.3:
                # Simple label
                return random.choice(base_words).capitalize()
            else:
                # Compound label
                modifier = random.choice(vocab.get('modifiers', ['']))
                effect = random.choice(vocab.get('effect', ['']))
                if random.random() < 0.5:
                    return f"{modifier} {random.choice(base_words)}".strip().capitalize()
                else:
                    return f"{random.choice(base_words).capitalize()} {effect}"
        
        # General label generation (existing logic)
        pattern_weights = [0.2, 0.25, 0.15, 0.2, 0.1, 0.1]
        pattern_choice = random.choices(range(6), weights=pattern_weights)[0]
        
        if pattern_choice == 0:
            return random.choice(vocab.get('core', ['surveillance']) + vocab.get('concepts', [])).capitalize()
        elif pattern_choice == 1:
            concepts = vocab.get('concepts', vocab.get('technology', ['surveillance']))
            effects = vocab.get('effect', ['effect'])
            return f"{random.choice(concepts).capitalize()} {random.choice(effects)}"
        elif pattern_choice == 2:
            effects = vocab.get('effect', ['effect'])
            preps = vocab.get('prepositions', ['of'])
            cores = vocab.get('core', ['surveillance'])
            return f"{random.choice(effects).capitalize()} {random.choice(preps)} {random.choice(cores)}"
        elif pattern_choice == 3:
            mods = vocab.get('modifiers', ['positive'])
            concepts = vocab.get('concepts', vocab.get('technology', ['surveillance']))
            return f"{random.choice(mods).capitalize()} {random.choice(concepts)}"
        elif pattern_choice == 4:
            concepts = vocab.get('concepts', vocab.get('core', ['surveillance']))
            if len(concepts) >= 2:
                c1, c2 = random.sample(concepts, 2)
                return f"{c1.capitalize()} and {c2}"
            else:
                return random.choice(concepts).capitalize()
        else:
            actions = vocab.get('actions', ['support'])
            preps = vocab.get('prepositions', ['for'])
            cores = vocab.get('core', ['surveillance'])
            return f"{random.choice(actions).capitalize()} {random.choice(preps)} {random.choice(cores)}"
    
    def generate_evidence_count(self):
        """Generate evidence count matching real distribution"""
        # Based on real data: mean=1.29 for camera
        if random.random() < 0.8:  # 80% of nodes
            return 1
        elif random.random() < 0.85:  # 15% have 2
            return 2
        else:  # 5% have more
            return random.choice([3, 4])
    
    def generate_confidence(self):
        """Generate confidence with realistic variance"""
        mean = self.stats['confidence']['mean']
        std = self.stats['confidence']['std']
        value = np.random.normal(mean, std)
        return max(0.1, min(1.0, value))
    
    def generate_importance(self):
        """Generate importance with realistic distribution"""
        mean = self.stats['importance']['mean']
        std = self.stats['importance']['std']
        value = np.random.normal(mean, std)
        return max(0.1, min(1.0, value))
    
    def should_connect_nodes(self, source_cat, target_cat):
        """Determine if two nodes should be connected based on patterns"""
        pattern = f"{source_cat}->{target_cat}"
        
        # Get probability from real data
        prob = self.pattern_probabilities.get(pattern, 0.001)  # Small default
        
        # Boost common patterns
        if pattern in ['technology->safety', 'safety->stance', 'technology->privacy', 
                      'privacy->stance', 'technology->trust', 'technology->stance']:
            prob = min(prob * 2, 0.2)  # Boost but cap at 20%
        
        return random.random() < prob
    
    def generate_edges_with_patterns(self, nodes, edge_count):
        """Generate edges following real pattern distribution"""
        edges = {}
        edge_id = 1
        node_ids = list(nodes.keys())
        
        # Categorize all nodes
        node_categories = {}
        for nid, node in nodes.items():
            label = node.get('label', '')
            node_categories[nid] = self.categorize_node_label(label)
        
        # Ensure stance node has connections (important pattern)
        stance_id = 'n1'
        stance_connections = min(random.randint(3, 5), len(node_ids) - 1)
        
        # Connect stance node based on common patterns
        for _ in range(stance_connections):
            # Choose target based on real patterns
            target_patterns = [
                ('technology', 0.3),
                ('safety', 0.25),
                ('privacy', 0.2),
                ('general', 0.15),
                ('effect', 0.1)
            ]
            
            # Find nodes matching preferred patterns
            target_cat = random.choices(
                [p[0] for p in target_patterns],
                weights=[p[1] for p in target_patterns]
            )[0]
            
            candidates = [nid for nid in node_ids 
                         if nid != stance_id and node_categories[nid] == target_cat]
            
            if not candidates:
                candidates = [nid for nid in node_ids if nid != stance_id]
            
            if candidates:
                target = random.choice(candidates)
                
                # Determine direction based on patterns
                if node_categories[target] in ['safety', 'technology']:
                    # These often lead TO stance
                    source, dest = target, stance_id
                else:
                    # Others often come FROM stance
                    source, dest = stance_id, target
                
                edge_key = f"e{edge_id}"
                edges[edge_key] = {
                    "source": source,
                    "target": dest,
                    "weight": 0.5,
                    "correlation": 0.5  # Keep fixed as in real data
                }
                
                nodes[source]["outgoing_edges"].append(edge_key)
                nodes[dest]["incoming_edges"].append(edge_key)
                edge_id += 1
        
        # Generate remaining edges based on patterns
        attempts = 0
        max_attempts = edge_count * 10
        
        while len(edges) < edge_count and attempts < max_attempts:
            attempts += 1
            
            # Select source and target based on pattern probabilities
            source = random.choice(node_ids)
            target = random.choice([n for n in node_ids if n != source])
            
            # Check if this edge type should exist
            source_cat = node_categories[source]
            target_cat = node_categories[target]
            
            if not self.should_connect_nodes(source_cat, target_cat):
                continue
            
            # Check if edge already exists
            edge_exists = any(
                (e["source"] == source and e["target"] == target) or
                (e["source"] == target and e["target"] == source)
                for e in edges.values()
            )
            
            if not edge_exists:
                edge_key = f"e{edge_id}"
                edges[edge_key] = {
                    "source": source,
                    "target": target,
                    "weight": 0.5,
                    "correlation": 0.5
                }
                
                nodes[source]["outgoing_edges"].append(edge_key)
                nodes[target]["incoming_edges"].append(edge_key)
                edge_id += 1
        
        return edges
    
    def generate_cbn(self, agent_id=None, topic='camera'):
        """Generate edge-aware synthetic CBN"""
        if agent_id is None:
            agent_id = f"synth_{uuid.uuid4().hex[:8]}"
        
        # Node count
        node_mean = self.stats['node_count']['mean']
        node_std = self.stats['node_count']['std']
        node_count = int(np.random.normal(node_mean, node_std))
        node_count = max(5, min(150, node_count))
        
        # Edge count
        edge_mean = self.stats['edge_count']['mean']
        edge_std = self.stats['edge_count']['std']
        edge_count = int(np.random.normal(edge_mean, edge_std))
        edge_count = max(0, min(node_count * 2, edge_count))
        
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
        
        # Generate nodes with category diversity based on real patterns
        category_distribution = {
            'technology': 0.25,
            'safety': 0.15,
            'privacy': 0.10,
            'general': 0.20,
            'effect': 0.08,
            'trust': 0.05,
            'community': 0.05,
            'government': 0.04,
            'rights': 0.04,
            'economic': 0.02,
            'accountability': 0.02
        }
        
        anchor_ratio_mean = self.stats['anchor_ratio']['mean']
        
        for i in range(2, node_count + 1):
            node_id = f"n{i}"
            
            # Choose category based on distribution
            category = random.choices(
                list(category_distribution.keys()),
                weights=list(category_distribution.values())
            )[0]
            
            # Generate label for category
            label = self.generate_node_label(topic, is_stance=False, target_category=category)
            
            # Generate evidence
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
            
            # Anchor status
            is_anchor = random.random() < anchor_ratio_mean
            
            node = {
                "label": label,
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
        
        # Generate edges using patterns
        cbn["edges"] = self.generate_edges_with_patterns(cbn["nodes"], edge_count)
        
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
        
        return True


if __name__ == "__main__":
    # Test
    from cbn_statistics_analyzer import CBNStatisticsAnalyzer
    analyzer = CBNStatisticsAnalyzer()
    cbns_root = "ref_data/cbns"
    statistics = analyzer.get_topic_statistics(cbns_root, 'camera')
    
    generator = EdgeAwareSyntheticCBNGenerator(statistics)
    cbn = generator.generate_cbn(topic='camera')
    
    print(f"Nodes: {len(cbn['nodes'])}")
    print(f"Edges: {len(cbn['edges'])}")
    print(f"Valid: {generator.validate_cbn(cbn)}")
    
    # Print node categories
    print("\nNode categories:")
    cat_counts = {}
    for node in cbn['nodes'].values():
        cat = generator.categorize_node_label(node['label'])
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")
