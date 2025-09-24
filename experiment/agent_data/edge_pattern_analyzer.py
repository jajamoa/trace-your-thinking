"""
Edge Pattern Analyzer
Analyzes edge connection patterns and semantic relationships in CBNs
"""
import json
import os
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from itertools import combinations
import re
import random


class EdgePatternAnalyzer:
    """Analyzes edge patterns and semantic relationships"""
    
    def __init__(self):
        self.edge_patterns = defaultdict(lambda: defaultdict(int))
        self.node_type_connections = defaultdict(set)
        self.correlation_patterns = defaultdict(lambda: defaultdict(list))
        self.forbidden_connections = set()
        self.node_categories = {}
        
    def categorize_node_label(self, label):
        """Categorize node labels by semantic type"""
        label_lower = label.lower()
        
        # Define semantic categories
        categories = {
            'stance': ['support', 'opposition', 'against', 'favor', 'oppose'],
            'effect': ['effect', 'impact', 'influence', 'result', 'consequence'],
            'privacy': ['privacy', 'personal', 'data', 'information', 'confidential'],
            'safety': ['safety', 'security', 'protection', 'crime', 'prevention'],
            'trust': ['trust', 'confidence', 'reliability', 'credibility'],
            'technology': ['technology', 'surveillance', 'camera', 'monitoring', 'system'],
            'community': ['community', 'public', 'society', 'people', 'citizens'],
            'government': ['government', 'policy', 'regulation', 'law', 'enforcement'],
            'rights': ['rights', 'freedom', 'liberties', 'civil'],
            'economic': ['economic', 'cost', 'budget', 'financial', 'money'],
            'emotion': ['feeling', 'perception', 'sense', 'fear', 'comfort'],
            'accountability': ['accountability', 'transparency', 'oversight', 'control']
        }
        
        # Find matching categories
        matched_categories = []
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in label_lower:
                    matched_categories.append(category)
                    break
        
        # Default category if no match
        if not matched_categories:
            # Check for common patterns
            if any(word in label_lower for word in ['positive', 'negative', 'strong', 'weak']):
                matched_categories.append('modifier')
            else:
                matched_categories.append('general')
        
        return matched_categories
    
    def extract_edge_patterns(self, cbns, topic='camera'):
        """Extract patterns from edges in CBNs"""
        print(f"Analyzing edge patterns for {len(cbns)} CBNs...")
        
        for cbn_data in cbns:
            # Handle different data structures
            if 'graphs' in cbn_data:
                graphs = cbn_data['graphs']
            else:
                graphs = [cbn_data]
            
            for graph_wrapper in graphs:
                if 'graphData' in graph_wrapper:
                    graph = graph_wrapper['graphData']
                else:
                    graph = graph_wrapper
                
                nodes = graph.get('nodes', {})
                edges = graph.get('edges', {})
                
                # Categorize all nodes
                node_categories = {}
                for node_id, node in nodes.items():
                    label = node.get('label', '')
                    categories = self.categorize_node_label(label)
                    node_categories[node_id] = categories
                    
                    # Store node text for pattern analysis
                    self.node_categories[label] = categories
                
                # Analyze edges
                for edge_id, edge in edges.items():
                    source_id = edge.get('source')
                    target_id = edge.get('target')
                    correlation = edge.get('correlation', 0.5)
                    
                    if source_id in nodes and target_id in nodes:
                        source_label = nodes[source_id].get('label', '')
                        target_label = nodes[target_id].get('label', '')
                        source_cats = node_categories.get(source_id, ['general'])
                        target_cats = node_categories.get(target_id, ['general'])
                        
                        # Record connection patterns
                        for s_cat in source_cats:
                            for t_cat in target_cats:
                                pattern_key = f"{s_cat}->{t_cat}"
                                if pattern_key not in self.edge_patterns:
                                    self.edge_patterns[pattern_key] = {'count': 0, 'correlations': []}
                                self.edge_patterns[pattern_key]['count'] += 1
                                self.edge_patterns[pattern_key]['correlations'].append(correlation)
                                
                                # Track specific label connections
                                label_pair = (source_label.lower(), target_label.lower())
                                self.correlation_patterns[pattern_key][label_pair].append(correlation)
        
        return self.analyze_patterns()
    
    def analyze_patterns(self):
        """Analyze collected patterns"""
        analysis = {
            'category_connections': {},
            'common_patterns': [],
            'rare_patterns': [],
            'correlation_tendencies': {},
            'semantic_rules': []
        }
        
        # Analyze category connections
        total_edges = sum(data['count'] for data in self.edge_patterns.values())
        
        for pattern, data in self.edge_patterns.items():
            if 'count' not in data:
                data['count'] = 0
            if 'correlations' not in data:
                data['correlations'] = []
                
            count = data['count']
            correlations = data['correlations']
            
            # Calculate statistics
            freq = count / total_edges if total_edges > 0 else 0
            avg_corr = np.mean(correlations) if correlations else 0.5
            
            analysis['category_connections'][pattern] = {
                'count': count,
                'frequency': freq,
                'avg_correlation': avg_corr,
                'correlation_std': np.std(correlations) if correlations else 0
            }
            
            # Identify common and rare patterns
            if freq > 0.05:  # More than 5% of edges
                analysis['common_patterns'].append({
                    'pattern': pattern,
                    'frequency': freq,
                    'typical_correlation': 'positive' if avg_corr > 0.5 else 'negative'
                })
            elif count < 10 and total_edges > 1000:  # Very rare
                analysis['rare_patterns'].append(pattern)
        
        # Extract semantic rules
        analysis['semantic_rules'] = self.extract_semantic_rules()
        
        return analysis
    
    def extract_semantic_rules(self):
        """Extract semantic rules from patterns"""
        rules = []
        
        # Common semantic patterns in surveillance context
        positive_associations = [
            ('safety', 'support'),  # Safety leads to support
            ('crime', 'surveillance'),  # Crime concerns lead to surveillance support
            ('security', 'technology'),  # Security needs drive technology
            ('protection', 'camera'),  # Protection drives camera support
            ('trust', 'government'),  # Trust in government supports surveillance
        ]
        
        negative_associations = [
            ('privacy', 'surveillance'),  # Privacy concerns oppose surveillance
            ('rights', 'monitoring'),  # Rights concerns oppose monitoring
            ('freedom', 'camera'),  # Freedom concerns oppose cameras
            ('abuse', 'trust'),  # Abuse concerns reduce trust
            ('bias', 'support'),  # Bias concerns reduce support
        ]
        
        conflicting_pairs = [
            ('privacy', 'safety'),  # Classic tension
            ('freedom', 'security'),  # Classic tension
            ('individual', 'community'),  # Individual vs collective
            ('cost', 'effectiveness'),  # Economic tradeoffs
        ]
        
        rules.extend([
            {
                'type': 'positive_association',
                'categories': list(positive_associations),
                'description': 'These category pairs tend to have positive correlations'
            },
            {
                'type': 'negative_association', 
                'categories': list(negative_associations),
                'description': 'These category pairs tend to have negative correlations'
            },
            {
                'type': 'conflicting',
                'categories': list(conflicting_pairs),
                'description': 'These represent fundamental tensions/tradeoffs'
            }
        ])
        
        return rules
    
    def get_connection_probability(self, source_cats, target_cats, patterns):
        """Get probability of connection between category types"""
        probs = []
        for s_cat in source_cats:
            for t_cat in target_cats:
                pattern = f"{s_cat}->{t_cat}"
                if pattern in patterns:
                    probs.append(patterns[pattern]['frequency'])
        
        return max(probs) if probs else 0.01  # Small default probability
    
    def get_correlation_tendency(self, source_label, target_label, source_cats, target_cats):
        """Get expected correlation between nodes"""
        # Check semantic rules
        for s_cat in source_cats:
            for t_cat in target_cats:
                # Positive associations
                if (s_cat, t_cat) in [
                    ('safety', 'support'), ('crime', 'surveillance'),
                    ('security', 'technology'), ('protection', 'camera'),
                    ('trust', 'government'), ('effectiveness', 'support')
                ]:
                    return random.choice([0.7, 0.8, 0.9])  # Positive
                
                # Negative associations
                elif (s_cat, t_cat) in [
                    ('privacy', 'surveillance'), ('rights', 'monitoring'),
                    ('freedom', 'camera'), ('abuse', 'trust'),
                    ('bias', 'support'), ('cost', 'support')
                ]:
                    return random.choice([0.1, 0.2, 0.3])  # Negative
        
        # Default neutral
        return 0.5
    
    def save_analysis(self, analysis, output_file):
        """Save analysis results"""
        # Convert numpy types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v) for v in obj]
            return obj
        
        analysis = convert_types(analysis)
        
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"Edge pattern analysis saved to: {output_file}")


