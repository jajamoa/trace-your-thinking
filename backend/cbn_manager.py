"""
CBN Manager Module
Responsible for managing the Causal Belief Network graph, including node merging, edge updates, etc.
"""
import uuid
import time
import json
from collections import defaultdict
import logging


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
        self.max_anchors = 7  # Based on Miller's Law (7±2 chunks)
        # Initialize logger
        self.logger = logging.getLogger(__name__)
    
    def merge_and_tag_nodes(self, cbn, new_nodes):
        """
        Merge new nodes into the existing CBN and tag them appropriately.
        
        Args:
            cbn (dict): The existing CBN
            new_nodes (dict): New nodes to merge
            
        Returns:
            dict: Updated CBN
        """
        # Ensure required structures exist
        if 'nodes' not in cbn:
            cbn['nodes'] = {}
        
        # Process each new node
        for node_id, node_data in new_nodes.items():
            # Check if this node is similar to any existing node
            similar_node = self._find_similar_node(cbn['nodes'], node_data)
            
            if similar_node:
                # Update the existing node with new information
                self._update_existing_node(cbn['nodes'][similar_node], node_data)
            else:
                # Get QA ID from source
                qa_id = node_data.get('source_qa', ['unknown_qa_id'])[0]
                
                # Create evidence entry
                evidence_entry = {
                    "qa_id": qa_id,
                    "confidence": node_data.get('confidence', 0.5),
                    "importance": node_data.get('importance', 0.5)
                }
                
                # Create and add the new node with evidence structure
                cbn['nodes'][node_id] = {
                    "label": node_data.get('label', ''),
                    "aggregate_confidence": node_data.get('confidence', 0.5),
                    "evidence": [evidence_entry],
                    "incoming_edges": [],
                    "outgoing_edges": [],
                    "importance": node_data.get('importance', 0.5),  # Keep top-level importance for quick access
                    "status": "candidate",  # Default to candidate status
                    "frequency": 1  # Initialize frequency counter
                }
        
        # Check if any nodes should be promoted to anchors
        self._check_node_promotion(cbn)
        
        return cbn
    
    def add_or_update_edge(self, cbn, edge_data):
        """
        Add a new edge or update an existing edge in the CBN.
        
        Args:
            cbn (dict): The existing CBN
            edge_data (dict): Edge data to add/update
            
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
        
        # Check if an edge already exists between these nodes
        existing_edge_id = None
        for edge_id, edge in cbn['edges'].items():
            if edge['source'] == from_node_id and edge['target'] == to_node_id:
                existing_edge_id = edge_id
                break
        
        # Get confidence from edge data (default 0.7)
        confidence = edge_data.get('confidence', 0.7)
        
        # Calculate modifier based on direction (-1.0 to 1.0)
        # positive direction = positive modifier, negative direction = negative modifier
        modifier = 1.0
        if edge_data.get('direction', 'positive') == 'negative':
            modifier = -1.0
            
        # Scale by confidence to get [-confidence, +confidence]
        adjusted_modifier = modifier * confidence
        
        # Create evidence entry
        evidence_entry = {
            "qa_id": edge_data.get('source_qa', 'unknown_qa_id'),
            "confidence": confidence,
            "original_modifier": modifier
        }
        
        if existing_edge_id:
            # Update existing edge
            edge = cbn['edges'][existing_edge_id]
            
            # Add evidence if not already present
            evidence_exists = False
            for evidence in edge.get('evidence', []):
                if evidence['qa_id'] == edge_data.get('source_qa', 'unknown_qa_id'):
                    # Update evidence with new values
                    evidence['confidence'] = confidence
                    evidence['original_modifier'] = modifier
                    evidence_exists = True
                    break
            
            if not evidence_exists:
                # Add new evidence
                if 'evidence' not in edge:
                    edge['evidence'] = []
                edge['evidence'].append(evidence_entry)
            
            # Recalculate aggregate confidence
            edge['aggregate_confidence'] = self._calculate_aggregate_confidence(edge['evidence'])
            # Recalculate modifier
            edge['modifier'] = self._calculate_aggregate_modifier(edge['evidence'])
            
            # Cache labels for convenience
            edge['source_label'] = edge_data.get('from_label', edge.get('source_label', ''))
            edge['target_label'] = edge_data.get('to_label', edge.get('target_label', ''))
        else:
            # Create a new edge with sequential ID
            if 'edge_counter' not in cbn:
                cbn['edge_counter'] = 0
            
            cbn['edge_counter'] += 1
            edge_id = f"e{cbn['edge_counter']}"
            
            # Create edge structure with evidence
            cbn['edges'][edge_id] = {
                "source": from_node_id,
                "target": to_node_id,
                "aggregate_confidence": confidence,
                "evidence": [evidence_entry],
                "modifier": adjusted_modifier,
                "source_label": edge_data.get('from_label', ''),
                "target_label": edge_data.get('to_label', '')
            }
            
            # Update node references
            cbn['nodes'][from_node_id]['outgoing_edges'].append(edge_id)
            cbn['nodes'][to_node_id]['incoming_edges'].append(edge_id)
        
        return cbn, edge_id
    
    def _calculate_aggregate_confidence(self, evidence_list):
        """
        Calculate aggregate confidence from a list of evidence.
        
        Args:
            evidence_list (list): List of evidence entries
            
        Returns:
            float: Aggregate confidence (0.0-1.0)
        """
        if not evidence_list:
            return 0.0
            
        # Simple approach: use the maximum confidence from evidence
        return max(e['confidence'] for e in evidence_list)
    
    def _calculate_aggregate_modifier(self, evidence_list):
        """
        Calculate aggregate modifier from evidence list.
        
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
        if 'confidence' in function_params:
            # Update evidence for this edge with the new confidence
            new_confidence = function_params.get('confidence', 0.7)
            
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
            parsed_belief (dict, optional): Parsed belief from the QA pair
            extracted_nodes (dict, optional): Dictionary of extracted nodes with confidence
            edge_id (str, optional): Edge ID if an edge was created/updated
            
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
        
        # Extract source and target node IDs if we have a parsed belief
        extracted_pairs = []
        if parsed_belief and 'belief_structure' in parsed_belief and edge_id:
            belief_structure = parsed_belief.get('belief_structure', {})
            source_node_id = belief_structure.get('from')
            target_node_id = belief_structure.get('to')
            
            if source_node_id and target_node_id:
                # Get the edge details
                edge = cbn['edges'].get(edge_id, {})
                source_label = edge.get('source_label', '')
                target_label = edge.get('target_label', '')
                
                if not source_label and source_node_id in cbn['nodes']:
                    source_label = cbn['nodes'][source_node_id].get('label', '')
                    
                if not target_label and target_node_id in cbn['nodes']:
                    target_label = cbn['nodes'][target_node_id].get('label', '')
                
                # Get confidence from belief strength
                confidence = parsed_belief.get('belief_strength', {}).get('estimated_probability', 0.5)
                # Get direction from belief structure
                direction = belief_structure.get('direction', 'positive')
                # Calculate modifier
                modifier = 1.0 if direction == 'positive' else -1.0
                
                # Add extracted pair with edge_id and labels
                extracted_pairs.append({
                    "edge_id": edge_id,
                    "source": source_node_id,
                    "target": target_node_id,
                    "source_label": source_label,
                    "target_label": target_label,
                    "confidence": confidence,
                    "modifier": modifier * confidence
                })
        
        # Prepare extracted_nodes list for QA history
        node_entries = []
        if extracted_nodes:
            for node_id, node in extracted_nodes.items():
                node_entry = {
                    "node_id": node_id,
                    "label": node.get('label', ''),
                    "confidence": node.get('confidence', 0.5),
                    "importance": node.get('importance', 0.5),
                    "status": cbn['nodes'].get(node_id, {}).get('status', 'candidate')
                }
                node_entries.append(node_entry)
        
        # Create QA entry in CBN format
        qa_entry = {
            "question": qa_pair.get('question', ''),
            "answer": qa_pair.get('answer', ''),
            "extracted_pairs": extracted_pairs,
            "extracted_nodes": node_entries
        }
        
        # Add/update QA in qa_history
        cbn['qa_history'][qa_id] = qa_entry
        
        return cbn
    
    def check_termination(self, cbn):
        """
        Check if the interview should be terminated based on CBN state.
        
        Args:
            cbn (dict): The current CBN
            
        Returns:
            bool: True if the interview should be terminated, False otherwise
        """
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
        if self.current_step == 1 and len(self.anchor_queue) >= 3:
            self.current_step = 2
        
        # If we're in Step 2 and new nodes have been discovered recently, consider going back to Step 1
        elif self.current_step == 2:
            # Count new candidate nodes
            candidate_count = sum(1 for node in cbn['nodes'].values() if node.get('status') == 'candidate')
            if candidate_count > 3:
                self.current_step = 1
        
        return self.current_step
    
    def _find_similar_node(self, existing_nodes, new_node):
        """
        Find a node in the existing nodes that is similar to the new node.
        
        Args:
            existing_nodes (dict): Existing nodes
            new_node (dict): New node to check
            
        Returns:
            str or None: ID of similar node, or None if no similar node found
        """
        # Simple similarity check based on label (real implementation would use embeddings)
        new_label = new_node['label'].lower()
        
        for node_id, node in existing_nodes.items():
            if node['label'].lower() == new_label:
                return node_id
        
        return None
    
    def _update_existing_node(self, existing_node, new_node):
        """
        Update an existing node with information from a new node.
        
        Args:
            existing_node (dict): Existing node to update
            new_node (dict): New node with updated information
        """
        # Get QA ID from new node
        qa_ids = new_node.get('source_qa', ['unknown_qa_id'])
        qa_id = qa_ids[0] if qa_ids else 'unknown_qa_id'
        
        # Create new evidence entry
        new_evidence = {
            "qa_id": qa_id,
            "confidence": new_node.get('confidence', 0.5),
            "importance": new_node.get('importance', 0.5)
        }
        
        # Initialize evidence if it doesn't exist
        if 'evidence' not in existing_node:
            existing_node['evidence'] = []
        
        # Check if we already have evidence for this QA
        evidence_exists = False
        for evidence in existing_node['evidence']:
            if evidence['qa_id'] == qa_id:
                # Update if new evidence has higher confidence or importance
                if new_node.get('confidence', 0) > evidence.get('confidence', 0):
                    evidence['confidence'] = new_node['confidence']
                if new_node.get('importance', 0) > evidence.get('importance', 0):
                    evidence['importance'] = new_node['importance']
                evidence_exists = True
                break
        
        # Add new evidence if not already present
        if not evidence_exists:
            existing_node['evidence'].append(new_evidence)
        
        # Update aggregate confidence from evidence
        existing_node['aggregate_confidence'] = self._calculate_node_aggregate_confidence(existing_node['evidence'])
        
        # Update importance if the new importance is higher
        existing_importance = existing_node.get('importance', 0.5)
        new_importance = new_node.get('importance', 0.5)
        existing_node['importance'] = max(existing_importance, new_importance)
        
        # Increment frequency counter
        existing_node['frequency'] = existing_node.get('frequency', 1) + 1
        
        # Add to source QAs if not already present
        if qa_id not in existing_node.get('source_qa', []):
            if 'source_qa' not in existing_node:
                existing_node['source_qa'] = []
            existing_node['source_qa'].append(qa_id)
    
    def _calculate_node_aggregate_confidence(self, evidence_list):
        """
        Calculate aggregate confidence for a node from evidence.
        
        Args:
            evidence_list (list): List of evidence entries
            
        Returns:
            float: Aggregate confidence (0.0-1.0)
        """
        if not evidence_list:
            return 0.0
            
        # Calculate weighted average based on importance
        total_weight = 0.0
        weighted_sum = 0.0
        
        for evidence in evidence_list:
            importance = evidence.get('importance', 0.5)
            confidence = evidence.get('confidence', 0.5)
            weighted_sum += importance * confidence
            total_weight += importance
        
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            # If no weights, use max confidence
            return max(e.get('confidence', 0) for e in evidence_list)
    
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