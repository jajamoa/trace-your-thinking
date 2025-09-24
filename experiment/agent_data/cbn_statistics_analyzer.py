"""
CBN Statistics Analyzer
Analyzes existing CBN data to extract statistical patterns for synthetic data generation
Supports topic-specific statistics with intelligent caching
"""
import json
import numpy as np
from collections import defaultdict, Counter
import os
import hashlib
from pathlib import Path
from datetime import datetime


class CBNStatisticsAnalyzer:
    """Analyzes existing CBN data to extract statistical information"""
    
    def __init__(self):
        self.node_count_dist = []
        self.edge_count_dist = []
        self.confidence_dist = []
        self.importance_dist = []
        self.weight_dist = []
        self.correlation_dist = []
        self.node_labels = []
        self.label_words = Counter()
        self.evidence_count_dist = []
        self.stance_node_patterns = []
        self.anchor_ratio_dist = []
        
    def get_topic_statistics(self, cbns_root_path, topic, force_regenerate=False):
        """
        Get statistics for a specific topic with intelligent caching
        
        Args:
            cbns_root_path: Path to the cbns root directory
            topic: Topic name (e.g., 'zoning', 'healthcare', 'camera')
            force_regenerate: Force regeneration even if cache exists
            
        Returns:
            dict: Statistics for the topic
        """
        topic_path = Path(cbns_root_path) / topic
        stats_file = topic_path / f"{topic}_statistics.json"
        
        # Check if we need to regenerate statistics
        should_regenerate = force_regenerate or self._should_regenerate_stats(topic_path, stats_file)
        
        if not should_regenerate and stats_file.exists():
            print(f"Using cached statistics for {topic}: {stats_file}")
            with open(stats_file, 'r') as f:
                return json.load(f)
        
        # Generate new statistics
        print(f"Generating statistics for topic: {topic}")
        self._reset_statistics()
        
        if not topic_path.exists():
            print(f"Warning: No data directory for topic '{topic}' at {topic_path}")
            return self._get_default_statistics(topic)
        
        # Find JSON files in topic directory (exclude statistics files)
        all_json_files = list(topic_path.glob("*.json"))
        json_files = [f for f in all_json_files if not f.name.endswith('_statistics.json')]
        
        if not json_files:
            print(f"Warning: No CBN data files found for topic '{topic}' in {topic_path}")
            return self._get_default_statistics(topic)
        
        print(f"Analyzing {len(json_files)} files for topic '{topic}':")
        for json_file in json_files:
            print(f"  - {json_file.name}")
            self.analyze_file(str(json_file))
        
        # Generate statistics
        stats = self.get_statistics()
        stats['topic'] = topic
        stats['source_files'] = [f.name for f in json_files]
        stats['file_hashes'] = {f.name: self._get_file_hash(f) for f in json_files}
        stats['generated_at'] = datetime.now().isoformat()
        
        # Save statistics
        self.save_topic_statistics(stats, stats_file)
        
        return stats
    
    def _should_regenerate_stats(self, topic_path, stats_file):
        """Check if statistics should be regenerated"""
        if not stats_file.exists():
            return True
        
        try:
            with open(stats_file, 'r') as f:
                existing_stats = json.load(f)
        except:
            return True
        
        # Check if file list changed (exclude statistics files)
        all_current_files = list(topic_path.glob("*.json"))
        current_files = [f for f in all_current_files if not f.name.endswith('_statistics.json')]
        existing_files = existing_stats.get('source_files', [])
        current_file_names = {f.name for f in current_files}
        existing_file_names = set(existing_files)
        
        if current_file_names != existing_file_names:
            print(f"File list changed for {topic_path.name}. Regenerating statistics.")
            return True
        
        # Check if any file content changed
        existing_hashes = existing_stats.get('file_hashes', {})
        for file_path in current_files:
            current_hash = self._get_file_hash(file_path)
            if existing_hashes.get(file_path.name) != current_hash:
                print(f"File {file_path.name} changed. Regenerating statistics.")
                return True
        
        return False
    
    def _get_file_hash(self, file_path):
        """Get SHA256 hash of a file for change detection"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return None
    
    def _reset_statistics(self):
        """Reset all statistics collections"""
        self.node_count_dist = []
        self.edge_count_dist = []
        self.confidence_dist = []
        self.importance_dist = []
        self.weight_dist = []
        self.correlation_dist = []
        self.node_labels = []
        self.label_words = Counter()
        self.evidence_count_dist = []
        self.stance_node_patterns = []
        self.anchor_ratio_dist = []
    
    def _get_default_statistics(self, topic):
        """Get default statistics when no data is available"""
        print(f"Using default statistics for topic '{topic}' (no source data available)")
        return {
            'topic': topic,
            'source_files': [],
            'file_hashes': {},
            'generated_at': datetime.now().isoformat(),
            'data_source': 'default_fallback',
            'node_count': {'mean': 15, 'std': 5, 'min': 8, 'max': 25},
            'edge_count': {'mean': 10, 'std': 3, 'min': 5, 'max': 15},
            'confidence': {'mean': 0.7, 'std': 0.15, 'min': 0.3, 'max': 1.0},
            'importance': {'mean': 0.7, 'std': 0.15, 'min': 0.3, 'max': 1.0},
            'weight': {'mean': 0.6, 'std': 0.2, 'min': 0.2, 'max': 1.0},
            'correlation': {'mean': 0.5, 'std': 0.3, 'min': -1.0, 'max': 1.0},
            'evidence_count': {'mean': 2, 'std': 1, 'min': 1, 'max': 5},
            'anchor_ratio': {'mean': 0.3, 'std': 0.1, 'min': 0.2, 'max': 0.5},
            'stance_node_count': {'mean': 1, 'std': 0, 'min': 1, 'max': 1},
            'total_graphs_analyzed': 0,
            'top_words': [],
            'unique_labels': 0
        }

    def analyze_all_cbns_data(self, cbns_root_path):
        """
        Analyze all JSON files in all subdirectories under cbns/
        
        Args:
            cbns_root_path: Path to the cbns root directory
        """
        cbns_path = Path(cbns_root_path)
        if not cbns_path.exists():
            print(f"Warning: CBNs path {cbns_path} does not exist")
            return
            
        print(f"Scanning CBNs data from: {cbns_path}")
        
        # Find all JSON files recursively
        json_files = list(cbns_path.rglob("*.json"))
        
        if not json_files:
            print(f"No JSON files found in {cbns_path}")
            return
            
        print(f"Found {len(json_files)} JSON files:")
        for json_file in json_files:
            relative_path = json_file.relative_to(cbns_path)
            print(f"  - {relative_path}")
            self.analyze_file(str(json_file))
            
    def analyze_file(self, file_path):
        """Analyze a single JSON file"""
        print(f"Analyzing file: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return
            
        # Analyze each session's graphs
        graphs_analyzed = 0
        for session in data:
            if 'graphs' not in session:
                continue
                
            for graph_item in session['graphs']:
                if 'graphData' in graph_item:
                    graph = graph_item['graphData']
                elif 'graph' in graph_item:
                    graph = graph_item['graph']
                else:
                    continue
                    
                self._analyze_graph(graph)
                graphs_analyzed += 1
                
        print(f"  Analyzed {graphs_analyzed} graphs from {file_path}")
                
    def _analyze_graph(self, graph):
        """Analyze a single graph"""
        if 'nodes' not in graph:
            return
            
        nodes = graph.get('nodes', {})
        edges = graph.get('edges', {})
        
        # Node count
        self.node_count_dist.append(len(nodes))
        
        # Edge count
        self.edge_count_dist.append(len(edges))
        
        # Analyze stance nodes
        stance_nodes = [node for node in nodes.values() if node.get('is_stance', False)]
        self.stance_node_patterns.append(len(stance_nodes))
        
        # Anchor ratio
        anchor_nodes = [node for node in nodes.values() if node.get('status') == 'anchor']
        if nodes:
            anchor_ratio = len(anchor_nodes) / len(nodes)
            self.anchor_ratio_dist.append(anchor_ratio)
        
        # Analyze nodes
        for node_id, node in nodes.items():
            # Labels
            label = node.get('label', '')
            if label:
                self.node_labels.append(label)
                # Extract words
                words = label.lower().split()
                for word in words:
                    # Clean word
                    word = ''.join(c for c in word if c.isalnum())
                    if word:
                        self.label_words[word] += 1
                    
            # Confidence and importance
            self.confidence_dist.append(node.get('aggregate_confidence', 0.5))
            self.importance_dist.append(node.get('importance', 0.5))
            
            # Evidence count
            evidence_count = len(node.get('evidence', []))
            self.evidence_count_dist.append(evidence_count)
            
        # Analyze edges
        for edge_id, edge in edges.items():
            self.weight_dist.append(edge.get('weight', 0.5))
            self.correlation_dist.append(edge.get('correlation', 0.5))
            
    def get_statistics(self):
        """Get comprehensive statistics"""
        def safe_stats(data, default_mean=0.5, default_std=0.1):
            """Calculate statistics with fallback defaults"""
            if not data:
                return {
                    'mean': default_mean,
                    'std': default_std,
                    'min': default_mean - default_std,
                    'max': default_mean + default_std
                }
            return {
                'mean': float(np.mean(data)),
                'std': float(np.std(data)),
                'min': float(min(data)),
                'max': float(max(data))
            }
        
        return {
            'node_count': safe_stats(self.node_count_dist, 10, 3),
            'edge_count': safe_stats(self.edge_count_dist, 8, 3),
            'confidence': safe_stats(self.confidence_dist, 0.7, 0.15),
            'importance': safe_stats(self.importance_dist, 0.7, 0.15),
            'weight': safe_stats(self.weight_dist, 0.6, 0.2),
            'correlation': safe_stats(self.correlation_dist, 0.5, 0.3),
            'evidence_count': safe_stats(self.evidence_count_dist, 2, 1),
            'anchor_ratio': safe_stats(self.anchor_ratio_dist, 0.3, 0.1),
            'stance_node_count': safe_stats(self.stance_node_patterns, 1, 0),
            'total_graphs_analyzed': len(self.node_count_dist),
            'top_words': self.label_words.most_common(100) if self.label_words else [],
            'unique_labels': len(set(self.node_labels))
        }
        
    def save_statistics(self, output_path):
        """Save statistics to JSON file"""
        stats = self.get_statistics()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"Statistics saved to: {output_path}")
        return stats
    
    def save_topic_statistics(self, stats, output_path):
        """Save topic-specific statistics"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"Topic statistics saved to: {output_path}")
    
    def generate_all_topic_statistics(self, cbns_root_path, force_regenerate=False):
        """Generate statistics for all available topics"""
        cbns_path = Path(cbns_root_path)
        
        if not cbns_path.exists():
            print(f"CBNs path does not exist: {cbns_path}")
            return {}
        
        # Find all topic directories
        topic_dirs = [d for d in cbns_path.iterdir() if d.is_dir()]
        
        results = {}
        for topic_dir in topic_dirs:
            topic = topic_dir.name
            print(f"\n{'='*50}")
            print(f"Processing topic: {topic}")
            print(f"{'='*50}")
            
            stats = self.get_topic_statistics(cbns_root_path, topic, force_regenerate)
            results[topic] = stats
        
        return results


