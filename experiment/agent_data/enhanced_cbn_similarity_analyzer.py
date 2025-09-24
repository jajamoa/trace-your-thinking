"""
Enhanced CBN Similarity Analyzer
Includes edge pattern analysis in similarity metrics
"""
import json
import numpy as np
from collections import defaultdict, Counter
from pathlib import Path
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd


class EnhancedCBNSimilarityAnalyzer:
    """Enhanced analyzer that includes edge patterns"""
    
    def __init__(self):
        self.real_cbns = []
        self.synthetic_cbns = []
        self.edge_patterns = None
        
    def load_edge_patterns(self, topic='camera'):
        """Load pre-computed edge patterns"""
        pattern_file = Path(__file__).parent / "ref_data" / "cbns" / topic / f"{topic}_edge_patterns.json"
        if pattern_file.exists():
            with open(pattern_file, 'r') as f:
                self.edge_patterns = json.load(f)
            print(f"Loaded edge patterns for {topic}")
        else:
            print(f"No edge patterns found for {topic}, running basic analysis")
            
    def categorize_node(self, label):
        """Categorize node by semantic type"""
        label_lower = label.lower()
        
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
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in label_lower:
                    return category
        
        if any(word in label_lower for word in ['positive', 'negative', 'strong', 'weak']):
            return 'modifier'
        
        return 'general'
    
    def extract_edge_features(self, cbns):
        """Extract edge pattern features from CBNs"""
        edge_pattern_counts = defaultdict(int)
        correlation_patterns = defaultdict(list)
        total_edges = 0
        
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
                
                # Categorize nodes
                node_categories = {}
                for node_id, node in nodes.items():
                    label = node.get('label', '')
                    node_categories[node_id] = self.categorize_node(label)
                
                # Analyze edges
                for edge_id, edge in edges.items():
                    source_id = edge.get('source')
                    target_id = edge.get('target')
                    correlation = edge.get('correlation', 0.5)
                    
                    if source_id in nodes and target_id in nodes:
                        source_cat = node_categories[source_id]
                        target_cat = node_categories[target_id]
                        pattern = f"{source_cat}->{target_cat}"
                        
                        edge_pattern_counts[pattern] += 1
                        correlation_patterns[pattern].append(correlation)
                        total_edges += 1
        
        # Calculate pattern distribution
        pattern_distribution = {}
        for pattern, count in edge_pattern_counts.items():
            pattern_distribution[pattern] = count / total_edges if total_edges > 0 else 0
        
        # Calculate correlation statistics
        correlation_stats = {}
        for pattern, corrs in correlation_patterns.items():
            if corrs:
                correlation_stats[pattern] = {
                    'mean': np.mean(corrs),
                    'std': np.std(corrs)
                }
        
        return {
            'pattern_distribution': pattern_distribution,
            'correlation_stats': correlation_stats,
            'total_edges': total_edges,
            'unique_patterns': len(edge_pattern_counts)
        }
    
    def compare_edge_patterns(self, real_features, synthetic_features):
        """Compare edge pattern distributions"""
        real_dist = real_features['pattern_distribution']
        synth_dist = synthetic_features['pattern_distribution']
        
        # Get all patterns
        all_patterns = set(real_dist.keys()) | set(synth_dist.keys())
        
        # Create aligned distributions
        real_probs = []
        synth_probs = []
        
        for pattern in all_patterns:
            real_probs.append(real_dist.get(pattern, 0))
            synth_probs.append(synth_dist.get(pattern, 0))
        
        # Calculate similarity metrics
        # JS divergence (symmetric KL divergence)
        real_probs = np.array(real_probs) + 1e-10  # Avoid log(0)
        synth_probs = np.array(synth_probs) + 1e-10
        
        real_probs = real_probs / real_probs.sum()
        synth_probs = synth_probs / synth_probs.sum()
        
        m = (real_probs + synth_probs) / 2
        js_divergence = 0.5 * stats.entropy(real_probs, m) + 0.5 * stats.entropy(synth_probs, m)
        js_similarity = 1 - js_divergence  # Convert to similarity
        
        # Pattern overlap (Jaccard similarity)
        real_patterns = set(p for p, v in real_dist.items() if v > 0.001)
        synth_patterns = set(p for p, v in synth_dist.items() if v > 0.001)
        
        if real_patterns or synth_patterns:
            jaccard = len(real_patterns & synth_patterns) / len(real_patterns | synth_patterns)
        else:
            jaccard = 0
        
        # Top pattern similarity
        top_k = 20
        real_top = sorted(real_dist.items(), key=lambda x: x[1], reverse=True)[:top_k]
        synth_top = sorted(synth_dist.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        real_top_patterns = [p[0] for p in real_top]
        synth_top_patterns = [p[0] for p in synth_top]
        
        top_overlap = len(set(real_top_patterns) & set(synth_top_patterns)) / top_k
        
        return {
            'js_similarity': js_similarity,
            'jaccard_similarity': jaccard,
            'top_pattern_overlap': top_overlap,
            'unique_patterns_real': len(real_patterns),
            'unique_patterns_synthetic': len(synth_patterns)
        }
    
    def load_real_cbns(self, topic='camera'):
        """Load real CBNs for a specific topic"""
        print(f"Loading real CBNs for topic: {topic}")
        cbns_dir = Path(__file__).parent / "ref_data" / "cbns" / topic
        
        for json_file in cbns_dir.glob("*.json"):
            if 'statistics' not in json_file.name and 'edge_patterns' not in json_file.name:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.real_cbns.extend(data)
                    else:
                        self.real_cbns.append(data)
        
        print(f"Loaded {len(self.real_cbns)} real CBNs")
    
    def load_synthetic_cbns(self, synthetic_dir, topic='camera'):
        """Load synthetic CBNs from generated agents"""
        print(f"Loading synthetic CBNs for topic: {topic}")
        synthetic_path = Path(synthetic_dir)
        
        if not synthetic_path.exists():
            print(f"Warning: Synthetic directory {synthetic_path} does not exist")
            return
        
        # Find all GT CBN files for the specified topic in cbn folders
        cbn_files = list(synthetic_path.rglob(f"cbn/gt_cbn_{topic}.json"))
        
        for cbn_file in cbn_files:
            with open(cbn_file, 'r') as f:
                cbn = json.load(f)
                self.synthetic_cbns.append({'graphData': cbn})
        
        print(f"Loaded {len(self.synthetic_cbns)} synthetic CBNs")
    
    def extract_structural_features(self, cbns):
        """Extract standard structural features"""
        stats = defaultdict(list)
        
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
                
                # Basic counts
                node_count = len(graph.get('nodes', {}))
                edge_count = len(graph.get('edges', {}))
                
                stats['node_count'].append(node_count)
                stats['edge_count'].append(edge_count)
                
                # Edge density
                if node_count > 1:
                    max_edges = node_count * (node_count - 1) / 2
                    edge_density = edge_count / max_edges if max_edges > 0 else 0
                else:
                    edge_density = 0
                stats['edge_density'].append(edge_density)
                
                # Node degrees
                degrees = defaultdict(int)
                for edge in graph.get('edges', {}).values():
                    degrees[edge['source']] += 1
                    degrees[edge['target']] += 1
                
                if degrees:
                    stats['degree_mean'].append(np.mean(list(degrees.values())))
                    stats['degree_max'].append(max(degrees.values()))
                else:
                    stats['degree_mean'].append(0)
                    stats['degree_max'].append(0)
        
        return stats
    
    def compare_distributions(self, real_stats, synth_stats):
        """Compare distributions with statistical tests"""
        results = {}
        
        for feature in set(real_stats.keys()) | set(synth_stats.keys()):
            if feature in real_stats and feature in synth_stats:
                real_vals = np.array(real_stats[feature])
                synth_vals = np.array(synth_stats[feature])
                
                # Statistical tests
                ks_stat, ks_pval = stats.ks_2samp(real_vals, synth_vals)
                mw_stat, mw_pval = stats.mannwhitneyu(real_vals, synth_vals, alternative='two-sided')
                
                # Effect size
                pooled_std = np.sqrt((np.var(real_vals) + np.var(synth_vals)) / 2)
                cohens_d = (np.mean(real_vals) - np.mean(synth_vals)) / pooled_std if pooled_std > 0 else 0
                
                results[feature] = {
                    'real_mean': np.mean(real_vals),
                    'real_std': np.std(real_vals),
                    'synth_mean': np.mean(synth_vals),
                    'synth_std': np.std(synth_vals),
                    'ks_pval': ks_pval,
                    'mw_pval': mw_pval,
                    'cohens_d': cohens_d,
                    'similar': ks_pval > 0.05
                }
        
        return results
    
    def calculate_overall_similarity(self, structural_similarity, edge_pattern_similarity):
        """Calculate overall similarity score including edge patterns"""
        # Structural similarity (from distribution tests)
        struct_score = structural_similarity
        
        # Edge pattern similarity (average of metrics)
        edge_scores = [
            edge_pattern_similarity['js_similarity'],
            edge_pattern_similarity['jaccard_similarity'],
            edge_pattern_similarity['top_pattern_overlap']
        ]
        edge_score = np.mean(edge_scores)
        
        # Weighted average (edge patterns are important)
        overall = 0.6 * struct_score + 0.4 * edge_score
        
        return {
            'overall_score': overall,
            'structural_score': struct_score,
            'edge_pattern_score': edge_score,
            'details': {
                'js_similarity': edge_pattern_similarity['js_similarity'],
                'pattern_overlap': edge_pattern_similarity['jaccard_similarity'],
                'top_pattern_match': edge_pattern_similarity['top_pattern_overlap']
            }
        }
    
    def analyze(self, synthetic_dir, topic='camera', output_dir='enhanced_analysis'):
        """Run enhanced analysis"""
        # Load data
        self.load_edge_patterns(topic)
        self.load_real_cbns(topic)
        self.load_synthetic_cbns(synthetic_dir, topic)
        
        # Extract features
        print("Extracting structural features...")
        real_struct = self.extract_structural_features(self.real_cbns)
        synth_struct = self.extract_structural_features(self.synthetic_cbns)
        
        print("Extracting edge pattern features...")
        real_edge_features = self.extract_edge_features(self.real_cbns)
        synth_edge_features = self.extract_edge_features(self.synthetic_cbns)
        
        # Compare
        print("Comparing distributions...")
        struct_comparison = self.compare_distributions(real_struct, synth_struct)
        
        # Calculate structural similarity
        similar_features = sum(1 for f in struct_comparison.values() if f['similar'])
        total_features = len(struct_comparison)
        structural_similarity = similar_features / total_features if total_features > 0 else 0
        
        print("Comparing edge patterns...")
        edge_comparison = self.compare_edge_patterns(real_edge_features, synth_edge_features)
        
        # Overall similarity
        overall_similarity = self.calculate_overall_similarity(
            structural_similarity,
            edge_comparison
        )
        
        # Save results
        Path(output_dir).mkdir(exist_ok=True)
        
        # Convert numpy types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, (np.bool_, np.bool8)):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
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
        
        results = {
            'structural_comparison': convert_types(struct_comparison),
            'edge_pattern_comparison': convert_types(edge_comparison),
            'overall_similarity': convert_types(overall_similarity),
            'real_edge_features': convert_types(real_edge_features),
            'synthetic_edge_features': convert_types(synth_edge_features)
        }
        
        with open(f"{output_dir}/enhanced_similarity_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        # Create report
        report = self.generate_report(results)
        with open(f"{output_dir}/enhanced_similarity_report.txt", 'w') as f:
            f.write(report)
        
        print(f"\nOverall similarity score: {overall_similarity['overall_score']:.2%}")
        print(f"- Structural similarity: {overall_similarity['structural_score']:.2%}")
        print(f"- Edge pattern similarity: {overall_similarity['edge_pattern_score']:.2%}")
        
        return results
    
    def generate_report(self, results):
        """Generate detailed report"""
        report = []
        report.append("ENHANCED CBN SIMILARITY ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall scores
        overall = results['overall_similarity']
        report.append("OVERALL SIMILARITY")
        report.append("-" * 40)
        report.append(f"Overall Score: {overall['overall_score']:.2%}")
        report.append(f"Structural Score: {overall['structural_score']:.2%}")
        report.append(f"Edge Pattern Score: {overall['edge_pattern_score']:.2%}")
        report.append("")
        
        # Edge pattern details
        report.append("EDGE PATTERN ANALYSIS")
        report.append("-" * 40)
        edge_comp = results['edge_pattern_comparison']
        report.append(f"Pattern Distribution Similarity (JS): {edge_comp['js_similarity']:.3f}")
        report.append(f"Pattern Overlap (Jaccard): {edge_comp['jaccard_similarity']:.3f}")
        report.append(f"Top Pattern Overlap: {edge_comp['top_pattern_overlap']:.3f}")
        report.append(f"Unique patterns in real data: {edge_comp['unique_patterns_real']}")
        report.append(f"Unique patterns in synthetic data: {edge_comp['unique_patterns_synthetic']}")
        report.append("")
        
        # Top patterns comparison
        real_patterns = results['real_edge_features']['pattern_distribution']
        synth_patterns = results['synthetic_edge_features']['pattern_distribution']
        
        report.append("TOP EDGE PATTERNS")
        report.append("-" * 40)
        report.append("Real data top patterns:")
        real_top = sorted(real_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
        for pattern, freq in real_top:
            report.append(f"  {pattern}: {freq:.3f}")
        
        report.append("\nSynthetic data top patterns:")
        synth_top = sorted(synth_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
        for pattern, freq in synth_top:
            report.append(f"  {pattern}: {freq:.3f}")
        
        report.append("")
        
        # Structural comparison
        report.append("STRUCTURAL COMPARISON")
        report.append("-" * 40)
        struct_comp = results['structural_comparison']
        
        for feature, stats in sorted(struct_comp.items()):
            report.append(f"\n{feature.upper()}:")
            report.append(f"  Real: mean={stats['real_mean']:.3f}, std={stats['real_std']:.3f}")
            report.append(f"  Synthetic: mean={stats['synth_mean']:.3f}, std={stats['synth_std']:.3f}")
            report.append(f"  KS test p-value: {stats['ks_pval']:.4f}")
            report.append(f"  Similar distribution: {'YES' if stats['similar'] else 'NO'}")
        
        return "\n".join(report)


if __name__ == "__main__":
    import sys
    
    synthetic_dir = sys.argv[1] if len(sys.argv) > 1 else "synthetic_agents"
    topic = sys.argv[2] if len(sys.argv) > 2 else "camera"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "enhanced_analysis"
    
    analyzer = EnhancedCBNSimilarityAnalyzer()
    analyzer.analyze(synthetic_dir, topic, output_dir)