def analyze_topic_edge_patterns(topic='camera'):
    """Analyze edge patterns for a specific topic"""
    analyzer = EdgePatternAnalyzer()
    
    # Load CBNs
    cbns_dir = Path(__file__).parent / "ref_data" / "cbns" / topic
    all_cbns = []
    
    for json_file in cbns_dir.glob("*.json"):
        if 'statistics' not in json_file.name:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_cbns.extend(data)
                else:
                    all_cbns.append(data)
    
    print(f"Loaded {len(all_cbns)} CBN files for {topic}")
    
    # Analyze patterns
    analysis = analyzer.extract_edge_patterns(all_cbns, topic)
    
    # Save results
    output_file = cbns_dir / f"{topic}_edge_patterns.json"
    analyzer.save_analysis(analysis, output_file)
    
    # Print summary
    print("\n=== Edge Pattern Analysis Summary ===")
    print(f"Total unique patterns: {len(analysis['category_connections'])}")
    print(f"Common patterns (>5% frequency): {len(analysis['common_patterns'])}")
    print(f"Rare patterns: {len(analysis['rare_patterns'])}")
    
    print("\nTop 10 most common patterns:")
    sorted_patterns = sorted(
        analysis['category_connections'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:10]
    
    for pattern, stats in sorted_patterns:
        print(f"  {pattern}: {stats['count']} edges ({stats['frequency']:.2%}), "
              f"avg correlation: {stats['avg_correlation']:.2f}")
    
    return analyzer, analysis


if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else 'camera'
    analyze_topic_edge_patterns(topic)
