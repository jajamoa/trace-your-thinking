"""
CBN Manager Module
Responsible for managing the Causal Belief Network graph, including node merging, edge updates, etc.
"""
import uuid
import time
import json
from collections import defaultdict
import logging
import re
from llm_logger import llm_logger  # Import here to avoid circular import


class SemanticSimilarityEngine:
    """
    Engine for computing semantic similarity between node labels
    """
    
    def __init__(self, similarity_threshold=0.7):
        """Initialize the semantic similarity engine with threshold"""
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(__name__)
    
    def preprocess_label(self, label):
        """Preprocess node label for semantic comparison"""
        # Convert to lowercase and remove punctuation/special chars
        label = re.sub(r'[^a-zA-Z0-9\s]', ' ', label.lower())
        # Split into words
        return label.split()
    
    def node_similarity(self, label1, label2):
        """
        Calculate semantic similarity between two node labels
        
        Returns:
            float: Similarity score between 0 and 1
        """
        # Preprocess labels
        words1 = self.preprocess_label(label1)
        words2 = self.preprocess_label(label2)
        
        # Simple token overlap as a baseline
        common_words = set(words1).intersection(set(words2))
        total_words = set(words1).union(set(words2))
        
        if not total_words:
            return 0.0
        
        # Jaccard similarity coefficient
        return len(common_words) / len(total_words)
    
    def find_similar_nodes(self, nodes):
        """
        Find all pairs of nodes with similarity exceeding the threshold
        
        Args:
            nodes (dict): Dictionary of node_id -> node mapping from the graph
            
        Returns:
            list: List of tuples (node_id1, node_id2, similarity) for similar nodes
        """
        if not nodes or len(nodes) < 2:
            return []
        
        self.logger.info(f"Finding similar nodes with semantic similarity method (threshold: {self.similarity_threshold})")
        
        similar_pairs = []
        processed_pairs = set()  # Track which pairs we've already compared
        
        # Compare each pair of nodes
        node_ids = list(nodes.keys())
        for i, node_id1 in enumerate(node_ids):
            for j, node_id2 in enumerate(node_ids[i+1:], i+1):  # Start from i+1 to avoid comparing twice
                # Skip if either node doesn't exist
                if node_id1 not in nodes or node_id2 not in nodes:
                    continue
                
                # Skip if already processed this pair
                pair_key = tuple(sorted([node_id1, node_id2]))
                if pair_key in processed_pairs:
                    continue
                
                processed_pairs.add(pair_key)
                
                # Get node labels
                label1 = nodes[node_id1].get('label', '')
                label2 = nodes[node_id2].get('label', '')
                
                # Skip if either label is empty
                if not label1 or not label2:
                    continue
                
                # Calculate similarity
                similarity = self.node_similarity(label1, label2)
                
                # If similarity exceeds threshold, add to results
                if similarity >= self.similarity_threshold:
                    self.logger.info(f"Similar nodes found: '{label1}' <-> '{label2}' (similarity: {similarity:.2f})")
                    similar_pairs.append((node_id1, node_id2, similarity))
        
        self.logger.info(f"Found {len(similar_pairs)} pairs of similar nodes")
        return similar_pairs


