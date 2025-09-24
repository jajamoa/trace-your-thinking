"""
CBN Similarity Analyzer
Compares synthetic CBNs with real CBNs across multiple dimensions:
- Structural similarity (node/edge distributions)
- Semantic similarity (label content)
- Graph properties (connectivity, clustering)
- Statistical distributions
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class CBNSimilarityAnalyzer:
    """Analyzes similarity between synthetic and real CBNs"""
    
    def __init__(self):
        self.real_cbns = []
        self.synthetic_cbns = []
        self.real_stats = defaultdict(list)
        self.synthetic_stats = defaultdict(list)
        
    def load_real_cbns(self, cbns_dir, topic='zoning'):
        """Load real CBNs from reference data"""
        print(f"Loading real CBNs for topic: {topic}")
        cbns_path = Path(cbns_dir) / topic
        
        if not cbns_path.exists():
            print(f"Warning: No real data found for topic {topic}")
            return
        
        # Load all JSON files except statistics
        json_files = [f for f in cbns_path.glob("*.json") 
                     if not f.name.endswith('_statistics.json')]
        
        for json_file in json_files:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            # Extract individual CBNs
            for session in data:
                if 'graphs' not in session:
                    continue
                    
                for graph_item in session['graphs']:
                    if 'graphData' in graph_item:
                        cbn = graph_item['graphData']
                        cbn['source_file'] = json_file.name
                        cbn['session_id'] = session.get('sessionId', 'unknown')
                        self.real_cbns.append(cbn)
        
        print(f"Loaded {len(self.real_cbns)} real CBNs")
    
    def load_synthetic_cbns(self, synthetic_dir, topic='zoning'):
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
                cbn['source_file'] = cbn_file.name
                cbn['agent_id'] = cbn_file.parent.parent.name  # Two levels up from cbn folder
                self.synthetic_cbns.append(cbn)
        
        print(f"Loaded {len(self.synthetic_cbns)} synthetic CBNs")
    
    def extract_features(self, cbns, label=''):
        """Extract comprehensive features from CBNs"""
        stats = defaultdict(list)
        all_labels = []
        
        for cbn in cbns:
            nodes = cbn.get('nodes', {})
            edges = cbn.get('edges', {})
            
            # Basic counts
            node_count = len(nodes)
            edge_count = len(edges)
            stats['node_count'].append(node_count)
            stats['edge_count'].append(edge_count)
            
            # Edge density (ratio of actual edges to possible edges)
            if node_count > 1:
                max_edges = node_count * (node_count - 1) / 2
                edge_density = edge_count / max_edges if max_edges > 0 else 0
            else:
                edge_density = 0
            stats['edge_density'].append(edge_density)
            
            # Node features
            confidences = []
            importances = []
            evidence_counts = []
            node_labels = []
            anchor_count = 0
            stance_count = 0
            
            for node_id, node in nodes.items():
                # Confidence and importance
                conf = node.get('aggregate_confidence', 0)
                imp = node.get('importance', 0)
                confidences.append(conf)
                importances.append(imp)
                
                # Evidence count
                evidence_count = len(node.get('evidence', []))
                evidence_counts.append(evidence_count)
                
                # Labels
                label_text = node.get('label', '')
                if label_text:
                    node_labels.append(label_text)
                    all_labels.append(label_text)
                
                # Node types
                if node.get('status') == 'anchor':
                    anchor_count += 1
                if node.get('is_stance', False):
                    stance_count += 1
            
            # Store node-level statistics
            if confidences:
                stats['confidence_mean'].append(np.mean(confidences))
                stats['confidence_std'].append(np.std(confidences))
            else:
                stats['confidence_mean'].append(0)
                stats['confidence_std'].append(0)
                
            if importances:
                stats['importance_mean'].append(np.mean(importances))
                stats['importance_std'].append(np.std(importances))
            else:
                stats['importance_mean'].append(0)
                stats['importance_std'].append(0)
            
            if evidence_counts:
                stats['evidence_mean'].append(np.mean(evidence_counts))
                stats['evidence_max'].append(np.max(evidence_counts))
            else:
                stats['evidence_mean'].append(0)
                stats['evidence_max'].append(0)
            
            # Node type ratios
            stats['anchor_ratio'].append(anchor_count / node_count if node_count > 0 else 0)
            stats['stance_count'].append(stance_count)
            
            # Edge features
            weights = []
            correlations = []
            for edge_id, edge in edges.items():
                weights.append(edge.get('weight', 0.5))
                correlations.append(edge.get('correlation', 0.5))
            
            if weights:
                stats['weight_mean'].append(np.mean(weights))
                stats['weight_std'].append(np.std(weights))
            else:
                stats['weight_mean'].append(0.5)
                stats['weight_std'].append(0)
                
            if correlations:
                stats['correlation_mean'].append(np.mean(correlations))
                stats['correlation_std'].append(np.std(correlations))
            else:
                stats['correlation_mean'].append(0.5)
                stats['correlation_std'].append(0)
            
            # Graph connectivity
            in_degrees = defaultdict(int)
            out_degrees = defaultdict(int)
            
            for edge in edges.values():
                source = edge.get('source')
                target = edge.get('target')
                if source and target:
                    out_degrees[source] += 1
                    in_degrees[target] += 1
            
            degrees = list(in_degrees.values()) + list(out_degrees.values())
            if degrees:
                stats['degree_mean'].append(np.mean(degrees))
                stats['degree_max'].append(np.max(degrees))
            else:
                stats['degree_mean'].append(0)
                stats['degree_max'].append(0)
        
        return stats, all_labels
    
    def compare_distributions(self, real_stats, synthetic_stats):
        """Compare distributions using statistical tests"""
        comparison_results = {}
        
        for feature in real_stats:
            if feature not in synthetic_stats:
                continue
                
            real_data = np.array(real_stats[feature])
            synthetic_data = np.array(synthetic_stats[feature])
            
            # Skip if either is empty
            if len(real_data) == 0 or len(synthetic_data) == 0:
                continue
            
            # Kolmogorov-Smirnov test
            ks_stat, ks_pvalue = stats.ks_2samp(real_data, synthetic_data)
            
            # Mann-Whitney U test (non-parametric)
            mw_stat, mw_pvalue = stats.mannwhitneyu(real_data, synthetic_data, alternative='two-sided')
            
            # Calculate effect size (Cohen's d)
            mean_diff = np.mean(real_data) - np.mean(synthetic_data)
            pooled_std = np.sqrt((np.std(real_data)**2 + np.std(synthetic_data)**2) / 2)
            cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0
            
            comparison_results[feature] = {
                'real_mean': np.mean(real_data),
                'real_std': np.std(real_data),
                'synthetic_mean': np.mean(synthetic_data),
                'synthetic_std': np.std(synthetic_data),
                'ks_statistic': ks_stat,
                'ks_pvalue': ks_pvalue,
                'mw_pvalue': mw_pvalue,
                'cohens_d': cohens_d,
                'similar': ks_pvalue > 0.05  # Not significantly different
            }
        
        return comparison_results
    
    def analyze_semantic_similarity(self, real_labels, synthetic_labels):
        """Analyze semantic similarity of node labels"""
        if not real_labels or not synthetic_labels:
            return {}
        
        # Create vocabulary
        all_labels = real_labels + synthetic_labels
        
        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        
        # Fit on all labels
        vectorizer.fit(all_labels)
        
        # Transform separately
        real_vectors = vectorizer.transform(real_labels)
        synthetic_vectors = vectorizer.transform(synthetic_labels)
        
        # Calculate average vectors
        real_avg = real_vectors.mean(axis=0).A[0]
        synthetic_avg = synthetic_vectors.mean(axis=0).A[0]
        
        # Cosine similarity
        similarity = cosine_similarity([real_avg], [synthetic_avg])[0][0]
        
        # Top words analysis
        feature_names = vectorizer.get_feature_names_out()
        
        # Top words in real data
        real_top_indices = real_avg.argsort()[-20:][::-1]
        real_top_words = [feature_names[i] for i in real_top_indices if real_avg[i] > 0]
        
        # Top words in synthetic data
        synthetic_top_indices = synthetic_avg.argsort()[-20:][::-1]
        synthetic_top_words = [feature_names[i] for i in synthetic_top_indices if synthetic_avg[i] > 0]
        
        # Word overlap
        word_overlap = len(set(real_top_words) & set(synthetic_top_words)) / len(set(real_top_words) | set(synthetic_top_words))
        
        return {
            'cosine_similarity': similarity,
            'word_overlap': word_overlap,
            'real_top_words': real_top_words[:10],
            'synthetic_top_words': synthetic_top_words[:10],
            'unique_real_words': list(set(real_top_words) - set(synthetic_top_words))[:10],
            'unique_synthetic_words': list(set(synthetic_top_words) - set(real_top_words))[:10]
        }
    
    def plot_distributions(self, real_stats, synthetic_stats, output_dir):
        """Create visualization plots"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Features to plot
        features_to_plot = [
            ('node_count', 'Number of Nodes', 'count'),
            ('edge_count', 'Number of Edges', 'count'),
            ('edge_density', 'Edge Density', 'density'),
            ('confidence_mean', 'Average Confidence', 'probability'),
            ('importance_mean', 'Average Importance', 'probability'),
            ('anchor_ratio', 'Anchor Node Ratio', 'ratio'),
            ('evidence_mean', 'Average Evidence Count', 'count'),
            ('degree_mean', 'Average Node Degree', 'count')
        ]
        
        # Create subplots
        fig, axes = plt.subplots(2, 4, figsize=(20, 10))
        axes = axes.flatten()
        
        for idx, (feature, title, ylabel) in enumerate(features_to_plot):
            ax = axes[idx]
            
            if feature in real_stats and feature in synthetic_stats:
                real_data = real_stats[feature]
                synthetic_data = synthetic_stats[feature]
                
                # Create overlapping histograms
                ax.hist(real_data, bins=30, alpha=0.5, label='Real', color='blue', density=True)
                ax.hist(synthetic_data, bins=30, alpha=0.5, label='Synthetic', color='red', density=True)
                
                ax.set_xlabel(title)
                ax.set_ylabel('Density')
                ax.legend()
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path / 'distribution_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create box plots
        fig, axes = plt.subplots(2, 4, figsize=(20, 10))
        axes = axes.flatten()
        
        for idx, (feature, title, ylabel) in enumerate(features_to_plot):
            ax = axes[idx]
            
            if feature in real_stats and feature in synthetic_stats:
                data_to_plot = []
                labels = []
                
                if len(real_stats[feature]) > 0:
                    data_to_plot.append(real_stats[feature])
                    labels.append('Real')
                
                if len(synthetic_stats[feature]) > 0:
                    data_to_plot.append(synthetic_stats[feature])
                    labels.append('Synthetic')
                
                if data_to_plot:
                    ax.boxplot(data_to_plot, labels=labels)
                    ax.set_ylabel(title)
                    ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path / 'boxplot_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_report(self, output_dir):
        """Generate comprehensive comparison report"""
        # Extract features
        print("Extracting features from real CBNs...")
        real_stats, real_labels = self.extract_features(self.real_cbns, 'real')
        
        print("Extracting features from synthetic CBNs...")
        synthetic_stats, synthetic_labels = self.extract_features(self.synthetic_cbns, 'synthetic')
        
        # Compare distributions
        print("Comparing distributions...")
        comparison_results = self.compare_distributions(real_stats, synthetic_stats)
        
        # Analyze semantic similarity
        print("Analyzing semantic similarity...")
        semantic_results = self.analyze_semantic_similarity(real_labels, synthetic_labels)
        
        # Create plots
        print("Creating visualizations...")
        self.plot_distributions(real_stats, synthetic_stats, output_dir)
        
        # Generate text report
        report_path = Path(output_dir) / 'similarity_report.txt'
        with open(report_path, 'w') as f:
            f.write("CBN SIMILARITY ANALYSIS REPORT\n")
            f.write("="*80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("DATA SUMMARY\n")
            f.write("-"*40 + "\n")
            f.write(f"Real CBNs analyzed: {len(self.real_cbns)}\n")
            f.write(f"Synthetic CBNs analyzed: {len(self.synthetic_cbns)}\n\n")
            
            f.write("DISTRIBUTION COMPARISON\n")
            f.write("-"*40 + "\n")
            
            # Sort features by p-value
            sorted_features = sorted(comparison_results.items(), 
                                   key=lambda x: x[1]['ks_pvalue'])
            
            for feature, results in sorted_features:
                f.write(f"\n{feature.upper().replace('_', ' ')}:\n")
                f.write(f"  Real: mean={results['real_mean']:.3f}, std={results['real_std']:.3f}\n")
                f.write(f"  Synthetic: mean={results['synthetic_mean']:.3f}, std={results['synthetic_std']:.3f}\n")
                f.write(f"  KS test p-value: {results['ks_pvalue']:.4f}\n")
                f.write(f"  Mann-Whitney p-value: {results['mw_pvalue']:.4f}\n")
                f.write(f"  Cohen's d: {results['cohens_d']:.3f}\n")
                f.write(f"  Similar distribution: {'YES' if results['similar'] else 'NO'}\n")
            
            f.write("\n\nSEMANTIC SIMILARITY\n")
            f.write("-"*40 + "\n")
            f.write(f"Cosine similarity: {semantic_results.get('cosine_similarity', 0):.3f}\n")
            f.write(f"Top word overlap: {semantic_results.get('word_overlap', 0):.3f}\n")
            
            f.write("\nTop words in REAL data:\n")
            for word in semantic_results.get('real_top_words', []):
                f.write(f"  - {word}\n")
            
            f.write("\nTop words in SYNTHETIC data:\n")
            for word in semantic_results.get('synthetic_top_words', []):
                f.write(f"  - {word}\n")
            
            f.write("\n\nOVERALL SIMILARITY SCORE\n")
            f.write("-"*40 + "\n")
            
            # Calculate overall similarity score
            similar_features = sum(1 for r in comparison_results.values() if r['similar'])
            total_features = len(comparison_results)
            distribution_similarity = similar_features / total_features if total_features > 0 else 0
            
            semantic_similarity = semantic_results.get('cosine_similarity', 0)
            
            overall_score = (distribution_similarity + semantic_similarity) / 2
            
            f.write(f"Distribution similarity: {distribution_similarity:.2%} ({similar_features}/{total_features} features)\n")
            f.write(f"Semantic similarity: {semantic_similarity:.2%}\n")
            f.write(f"Overall similarity score: {overall_score:.2%}\n")
        
        # Save detailed results as JSON
        json_path = Path(output_dir) / 'similarity_results.json'
        with open(json_path, 'w') as f:
            # Convert numpy types to Python types for JSON serialization
            json_results = {
                'summary': {
                    'real_cbns': int(len(self.real_cbns)),
                    'synthetic_cbns': int(len(self.synthetic_cbns)),
                    'overall_similarity': float(overall_score),
                    'distribution_similarity': float(distribution_similarity),
                    'semantic_similarity': float(semantic_similarity)
                },
                'distribution_comparison': {
                    k: {
                        'real_mean': float(v['real_mean']),
                        'real_std': float(v['real_std']),
                        'synthetic_mean': float(v['synthetic_mean']),
                        'synthetic_std': float(v['synthetic_std']),
                        'ks_statistic': float(v['ks_statistic']),
                        'ks_pvalue': float(v['ks_pvalue']),
                        'mw_pvalue': float(v['mw_pvalue']),
                        'cohens_d': float(v['cohens_d']),
                        'similar': bool(v['similar'])
                    } for k, v in comparison_results.items()
                },
                'semantic_analysis': semantic_results,
                'real_statistics': {k: {
                    'mean': float(np.mean(v)),
                    'std': float(np.std(v)),
                    'min': float(np.min(v)) if len(v) > 0 else 0,
                    'max': float(np.max(v)) if len(v) > 0 else 0
                } for k, v in real_stats.items()},
                'synthetic_statistics': {k: {
                    'mean': float(np.mean(v)),
                    'std': float(np.std(v)),
                    'min': float(np.min(v)) if len(v) > 0 else 0,
                    'max': float(np.max(v)) if len(v) > 0 else 0
                } for k, v in synthetic_stats.items()}
            }
            json.dump(json_results, f, indent=2)
        
        print(f"\nReport saved to: {report_path}")
        print(f"Detailed results saved to: {json_path}")
        print(f"Visualizations saved to: {output_dir}")
        
        return overall_score


def main():
    """Main function to run similarity analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze similarity between synthetic and real CBNs')
    parser.add_argument('--real_cbns_dir', type=str, 
                       default='ref_data/cbns',
                       help='Directory containing real CBN data')
    parser.add_argument('--synthetic_dir', type=str,
                       default='synthetic_agents',
                       help='Directory containing synthetic agents')
    parser.add_argument('--topic', type=str, default='zoning',
                       choices=['zoning', 'healthcare', 'camera'],
                       help='Topic to analyze')
    parser.add_argument('--output_dir', type=str,
                       default='similarity_analysis',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = CBNSimilarityAnalyzer()
    
    # Load data
    analyzer.load_real_cbns(args.real_cbns_dir, args.topic)
    analyzer.load_synthetic_cbns(args.synthetic_dir, args.topic)
    
    # Generate report
    if len(analyzer.real_cbns) > 0 and len(analyzer.synthetic_cbns) > 0:
        overall_score = analyzer.generate_report(args.output_dir)
        print(f"\nOverall similarity score: {overall_score:.2%}")
    else:
        print("Error: No CBNs loaded. Check your data paths.")


if __name__ == "__main__":
    main()