def main():
    """Main function for testing topic-specific statistics"""
    analyzer = CBNStatisticsAnalyzer()
    
    cbns_root = "/Users/chanceli/MIT/tyt-synth-agent/experiment/agent_data/ref_data/cbns"
    
    # Generate statistics for all topics
    print("Generating topic-specific statistics...")
    all_stats = analyzer.generate_all_topic_statistics(cbns_root)
    
    # Print summary for each topic
    print("\n" + "="*80)
    print("TOPIC-SPECIFIC STATISTICS SUMMARY")
    print("="*80)
    
    for topic, stats in all_stats.items():
        print(f"\n{topic.upper()} TOPIC:")
        print("-" * 40)
        if stats.get('data_source') == 'default_fallback':
            print("  ⚠️  Using default statistics (no source data available)")
        else:
            print(f"  📊 Source files: {stats.get('source_files', [])}")
            print(f"  📈 Total graphs analyzed: {stats.get('total_graphs_analyzed', 0)}")
        
        print(f"  🏗️  Average nodes per graph: {stats['node_count']['mean']:.1f}")
        print(f"  🔗 Average edges per graph: {stats['edge_count']['mean']:.1f}")
        print(f"  ⭐ Average stance nodes: {stats['stance_node_count']['mean']:.1f}")
        print(f"  🎯 Average anchor ratio: {stats['anchor_ratio']['mean']:.2f}")
        
        if stats.get('top_words'):
            top_words = [word for word, count in stats['top_words'][:8]]
            print(f"  📝 Top words: {', '.join(top_words)}")
    
    print(f"\n{'='*80}")
    print("All topic statistics generated and cached!")
    print("Use the cached statistics for faster synthetic data generation.")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