class CBNManager:
    """
    Manage the Causal Belief Network (CBN) graph, including node merging, edge updates, etc.
    """
    
    def __init__(self):
        """Initialize the CBN manager"""
        # Track anchor queue
        self.anchor_queue = []
        # Track node synonyms/clusters
        self.node_clusters = defaultdict(list)
        # Track current step
        self.current_step = 1  # Start with Step 1: Node Discovery
        # Track whether the interview has terminated
        self.terminate_interview = False
        # Track stable rounds for convergence
        self.stable_rounds = 0
        # Maximum allowed anchors
        self.max_anchors = 25  # Increased from 7 to 25
        # Maximum number of QA pairs before termination
        self.max_qa_count = 50  # Increased from 10 to 50
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        # LLM for similarity check (will be set by caller if needed)
        self.llm_extractor = None
        # Semantic similarity engine
        self.similarity_engine = SemanticSimilarityEngine(similarity_threshold=0.7)
    
    def set_llm_extractor(self, extractor):
        """
        Set the LLM extractor for similarity checks
        
        Args:
            extractor: LLM extractor instance
        """
        self.llm_extractor = extractor
    
    def merge_and_tag_nodes(self, cbn, new_nodes):
        """
        Add new nodes to the CBN (without merging).
        Merging will be handled by merge_graph_components.
        
        Args:
            cbn (dict): The existing CBN
            new_nodes (dict): New nodes to add
            
        Returns:
            dict: Updated CBN
        """
        # Ensure required structures exist
        if 'nodes' not in cbn:
            cbn['nodes'] = {}
        
        # Simply add new nodes to the CBN
        for node_id, node_data in new_nodes.items():
            # Create a temporary node ID
            temp_node_id = f"temp_{uuid.uuid4().hex[:8]}"
            
            # Get the evidence from the node data
            evidence = node_data.get('evidence', [])
            
            # If no evidence provided, create a default evidence entry
            if not evidence:
                # Get QA ID - try to extract it or use a default
                qa_id = "unknown_qa_id"
                if 'source_qa' in node_data and node_data['source_qa']:
                    qa_id = node_data['source_qa'][0]
                
                # Create default evidence entry
                evidence = [{
                    "qa_id": qa_id,
                    "confidence": node_data.get('aggregate_confidence', 0.5),
                    "importance": node_data.get('importance', 0.5)
                }]
                
                # Create and add the new node with evidence structure
            cbn['nodes'][temp_node_id] = {
                    "label": node_data.get('label', ''),
                "aggregate_confidence": node_data.get('aggregate_confidence', 0.5),
                "evidence": evidence,
                    "incoming_edges": [],
                    "outgoing_edges": [],
                "importance": node_data.get('importance', 0.5),
                    "status": "candidate",  # Default to candidate status
                "frequency": node_data.get('frequency', 1)  # Use provided frequency or default to 1
                }
        
        return cbn
    
    def add_edge(self, cbn, edge_data):
        """
        Add a new edge to the CBN (without merging).
        Merging will be handled by merge_graph_components.
        
        Args:
            cbn (dict): The existing CBN
            edge_data (dict): Edge data to add
            
        Returns:
            tuple: (Updated CBN, edge ID or None)
        """
        # Ensure required structures exist
        if 'edges' not in cbn:
            cbn['edges'] = {}
        if 'nodes' not in cbn:
            cbn['nodes'] = {}
        
        # Find the nodes corresponding to the from/to labels
        from_node_id = None
        to_node_id = None
        from_label = edge_data['from_label'].lower()
        to_label = edge_data['to_label'].lower()
        
        # Try to find nodes by label
        for node_id, node in cbn['nodes'].items():
            if node['label'].lower() == from_label:
                from_node_id = node_id
            if node['label'].lower() == to_label:
                to_node_id = node_id
        
        # If nodes don't exist, we can't create the edge
        if not from_node_id or not to_node_id:
            return cbn, None
        
        # Get confidence from edge data (default 0.7)
        confidence = edge_data.get('aggregate_confidence', 0.7)
        
        # Calculate modifier based on direction (-1.0 to 1.0) and strength
        strength = edge_data.get('strength', 0.7)
        direction = edge_data.get('direction', 'positive')
        modifier = strength if direction == 'positive' else -strength
            
        # Scale by confidence to get [-confidence, +confidence]
        adjusted_modifier = modifier * confidence
        
        # Create evidence entry with required fields according to schema
        evidence_entry = {
            "qa_id": edge_data.get('support_qas', ['unknown_qa_id'])[0],
            "confidence": confidence,
            "original_modifier": modifier
        }
        
        # Create a new edge with sequential ID
        if 'edge_counter' not in cbn:
            cbn['edge_counter'] = 0
        
        cbn['edge_counter'] += 1
        edge_id = f"e{cbn['edge_counter']}"
        
        # Create edge structure with evidence
        cbn['edges'][edge_id] = {
            "source": from_node_id,
            "target": to_node_id,
            "aggregate_confidence": confidence,  # Initially equal to the single evidence confidence
            "evidence": [evidence_entry],
            "modifier": adjusted_modifier,
            "source_label": edge_data.get('from_label', ''),
            "target_label": edge_data.get('to_label', ''),
            "explanation": edge_data.get('explanation', ''),
            "direction": direction,
            "strength": strength
        }
        
        # Log the created edge with additional information
        self.logger.info(f"Created edge {edge_id}: {edge_data.get('from_label', '')} → {edge_data.get('to_label', '')} ({direction}, strength: {strength:.2f}, aggregate_confidence: {confidence:.2f})")
        if edge_data.get('explanation'):
            self.logger.info(f"  Explanation: {edge_data.get('explanation')}")
            
            # Update node references
            cbn['nodes'][from_node_id]['outgoing_edges'].append(edge_id)
            cbn['nodes'][to_node_id]['incoming_edges'].append(edge_id)
        
        return cbn, edge_id
    
    def merge_graph_components(self, cbn):
        """
        Unified function to merge similar nodes and duplicate edges in the graph.
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            dict: Updated CBN with merged components
        """
        llm_logger.log_separator("GRAPH COMPONENT MERGING - START")
        self.logger.info("Starting graph component merging")
        
        # Log the graph state before merging
        node_count = len(cbn.get('nodes', {}))
        edge_count = len(cbn.get('edges', {}))
        anchor_count = len(cbn.get('anchor_queue', []))
        self.logger.info(f"Initial graph state: {node_count} nodes, {edge_count} edges, {anchor_count} anchors")
        
        # 1. Find and merge similar nodes
        llm_logger.log_separator("NODE MERGING - IDENTIFICATION PHASE")
        node_merge_candidates = self._find_mergeable_nodes(cbn)
        self.logger.info(f"Found {len(node_merge_candidates)} node merge candidates")
        
        # Apply node merges
        if node_merge_candidates:
            llm_logger.log_separator("NODE MERGING - EXECUTION PHASE")
            merge_count = 0
            for source_id, target_id in node_merge_candidates:
                # Skip if either node no longer exists (could have been merged already)
                if source_id not in cbn['nodes'] or target_id not in cbn['nodes']:
                    self.logger.info(f"Skipping merge: node {source_id} or {target_id} no longer exists")
                    continue
                    
                source_label = cbn['nodes'][source_id].get('label', 'unknown')
                target_label = cbn['nodes'][target_id].get('label', 'unknown')
                self.logger.info(f"Merging node '{source_label}' ({source_id}) into '{target_label}' ({target_id})")
                
                # Perform the merge
                cbn = self._merge_nodes(cbn, source_id, target_id)
                merge_count += 1
                
                # After each node merge, check for and merge any duplicate edges that might have been created
                cbn = self._merge_duplicate_edges_after_node_merge(cbn, target_id)
            
            self.logger.info(f"Successfully merged {merge_count} nodes")
        else:
            self.logger.info("No nodes to merge")
        
        # 3. Check for node promotion after merging
        llm_logger.log_separator("POST-MERGE NODE PROMOTION CHECK")
        self._check_node_promotion(cbn)
        
        # Log the final state after merging
        updated_node_count = len(cbn.get('nodes', {}))
        updated_edge_count = len(cbn.get('edges', {}))
        updated_anchor_count = len(cbn.get('anchor_queue', []))
        
        self.logger.info(f"Final graph state: {updated_node_count} nodes, {updated_edge_count} edges, {updated_anchor_count} anchors")
        self.logger.info(f"Changes: {node_count - updated_node_count} nodes removed, {edge_count - updated_edge_count} edges removed, {updated_anchor_count - anchor_count} new anchors")
        
        llm_logger.log_separator("GRAPH COMPONENT MERGING - COMPLETE")
        return cbn
    
    def _find_mergeable_nodes(self, cbn):
        """
        Find nodes that should be merged using semantic similarity analysis.
        Then determine merge direction based on priority rules.
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            list: List of tuples (source_id, target_id) for nodes to merge
        """
        merge_candidates = []
        
        # Skip if there are not enough nodes to consider merging
        if 'nodes' not in cbn or len(cbn['nodes']) < 2:
            return merge_candidates
        
        # Use semantic similarity to find similar nodes
        self.logger.info("Using semantic similarity to find similar nodes in graph")
        similar_node_pairs = self.similarity_engine.find_similar_nodes(cbn['nodes'])
        
        # Determine merge direction for each similar pair based on priority rules
        for node_id1, node_id2, similarity in similar_node_pairs:
            # Skip if either node doesn't exist in the graph
            if node_id1 not in cbn['nodes'] or node_id2 not in cbn['nodes']:
                self.logger.info(f"Skipping node pair: {node_id1} or {node_id2} not found in graph")
                continue
                
            # Get node data
            node1 = cbn['nodes'][node_id1]
            node2 = cbn['nodes'][node_id2]
            
            # Determine merge direction based on priority rules
            source_id, target_id = self._determine_merge_direction(node_id1, node_id2, node1, node2)
            
            # Get labels for logging
            source_node = cbn['nodes'][source_id]
            target_node = cbn['nodes'][target_id]
            source_label = source_node.get('label', 'unknown')
            target_label = target_node.get('label', 'unknown')
            
            self.logger.info(f"Merge direction determined: '{source_label}' ({source_id}) will merge into '{target_label}' ({target_id})")
            merge_candidates.append((source_id, target_id))
        
        return merge_candidates
    
    def _determine_merge_direction(self, node_id1, node_id2, node1, node2):
        """
        Determine which node should be kept (target) and which should be merged (source)
        based on priority rules.
        
        Priority rules:
        1. If one node is a stance node, it should be the target
        2. If one node is an anchor and the other isn't, anchor should be the target
        3. Higher frequency node should be the target
        4. Higher importance node should be the target
        5. Higher confidence node should be the target
        
        Args:
            node_id1 (str): ID of first node
            node_id2 (str): ID of second node
            node1 (dict): Data of first node
            node2 (dict): Data of second node
            
        Returns:
            tuple: (source_id, target_id) indicating merge direction
        """
        # Initialize with assumption that node1 is source and node2 is target
        source_id, target_id = node_id1, node_id2
        source_node, target_node = node1, node2
        
        # Rule 1: Stance node priority (highest)
        node1_is_stance = node1.get('is_stance', False)
        node2_is_stance = node2.get('is_stance', False)
        
        if node1_is_stance and not node2_is_stance:
            # node1 is stance, so it should be the target
            source_id, target_id = node_id2, node_id1
            source_node, target_node = node2, node1
            self.logger.info(f"Priority rule applied: Node {node_id1} is a stance node, keeping it as target")
            return source_id, target_id
            
        if node2_is_stance and not node1_is_stance:
            # node2 is stance, so it should be the target (already our assumption)
            self.logger.info(f"Priority rule applied: Node {node_id2} is a stance node, keeping it as target")
            return source_id, target_id
            
        # If both or neither are stance nodes, proceed to next rule
            
        # Rule 2: Anchor node priority
        node1_is_anchor = node1.get('status') == 'anchor'
        node2_is_anchor = node2.get('status') == 'anchor'
        
        if node1_is_anchor and not node2_is_anchor:
            # node1 is anchor, so it should be the target
            source_id, target_id = node_id2, node_id1
            source_node, target_node = node2, node1
            self.logger.info(f"Priority rule applied: Node {node_id1} is an anchor node, keeping it as target")
            return source_id, target_id
            
        if node2_is_anchor and not node1_is_anchor:
            # node2 is anchor, so it should be the target (already our assumption)
            self.logger.info(f"Priority rule applied: Node {node_id2} is an anchor node, keeping it as target")
            return source_id, target_id
            
        # If both or neither are anchor nodes, proceed to next rule
            
        # Rule 3: Higher frequency wins
        node1_freq = node1.get('frequency', 1)
        node2_freq = node2.get('frequency', 1)
        
        if node1_freq > node2_freq:
            # node1 has higher frequency, so it should be the target
            source_id, target_id = node_id2, node_id1
            source_node, target_node = node2, node1
            self.logger.info(f"Priority rule applied: Node {node_id1} has higher frequency ({node1_freq} > {node2_freq})")
            return source_id, target_id
            
        if node2_freq > node1_freq:
            # node2 has higher frequency (already our assumption)
            self.logger.info(f"Priority rule applied: Node {node_id2} has higher frequency ({node2_freq} > {node1_freq})")
            return source_id, target_id
            
        # If frequencies are equal, proceed to next rule
            
        # Rule 4: Higher importance wins
        node1_importance = node1.get('importance', 0.5)
        node2_importance = node2.get('importance', 0.5)
        
        if node1_importance > node2_importance:
            # node1 has higher importance, so it should be the target
            source_id, target_id = node_id2, node_id1
            source_node, target_node = node2, node1
            self.logger.info(f"Priority rule applied: Node {node_id1} has higher importance ({node1_importance:.2f} > {node2_importance:.2f})")
            return source_id, target_id
            
        if node2_importance > node1_importance:
            # node2 has higher importance (already our assumption)
            self.logger.info(f"Priority rule applied: Node {node_id2} has higher importance ({node2_importance:.2f} > {node1_importance:.2f})")
            return source_id, target_id
            
        # Rule 5: Higher confidence wins
        node1_confidence = node1.get('aggregate_confidence', 0.5)
        node2_confidence = node2.get('aggregate_confidence', 0.5)
        
        if node1_confidence > node2_confidence:
            # node1 has higher confidence, so it should be the target
            source_id, target_id = node_id2, node_id1
            source_node, target_node = node2, node1
            self.logger.info(f"Priority rule applied: Node {node_id1} has higher confidence ({node1_confidence:.2f} > {node2_confidence:.2f})")
            return source_id, target_id
            
        # In all other cases, maintain our original assumption (node1 is source, node2 is target)
        self.logger.info(f"Default merge direction used (no priority rule applied or equal values)")
        return source_id, target_id
    
    def _merge_nodes(self, cbn, source_id, target_id):
        """
        Merge source node into target node and update all related edges.
        
        Args:
            cbn (dict): The current CBN
            source_id (str): ID of the node to merge (will be removed)
            target_id (str): ID of the node to keep
            
        Returns:
            dict: Updated CBN
        """
        # Ensure both nodes exist
        if source_id not in cbn['nodes'] or target_id not in cbn['nodes']:
            self.logger.warning(f"Cannot merge nodes: {source_id} or {target_id} not found")
            return cbn
        
        source_node = cbn['nodes'][source_id]
        target_node = cbn['nodes'][target_id]
        
        # Log detailed merge information including node types
        source_node_type = "regular"
        if source_node.get('is_stance', False):
            source_node_type = "stance"
        elif source_node.get('status') == 'anchor':
            source_node_type = "anchor"
            
        target_node_type = "regular"
        if target_node.get('is_stance', False):
            target_node_type = "stance"
        elif target_node.get('status') == 'anchor':
            target_node_type = "anchor"
        
        self.logger.info(f"Merging node details:")
        self.logger.info(f"  - Source: '{source_node.get('label')}' (type: {source_node_type}, freq: {source_node.get('frequency', 1)}, imp: {source_node.get('importance', 0.5):.2f})")
        self.logger.info(f"  - Target: '{target_node.get('label')}' (type: {target_node_type}, freq: {target_node.get('frequency', 1)}, imp: {target_node.get('importance', 0.5):.2f})")
        
        # Log the merge priority reasoning
        if target_node.get('is_stance', False):
            self.logger.info(f"  - Merge priority: Target is a stance node (highest priority)")
        elif target_node.get('status') == 'anchor' and source_node.get('status') != 'anchor':
            self.logger.info(f"  - Merge priority: Target is an anchor node (high priority)")
        elif target_node.get('frequency', 1) > source_node.get('frequency', 1):
            self.logger.info(f"  - Merge priority: Target has higher frequency ({target_node.get('frequency', 1)} > {source_node.get('frequency', 1)})")
        elif target_node.get('importance', 0.5) > source_node.get('importance', 0.5):
            self.logger.info(f"  - Merge priority: Target has higher importance ({target_node.get('importance', 0.5):.2f} > {source_node.get('importance', 0.5):.2f})")
        elif target_node.get('aggregate_confidence', 0.5) > source_node.get('aggregate_confidence', 0.5):
            self.logger.info(f"  - Merge priority: Target has higher aggregate_confidence ({target_node.get('aggregate_confidence', 0.5):.2f} > {source_node.get('aggregate_confidence', 0.5):.2f})")
        
        # 1. Merge evidence
        if 'evidence' not in target_node:
            target_node['evidence'] = []
        
        evidence_count = 0
        for evidence in source_node.get('evidence', []):
            # Check if this evidence already exists in target
            qa_id = evidence.get('qa_id')
            exists = any(e.get('qa_id') == qa_id for e in target_node['evidence'])
            
            if not exists:
                # Ensure evidence has both confidence and importance values
                if 'confidence' not in evidence:
                    evidence['confidence'] = 0.5
                if 'importance' not in evidence:
                    evidence['importance'] = 0.5
                
                target_node['evidence'].append(evidence)
                evidence_count += 1
        
        self.logger.info(f"  - Merged {evidence_count} evidence items")
        
        # 2. Update frequency
        old_frequency = target_node.get('frequency', 1)
        target_node['frequency'] = old_frequency + source_node.get('frequency', 1)
        self.logger.info(f"  - Updated frequency: {old_frequency} → {target_node['frequency']}")
        
        # 3. Update importance and confidence using the new evidence list
        old_importance = target_node.get('importance', 0.5)
        new_importance = self._calculate_node_importance(target_node.get('evidence', []))
        target_node['importance'] = new_importance
        self.logger.info(f"  - Updated importance (evidence-weighted): {old_importance:.2f} → {new_importance:.2f}")
        
        old_confidence = target_node.get('aggregate_confidence', 0.5)
        new_confidence = self._calculate_node_aggregate_confidence(target_node.get('evidence', []))
        target_node['aggregate_confidence'] = new_confidence
        self.logger.info(f"  - Updated aggregate_confidence (maximum from evidence): {old_confidence:.2f} → {new_confidence:.2f}")
        
        # 4. Redirect all edges connected to the source node
        incoming_count = len(source_node.get('incoming_edges', []))
        outgoing_count = len(source_node.get('outgoing_edges', []))
        self.logger.info(f"  - Redirecting {incoming_count} incoming and {outgoing_count} outgoing edges")
        self._redirect_node_edges(cbn, source_id, target_id)
        
        # 5. Update references in qa_history
        if 'qa_history' in cbn:
            updated_qa_count = 0
            for qa_id, qa_entry in cbn['qa_history'].items():
                # Update node_id in extracted_nodes
                if 'extracted_nodes' in qa_entry:
                    for node_entry in qa_entry['extracted_nodes']:
                        if node_entry.get('node_id') == source_id:
                            node_entry['node_id'] = target_id
                            updated_qa_count += 1
                
                # Update source/target in extracted_pairs
                if 'extracted_pairs' in qa_entry:
                    for pair in qa_entry['extracted_pairs']:
                        if pair.get('source') == source_id:
                            pair['source'] = target_id
                            updated_qa_count += 1
                        if pair.get('target') == source_id:
                            pair['target'] = target_id
                            updated_qa_count += 1
            
            if updated_qa_count > 0:
                self.logger.info(f"  - Updated {updated_qa_count} references in qa_history")
        
        # 6. Remove the source node
        del cbn['nodes'][source_id]
        self.logger.info(f"  - Removed source node {source_id}")
        
        # 7. Update anchor queue if needed
        if 'anchor_queue' in cbn and source_id in cbn['anchor_queue']:
            cbn['anchor_queue'].remove(source_id)
            if target_id not in cbn['anchor_queue']:
                cbn['anchor_queue'].append(target_id)
                self.logger.info(f"  - Updated anchor queue: transferred anchor status to {target_id}")
        
        return cbn
    
    def _redirect_node_edges(self, cbn, old_node_id, new_node_id):
        """
        Redirect all edges connected to old_node_id to connect to new_node_id.
        
        Args:
            cbn (dict): The current CBN
            old_node_id (str): ID of the node being replaced
            new_node_id (str): ID of the node to redirect edges to
        """
        # Get the node objects
        old_node = cbn['nodes'][old_node_id]
        new_node = cbn['nodes'][new_node_id]
        
        # Handle incoming edges
        for edge_id in old_node.get('incoming_edges', []):
            if edge_id in cbn['edges']:
                # Update the edge target
                cbn['edges'][edge_id]['target'] = new_node_id
                # Add to new node's incoming edges if not already there
                if edge_id not in new_node.get('incoming_edges', []):
                    if 'incoming_edges' not in new_node:
                        new_node['incoming_edges'] = []
                    new_node['incoming_edges'].append(edge_id)
        
        # Handle outgoing edges
        for edge_id in old_node.get('outgoing_edges', []):
            if edge_id in cbn['edges']:
                # Update the edge source
                cbn['edges'][edge_id]['source'] = new_node_id
                # Add to new node's outgoing edges if not already there
                if edge_id not in new_node.get('outgoing_edges', []):
                    if 'outgoing_edges' not in new_node:
                        new_node['outgoing_edges'] = []
                    new_node['outgoing_edges'].append(edge_id)
    
    def _merge_duplicate_edges_after_node_merge(self, cbn, target_id):
        """
        Merge any duplicate edges that might have been created after a node merge.
        
        Args:
            cbn (dict): The current CBN
            target_id (str): ID of the merged node
            
        Returns:
            dict: Updated CBN
        """
        # Get the node object
        if target_id not in cbn['nodes']:
            return cbn
            
        target_node = cbn['nodes'][target_id]
        self.logger.info(f"Checking for duplicate edges after merging node {target_id}")
        
        # Create a mapping of (source, target) node pairs to edge IDs
        node_pair_to_edges = {}
        merge_candidates = []
        
        # Check the node's incoming and outgoing edges for duplicates
        for edge_id in target_node.get('incoming_edges', []) + target_node.get('outgoing_edges', []):
            if edge_id not in cbn['edges']:
                continue
                
            edge = cbn['edges'][edge_id]
            source = edge.get('source')
            target = edge.get('target')
            
            if source and target:
                node_pair = (source, target)
                
                if node_pair in node_pair_to_edges:
                    # Found duplicate edge, add to merge candidates
                    existing_edge_id = node_pair_to_edges[node_pair]
                    existing_edge = cbn['edges'][existing_edge_id]
                    
                    # Determine which edge to keep (one with higher confidence or more evidence)
                    existing_conf = existing_edge.get('aggregate_confidence', 0.5)
                    current_conf = edge.get('aggregate_confidence', 0.5)
                    existing_evidence = len(existing_edge.get('evidence', []))
                    current_evidence = len(edge.get('evidence', []))
                    
                    if existing_conf > current_conf or (existing_conf == current_conf and existing_evidence >= current_evidence):
                        source_id, target_id = edge_id, existing_edge_id
                    else:
                        source_id, target_id = existing_edge_id, edge_id
                        # Update the mapping
                        node_pair_to_edges[node_pair] = edge_id
                    
                    merge_candidates.append((source_id, target_id))
                else:
                    # First time seeing this node pair
                    node_pair_to_edges[node_pair] = edge_id
        
        # Apply edge merges
        if merge_candidates:
            llm_logger.log_separator("EDGE MERGING - EXECUTION PHASE")
            merge_count = 0
            for source_id, target_id in merge_candidates:
                # Skip if either edge no longer exists
                if source_id not in cbn['edges'] or target_id not in cbn['edges']:
                    self.logger.info(f"Skipping merge: edge {source_id} or {target_id} no longer exists")
                    continue
                
                source_edge = cbn['edges'][source_id]
                target_edge = cbn['edges'][target_id]
                source_node = cbn['nodes'].get(source_edge.get('source', ''), {}).get('label', 'unknown')
                target_node = cbn['nodes'].get(source_edge.get('target', ''), {}).get('label', 'unknown')
                
                self.logger.info(f"Merging edge {source_id} into {target_id} ({source_node} → {target_node})")
                
                # Perform the merge
                cbn = self._merge_edges(cbn, source_id, target_id)
                merge_count += 1
            
            self.logger.info(f"Successfully merged {merge_count} edges")
        else:
            self.logger.info("No duplicate edges found after node merge")
        
        return cbn
    
    def _merge_edges(self, cbn, source_id, target_id):
        """
        Merge source edge into target edge.
        
        Args:
            cbn (dict): The current CBN
            source_id (str): ID of the edge to merge (will be removed)
            target_id (str): ID of the edge to keep
            
        Returns:
            dict: Updated CBN
        """
        # Ensure both edges exist
        if source_id not in cbn['edges'] or target_id not in cbn['edges']:
            self.logger.warning(f"Cannot merge edges: {source_id} or {target_id} not found")
            return cbn
        
        source_edge = cbn['edges'][source_id]
        target_edge = cbn['edges'][target_id]
        
        source_node_id = source_edge.get('source', '')
        target_node_id = source_edge.get('target', '')
        source_node_label = cbn['nodes'].get(source_node_id, {}).get('label', 'unknown')
        target_node_label = cbn['nodes'].get(target_node_id, {}).get('label', 'unknown')
        
        self.logger.info(f"Merging edge details:")
        self.logger.info(f"  - Connection: {source_node_label} → {target_node_label}")
        self.logger.info(f"  - Source edge: {source_id} (aggregate_conf: {source_edge.get('aggregate_confidence', 0.5):.2f}, mod: {source_edge.get('modifier', 0):.2f})")
        self.logger.info(f"  - Target edge: {target_id} (aggregate_conf: {target_edge.get('aggregate_confidence', 0.5):.2f}, mod: {target_edge.get('modifier', 0):.2f})")
        
        # 1. Merge evidence
        if 'evidence' not in target_edge:
            target_edge['evidence'] = []
        
        evidence_count = 0
        for evidence in source_edge.get('evidence', []):
            # Check if this evidence already exists in target
            qa_id = evidence.get('qa_id')
            exists = any(e.get('qa_id') == qa_id for e in target_edge['evidence'])
            
            if not exists:
                # Ensure evidence has confidence and original_modifier fields
                if 'confidence' not in evidence:
                    evidence['confidence'] = 0.5
                if 'original_modifier' not in evidence:
                    evidence['original_modifier'] = 1.0
                
                target_edge['evidence'].append(evidence)
                evidence_count += 1
        
        self.logger.info(f"  - Merged {evidence_count} evidence items")
        
        # 2. Recalculate aggregate confidence and modifier
        old_confidence = target_edge.get('aggregate_confidence', 0.5)
        new_confidence = self._calculate_aggregate_confidence(target_edge.get('evidence', []))
        target_edge['aggregate_confidence'] = new_confidence
        
        old_modifier = target_edge.get('modifier', 0)
        new_modifier = self._calculate_aggregate_modifier(target_edge.get('evidence', []))
        target_edge['modifier'] = new_modifier
        
        # Calculate direction and strength from modifier
        target_edge['direction'] = 'positive' if new_modifier >= 0 else 'negative'
        target_edge['strength'] = abs(new_modifier)
        
        self.logger.info(f"  - Updated aggregate_confidence: {old_confidence:.2f} → {new_confidence:.2f}")
        self.logger.info(f"  - Updated modifier: {old_modifier:.2f} → {new_modifier:.2f}")
        self.logger.info(f"  - Updated direction: {target_edge['direction']}, strength: {target_edge['strength']:.2f}")
        
        # 3. Merge explanation - prefer target's if it exists, otherwise use source's
        if not target_edge.get('explanation') and source_edge.get('explanation'):
            target_edge['explanation'] = source_edge.get('explanation')
            self.logger.info(f"  - Updated explanation from source edge")
        
        # 4. Update any other edge properties
        # Keep current labels unless they're empty
        if not target_edge.get('source_label') and source_edge.get('source_label'):
            target_edge['source_label'] = source_edge['source_label']
            self.logger.info(f"  - Updated source label to: '{source_edge['source_label']}'")
        
        if not target_edge.get('target_label') and source_edge.get('target_label'):
            target_edge['target_label'] = source_edge['target_label']
            self.logger.info(f"  - Updated target label to: '{source_edge['target_label']}'")
        
        # 5. Update node references to remove the source edge and keep the target edge
        if source_node_id in cbn['nodes'] and source_id in cbn['nodes'][source_node_id].get('outgoing_edges', []):
            cbn['nodes'][source_node_id]['outgoing_edges'].remove(source_id)
            self.logger.info(f"  - Removed outgoing edge reference from source node")
        
        if target_node_id in cbn['nodes'] and source_id in cbn['nodes'][target_node_id].get('incoming_edges', []):
            cbn['nodes'][target_node_id]['incoming_edges'].remove(source_id)
            self.logger.info(f"  - Removed incoming edge reference from target node")
        
        # 6. Remove the source edge
        del cbn['edges'][source_id]
        self.logger.info(f"  - Removed source edge {source_id}")
        
        return cbn
    
    def update_function_params(self, cbn, edge_id, function_params):
        """
        Update function parameters for an edge.
        
        Args:
            cbn (dict): The existing CBN
            edge_id (str): ID of the edge to update
            function_params (dict): New function parameters
            
        Returns:
            dict: Updated CBN
        """
        # Ensure edge exists
        if 'edges' not in cbn or edge_id not in cbn['edges']:
            return cbn
        
        edge = cbn['edges'][edge_id]
        
        # Update confidence if provided
        if 'aggregate_confidence' in function_params:
            # Update evidence for this edge with the new confidence
            new_confidence = function_params.get('aggregate_confidence', 0.7)
            
            # If we have evidence, update the most recent one
            if edge['evidence']:
                current_modifier = edge['evidence'][-1].get('original_modifier', 1.0)
                edge['evidence'][-1]['confidence'] = new_confidence
                
                # Recalculate aggregate confidence
                edge['aggregate_confidence'] = self._calculate_aggregate_confidence(edge['evidence'])
                
                # Recalculate aggregate modifier
                edge['modifier'] = self._calculate_aggregate_modifier(edge['evidence'])
        
        return cbn
    
    def add_qa_to_graph(self, cbn, qa_pair, parsed_belief=None, extracted_nodes=None, edge_id=None):
        """
        Add a QA pair to the CBN graph.
        
        Args:
            cbn (dict): The existing CBN
            qa_pair (dict): QA pair to add
            parsed_belief (dict, optional): Deprecated, kept for parameter compatibility only
            extracted_nodes (dict, optional): Dictionary of extracted nodes with aggregate_confidence
            edge_id (str, optional): Edge ID if an edge was created/updated directly
            
        Returns:
            dict: Updated CBN
        """
        # Ensure qa_history structure exists
        if 'qa_history' not in cbn:
            cbn['qa_history'] = {}
        
        # Get the QA ID directly from the qa_pair
        # We now expect a simple format like 'qa1', 'qa2', etc.
        qa_id = qa_pair.get('id')
        if not qa_id or not isinstance(qa_id, str):
            # Fallback - generate sequential ID based on existing QA count
            qa_counter = len(cbn['qa_history']) + 1
            qa_id = f"qa{qa_counter}"
        
        # Extract edge information for QA history
        extracted_pairs = []
        
        # If we have a direct edge_id, use that
        if edge_id and edge_id in cbn.get('edges', {}):
            edge = cbn['edges'][edge_id]
            source_node_id = edge.get('source')
            target_node_id = edge.get('target')
            
            if source_node_id and target_node_id:
                # Get source and target labels
                source_label = edge.get('source_label', '')
                target_label = edge.get('target_label', '')
                
                if not source_label and source_node_id in cbn['nodes']:
                    source_label = cbn['nodes'][source_node_id].get('label', '')
                    
                if not target_label and target_node_id in cbn['nodes']:
                    target_label = cbn['nodes'][target_node_id].get('label', '')
                
                # Get confidence and modifier from edge
                confidence = edge.get('aggregate_confidence', 0.7)
                modifier = edge.get('modifier', 0.7)
                # Calculate direction from modifier
                direction = 'positive' if modifier >= 0 else 'negative'
                
                # Add extracted pair with edge information
                extracted_pairs.append({
                    "edge_id": edge_id,
                    "source": source_node_id,
                    "target": target_node_id,
                    "source_label": source_label,
                    "target_label": target_label,
                    "confidence": confidence,
                    "modifier": modifier,
                    "direction": direction
                })
                
                # Update the edge's evidence with this QA
                if 'evidence' not in edge:
                    edge['evidence'] = []
                    
                # Check if this QA is already in evidence
                qa_exists = any(e.get('qa_id') == qa_id for e in edge['evidence'])
                if not qa_exists:
                    # Add new evidence entry for this QA
                    edge['evidence'].append({
                        "qa_id": qa_id,
                        "confidence": confidence,
                        "original_modifier": modifier / max(confidence, 0.01)  # Recover original modifier
                    })
                    
                    # Recalculate aggregate values
                    edge['aggregate_confidence'] = self._calculate_aggregate_confidence(edge['evidence'])
                    edge['modifier'] = self._calculate_aggregate_modifier(edge['evidence'])
                    
                    self.logger.info(f"Added evidence for QA {qa_id} to edge {edge_id}")
                
                self.logger.info(f"Recorded edge in QA history: {source_label} → {target_label} ({direction}, aggregate_conf: {confidence:.2f})")
        
        # Prepare extracted_nodes list for QA history and update node evidence
        node_entries = []
        if extracted_nodes:
            for node_id, node_data in extracted_nodes.items():
                # First update node entry for QA history
                node_entry = {
                    "node_id": node_id,
                    "label": node_data.get('label', ''),
                    "confidence": node_data.get('aggregate_confidence', 0.5),
                    "importance": node_data.get('importance', 0.5),
                    "status": cbn['nodes'].get(node_id, {}).get('status', 'candidate')
                }
                node_entries.append(node_entry)
                
                # Then update the node's evidence with this QA
                if node_id in cbn['nodes']:
                    node = cbn['nodes'][node_id]
                    
                    # Initialize evidence array if not exists
                    if 'evidence' not in node:
                        node['evidence'] = []
                    
                    # Check if this QA is already in evidence
                    qa_exists = any(e.get('qa_id') == qa_id for e in node['evidence'])
                    if not qa_exists:
                        # Add new evidence entry for this QA
                        node_confidence = node_data.get('aggregate_confidence', 0.5)
                        node_importance = node_data.get('importance', 0.5)
                        
                        node['evidence'].append({
                            "qa_id": qa_id,
                            "confidence": node_confidence,
                            "importance": node_importance
                        })
                        
                        # Increment frequency counter (replacing source_qa counting)
                        node['frequency'] = node.get('frequency', 0) + 1
                        
                        # Recalculate aggregate values
                        node['aggregate_confidence'] = self._calculate_node_aggregate_confidence(node['evidence'])
                        node['importance'] = self._calculate_node_importance(node['evidence'])
                        
                        self.logger.info(f"Added evidence for QA {qa_id} to node {node_id}")
        
        # Create QA entry in CBN format
        qa_entry = {
            "question": qa_pair.get('question', ''),
            "answer": qa_pair.get('answer', ''),
            "extracted_pairs": extracted_pairs,
            "extracted_nodes": node_entries
        }
        
        # Add/update QA in qa_history
        cbn['qa_history'][qa_id] = qa_entry
        self.logger.info(f"Added QA entry with ID {qa_id} to qa_history")
        
        return cbn
    
    def check_termination(self, cbn):
        """
        Check if the interview should be terminated based on CBN state.
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            bool: True if the interview should be terminated, False otherwise
        """
        # Check the number of QA pairs
        qa_count = len(cbn.get('qa_history', {}))
        if qa_count >= self.max_qa_count:
            self.logger.info(f"QA count threshold reached: {qa_count} >= {self.max_qa_count}")
            self.terminate_interview = True
            return self.terminate_interview

        # Check for structural convergence
        structure_converged = self._check_structure_convergence(cbn)
        
        # Check for information gain saturation
        info_gain_saturated = self._check_info_gain_saturation(cbn)
        
        # Check for redundancy saturation
        redundancy_saturated = self._check_redundancy_saturation(cbn)
        
        # Terminate if all conditions are met
        if structure_converged and info_gain_saturated and redundancy_saturated:
            self.terminate_interview = True
        
        return self.terminate_interview
    
    def get_next_step(self, cbn):
        """
        Determine the next step based on the current CBN state.
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            int: The step to transition to (1 or 2)
        """
        # Update our local anchor queue from the CBN
        if 'anchor_queue' in cbn:
            self.anchor_queue = cbn['anchor_queue']
        
        # If we're in Step 1 and have enough anchor nodes, move to Step 2
        if self.current_step == 1 and len(self.anchor_queue) >= 5:  # Changed from 3 to 5
            self.current_step = 2
            self.logger.info(f"Transitioning from Step 1 to Step 2 (anchor count: {len(self.anchor_queue)})")
        
        # Once in Step 2, we stay in Step 2 (remove the condition to go back to Step 1)
        
        return self.current_step
    
    def _calculate_aggregate_confidence(self, evidence_list):
        """
        Calculate aggregate confidence from a list of evidence.
        Takes the average confidence from all evidence.
        
        Args:
            evidence_list (list): List of evidence entries
            
        Returns:
            float: Aggregate confidence (0.0-1.0)
        """
        if not evidence_list:
            return 0.0
        
        # Calculate average confidence from evidence
        total_confidence = sum(e['confidence'] for e in evidence_list)
        return total_confidence / len(evidence_list)
        
    def _calculate_aggregate_modifier(self, evidence_list):
        """
        Calculate aggregate modifier from evidence list.
        Uses weighted average based on confidence.
        
        Args:
            evidence_list (list): List of evidence entries
            
        Returns:
            float: Aggregate modifier (-1.0 to 1.0)
        """
        if not evidence_list:
            return 0.0
        
        # Get all modifiers weighted by confidence
        weighted_mods = []
        total_confidence = 0.0
        
        for evidence in evidence_list:
            confidence = evidence.get('confidence', 0.5)
            orig_mod = evidence.get('original_modifier', 1.0)
            weighted_mods.append((orig_mod * confidence, confidence))
            total_confidence += confidence
        
        # Calculate weighted average of modifiers
        if total_confidence > 0:
            return sum(mod_weight[0] for mod_weight in weighted_mods) / total_confidence
        else:
            return 0.0
    
    def _calculate_node_aggregate_confidence(self, evidence_list):
        """
        Calculate aggregate confidence for a node from evidence.
        Takes the average confidence from all evidence.
        
        Args:
            evidence_list (list): List of evidence entries
            
        Returns:
            float: Aggregate confidence (0.0-1.0)
        """
        if not evidence_list:
            return 0.5  # Default confidence if no evidence
        
        # Calculate average confidence from evidence
        total_confidence = sum(e.get('confidence', 0.5) for e in evidence_list)
        return total_confidence / len(evidence_list)
    
    def _calculate_node_importance(self, evidence_list):
        """
        Calculate aggregate importance for a node from evidence.
        Uses weighted average based on evidence confidence.
        
        Args:
            evidence_list (list): List of evidence entries
            
        Returns:
            float: Aggregate importance (0.0-1.0)
        """
        if not evidence_list:
            return 0.5  # Default importance
            
        # Calculate weighted average of importance based on confidence
        total_confidence = 0.0
        weighted_sum = 0.0
        
        for evidence in evidence_list:
            confidence = evidence.get('confidence', 0.5)
            importance = evidence.get('importance', 0.5)
            weighted_sum += importance * confidence
            total_confidence += confidence
        
        if total_confidence > 0:
            return weighted_sum / total_confidence
        else:
            # If no weights, use average importance
            return sum(e.get('importance', 0.5) for e in evidence_list) / len(evidence_list)
    
    def _check_node_promotion(self, cbn):
        """
        Check if any nodes should be promoted to anchors.
        
        Args:
            cbn (dict): The current CBN
        """
        # Update our local anchor queue from CBN
        if 'anchor_queue' in cbn:
            self.anchor_queue = cbn['anchor_queue']
        
        for node_id, node in cbn['nodes'].items():
            # Skip nodes that are already anchors
            if node.get('status') == 'anchor':
                continue
                
            # Skip nodes that don't have candidate status (ensure nodes go through candidate stage)
            if node.get('status') != 'candidate':
                continue
                
            # Check if node should be promoted based on frequency, importance, confidence, or edge connections
            frequency = node.get('frequency', 1)
            importance = node.get('importance', 0.5)
            confidence = node.get('aggregate_confidence', 0.5)
            connection_count = len(node.get('incoming_edges', [])) + len(node.get('outgoing_edges', []))
            
            # Add detailed logging about node promotion criteria
            self.logger.info(f"Checking promotion criteria for node: {node_id}")
            self.logger.info(f"  - frequency: {frequency}, importance: {importance}, confidence: {confidence}, connection_count: {connection_count}")
            self.logger.info(f"  - current anchor queue: {self.anchor_queue}, max anchors: {self.max_anchors}")
            
            # Promote to anchor if meets any of these criteria:
            # 1. Appears in multiple QAs (frequency >= 2)
            # 2. Has high importance (> 0.8)
            # 3. Has high confidence (> 0.8)
            # 4. Has connections to other nodes (> 1)
            # 5. Maximum anchors not exceeded
            if ((frequency >= 2 or (importance > 0.85 and confidence > 0.85) or connection_count > 0) and
                node_id not in self.anchor_queue and
                len(self.anchor_queue) < self.max_anchors):
                
                # Log which condition passed
                if frequency >= 2:
                    self.logger.info(f"  - Node {node_id} promoted to anchor due to frequency >= 2")
                elif importance > 0.85 and confidence > 0.85:
                    self.logger.info(f"  - Node {node_id} promoted to anchor due to high importance and confidence")
                elif connection_count > 0:
                    self.logger.info(f"  - Node {node_id} promoted to anchor due to having connections")
                
                # Promote to anchor
                node['status'] = 'anchor'
                self.anchor_queue.append(node_id)
                if 'anchor_queue' in cbn:
                    cbn['anchor_queue'] = self.anchor_queue
    
    def _check_structure_convergence(self, cbn):
        """
        Check if the structure has converged (no new meaningful changes).
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            bool: True if structure has converged, False otherwise
        """
        # Count candidate nodes
        candidate_count = sum(1 for node in cbn['nodes'].values() if node.get('status') == 'candidate')
        
        # Simple check: No candidate nodes and enough stable rounds
        if candidate_count == 0 and self.stable_rounds >= 3:
            return True
        
        # If there are still candidates, structure hasn't converged
        if candidate_count > 0:
            self.stable_rounds = 0
            return False
        
        # Increment stable rounds counter if no candidates
        self.stable_rounds += 1
        return False
    
    def _check_info_gain_saturation(self, cbn):
        """
        Check if information gain has saturated.
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            bool: True if information gain has saturated, False otherwise
        """
        # Simplified check: All anchor nodes have multiple edges
        for node_id in self.anchor_queue:
            if node_id in cbn['nodes']:
                node = cbn['nodes'][node_id]
                edge_count = len(node.get('incoming_edges', [])) + len(node.get('outgoing_edges', []))
                if edge_count < 2:
                    return False
        
        # If all anchor nodes have multiple edges, info gain has saturated
        return len(self.anchor_queue) > 0
    
    def _check_redundancy_saturation(self, cbn):
        """
        Check if redundancy has saturated (no new unique information being added).
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            bool: True if redundancy has saturated, False otherwise
        """
        # Simplified: Check if all anchors have been fully expanded
        return self._all_anchors_expanded(cbn)
    
    def _all_anchors_expanded(self, cbn):
        """
        Check if all anchor nodes have been fully expanded.
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            bool: True if all anchors have been fully expanded, False otherwise
        """
        for node_id in self.anchor_queue:
            if node_id in cbn['nodes']:
                node = cbn['nodes'][node_id]
                # An anchor is fully expanded if it has connections to at least 3 other nodes
                total_connections = len(node.get('incoming_edges', [])) + len(node.get('outgoing_edges', []))
                if total_connections < 3:
                    return False
        
        # If we have no anchors, consider them "all expanded"
        return len(self.anchor_queue) > 0 