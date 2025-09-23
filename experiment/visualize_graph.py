"""
Visualize exported causal graphs
Simple tool to display graph structure in terminal
"""
import json
import sys
from pathlib import Path


def load_causal_graph(file_path):
    """Load causal graph from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_graph_summary(graph):
    """Print graph summary"""
    print("\n" + "="*60)
    print("CAUSAL GRAPH SUMMARY")
    print("="*60)
    
    # Basic stats
    print(f"\nSession ID: {graph.get('agent_id', 'unknown')}")
    print(f"Total Nodes: {len(graph.get('nodes', {}))}")
    print(f"Total Edges: {len(graph.get('edges', {}))}")
    print(f"QA Count: {graph.get('qa_counter', 0)}")
    
    # Node details
    print("\n--- NODES ---")
    nodes = graph.get('nodes', {})
    
    # Group by status
    anchors = []
    candidates = []
    
    for node_id, node in nodes.items():
        if node.get('status') == 'anchor' or node.get('is_stance'):
            anchors.append((node_id, node))
        else:
            candidates.append((node_id, node))
            
    # Print anchors first
    if anchors:
        print("\nAnchor Nodes:")
        for node_id, node in anchors:
            label = node.get('label', 'unknown')
            confidence = node.get('aggregate_confidence', 0)
            freq = node.get('frequency', 1)
            is_stance = " [STANCE]" if node.get('is_stance') else ""
            print(f"  • {label}{is_stance} (confidence: {confidence:.2f}, frequency: {freq})")
            
    # Print candidates
    if candidates:
        print("\nCandidate Nodes:")
        for node_id, node in candidates:
            label = node.get('label', 'unknown')
            confidence = node.get('aggregate_confidence', 0)
            freq = node.get('frequency', 1)
            print(f"  ◦ {label} (confidence: {confidence:.2f}, frequency: {freq})")
            
    # Edge details
    edges = graph.get('edges', {})
    if edges:
        print("\n--- EDGES ---")
        for edge_id, edge in edges.items():
            source_id = edge.get('source')
            target_id = edge.get('target')
            
            # Get node labels
            source_label = nodes.get(source_id, {}).get('label', 'unknown')
            target_label = nodes.get(target_id, {}).get('label', 'unknown')
            
            # Edge properties
            direction = edge.get('direction', 'unknown')
            strength = edge.get('strength', 0)
            confidence = edge.get('aggregate_confidence', 0)
            
            # Arrow based on direction
            arrow = "→(+)" if direction == 'positive' else "→(-)"
            
            print(f"  {source_label} {arrow} {target_label}")
            print(f"    Strength: {strength:.2f}, Confidence: {confidence:.2f}")
            
            # Show explanation if available
            explanation = edge.get('explanation', '').strip()
            if explanation:
                print(f"    Explanation: {explanation[:60]}...")


def print_conversation_summary(conv_file):
    """Print conversation summary"""
    with open(conv_file, 'r', encoding='utf-8') as f:
        conv = json.load(f)
        
    print("\n" + "="*60)
    print("CONVERSATION SUMMARY")
    print("="*60)
    
    print(f"\nTopic: {conv.get('topic', 'unknown')}")
    print(f"Total QA Pairs: {conv.get('total_qa_count', 0)}")
    
    qa_pairs = conv.get('qa_pairs', [])
    if qa_pairs:
        print("\n--- CONVERSATION FLOW ---")
        for i, qa in enumerate(qa_pairs, 1):
            print(f"\nQ{i}: {qa.get('question', 'unknown')}")
            answer = qa.get('answer', 'unknown')
            # Truncate long answers
            if len(answer) > 100:
                answer = answer[:100] + "..."
            print(f"A{i}: {answer}")


def create_simple_visualization(graph):
    """Create a simple ASCII visualization of the graph"""
    print("\n" + "="*60)
    print("GRAPH STRUCTURE VISUALIZATION")
    print("="*60)
    
    nodes = graph.get('nodes', {})
    edges = graph.get('edges', {})
    
    if not nodes:
        print("No nodes to visualize")
        return
        
    # Find stance node
    stance_node_id = graph.get('stance_node_id')
    
    # Build adjacency lists
    outgoing = {}
    incoming = {}
    
    for edge_id, edge in edges.items():
        source = edge.get('source')
        target = edge.get('target')
        
        if source and target:
            outgoing.setdefault(source, []).append(target)
            incoming.setdefault(target, []).append(source)
            
    # Simple visualization starting from nodes with no incoming edges
    print("\nGraph Flow (simplified):")
    print("(→ positive influence, ⊣ negative influence)\n")
    
    # Find root nodes (no incoming edges)
    root_nodes = []
    for node_id in nodes:
        if node_id not in incoming or not incoming[node_id]:
            if node_id != stance_node_id:  # Skip stance node for now
                root_nodes.append(node_id)
                
    # Visualize from roots
    visited = set()
    
    def print_node_tree(node_id, indent=0):
        if node_id in visited:
            return
        visited.add(node_id)
        
        node = nodes.get(node_id, {})
        label = node.get('label', 'unknown')
        status = "[A]" if node.get('status') == 'anchor' else "[C]"
        
        print("  " * indent + f"{status} {label}")
        
        # Print outgoing connections
        if node_id in outgoing:
            for target_id in outgoing[node_id]:
                # Find edge to get direction
                for edge_id, edge in edges.items():
                    if edge.get('source') == node_id and edge.get('target') == target_id:
                        direction = edge.get('direction', 'unknown')
                        arrow = "→" if direction == 'positive' else "⊣"
                        print("  " * (indent + 1) + arrow)
                        break
                        
                print_node_tree(target_id, indent + 2)
                
    # Print trees from root nodes
    for root in root_nodes:
        print_node_tree(root)
        
    # Print stance node connections at the end
    if stance_node_id and stance_node_id in nodes:
        print("\nConnections to Stance Node:")
        stance_label = nodes[stance_node_id].get('label', 'stance')
        print(f"[STANCE] {stance_label}")
        
        if stance_node_id in incoming:
            for source_id in incoming[stance_node_id]:
                source_label = nodes.get(source_id, {}).get('label', 'unknown')
                
                # Find edge direction
                for edge_id, edge in edges.items():
                    if edge.get('source') == source_id and edge.get('target') == stance_node_id:
                        direction = edge.get('direction', 'unknown')
                        arrow = "→" if direction == 'positive' else "⊣"
                        print(f"  {source_label} {arrow} {stance_label}")
                        break


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python visualize_graph.py <causal_graph.json> [conversation.json]")
        print("\nExample:")
        print("  python visualize_graph.py exports/causal_graph_exp_xxx.json")
        sys.exit(1)
        
    graph_file = sys.argv[1]
    conv_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check if file exists
    if not Path(graph_file).exists():
        print(f"Error: File not found: {graph_file}")
        sys.exit(1)
        
    # Load and visualize graph
    try:
        graph = load_causal_graph(graph_file)
        
        # Print conversation summary if provided
        if conv_file and Path(conv_file).exists():
            print_conversation_summary(conv_file)
            
        # Print graph summary
        print_graph_summary(graph)
        
        # Create visualization
        create_simple_visualization(graph)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
