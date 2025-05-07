"""
SCM Manager Module
Responsible for managing the Structural Causal Model graph, including node merging, edge updates, etc.
"""
import uuid
import time
import json
from collections import defaultdict


class SCMManager:
    """
    Manage the Structural Causal Model (SCM) graph, including node merging, edge updates, etc.
    """
    
    def __init__(self):
        """Initialize the SCM manager"""
        # Track node candidate queue
        self.node_candidate_queue = []
        # Track anchor queue
        self.anchor_queue = []
        # Track node synonyms/clusters
        self.node_clusters = defaultdict(list)
        # Track current phase
        self.current_phase = 1  # Start with Phase 1: Node Discovery
        # Track whether the interview has terminated
        self.terminate_interview = False
        # Track stable rounds for convergence
        self.stable_rounds = 0
        # Maximum allowed anchors
        self.max_anchors = 7  # Based on Miller's Law (7±2 chunks)
    
    def merge_and_tag_nodes(self, agent_scm, new_nodes):
        """
        Merge new nodes into the existing SCM and tag them appropriately.
        
        Args:
            agent_scm (dict): The existing SCM
            new_nodes (dict): New nodes to merge
            
        Returns:
            dict: Updated SCM
        """
        # Ensure required structures exist
        if 'nodes' not in agent_scm:
            agent_scm['nodes'] = {}
        
        # Process each new node
        for node_id, node_data in new_nodes.items():
            # Check if this node is similar to any existing node
            similar_node = self._find_similar_node(agent_scm['nodes'], node_data)
            
            if similar_node:
                # Update the existing node with new information
                self._update_existing_node(agent_scm['nodes'][similar_node], node_data)
            else:
                # Add the new node to the SCM
                agent_scm['nodes'][node_id] = node_data
                
                # Add to candidate queue if it's a new node
                if node_data['status'] == 'proposed':
                    self.node_candidate_queue.append(node_id)
        
        # Check if any nodes should be promoted to anchors
        self._check_node_promotion(agent_scm)
        
        return agent_scm
    
    def add_or_update_edge(self, agent_scm, edge_data):
        """
        Add a new edge or update an existing edge in the SCM.
        
        Args:
            agent_scm (dict): The existing SCM
            edge_data (dict): Edge data to add/update
            
        Returns:
            dict: Updated SCM with new/updated edge
        """
        # Ensure required structures exist
        if 'edges' not in agent_scm:
            agent_scm['edges'] = {}
        if 'nodes' not in agent_scm:
            agent_scm['nodes'] = {}
        
        # Find the nodes corresponding to the from/to labels
        from_node_id = None
        to_node_id = None
        
        # Try to find nodes by label
        for node_id, node in agent_scm['nodes'].items():
            if node['label'].lower() == edge_data['from_label'].lower():
                from_node_id = node_id
            if node['label'].lower() == edge_data['to_label'].lower():
                to_node_id = node_id
        
        # If nodes don't exist, we can't create the edge
        if not from_node_id or not to_node_id:
            return agent_scm
        
        # Check if an edge already exists between these nodes
        existing_edge_id = None
        for edge_id, edge in agent_scm['edges'].items():
            if edge['from'] == from_node_id and edge['to'] == to_node_id:
                existing_edge_id = edge_id
                break
        
        if existing_edge_id:
            # Update the existing edge
            edge = agent_scm['edges'][existing_edge_id]
            
            # Add support QA if not already present
            for qa_id in edge_data.get('support_qas', []):
                if qa_id not in edge['support_qas']:
                    edge['support_qas'].append(qa_id)
            
            # Update confidence if new confidence is higher
            if edge_data.get('confidence', 0) > edge.get('confidence', 0):
                edge['confidence'] = edge_data['confidence']
            
            # Update function type if provided
            if 'function_type' in edge_data:
                edge['function']['function_type'] = edge_data['function_type']
        else:
            # Create a new edge
            edge_id = f"e_{uuid.uuid4().hex[:8]}"
            
            # Create function based on edge data
            function = {
                "target": to_node_id,
                "inputs": [from_node_id],
                "function_type": edge_data.get('function_type', 'sigmoid'),
                "parameters": {
                    "weights": [0.7],  # Default weight
                    "bias": 0.2  # Default bias
                },
                "noise_std": 0.1,
                "support_qas": edge_data.get('support_qas', []),
                "confidence": edge_data.get('confidence', 0.7)
            }
            
            # Create the new edge
            agent_scm['edges'][edge_id] = {
                "from": from_node_id,
                "to": to_node_id,
                "function": function,
                "support_qas": edge_data.get('support_qas', [])
            }
            
            # Update node references
            agent_scm['nodes'][from_node_id]['outgoing_edges'].append(edge_id)
            agent_scm['nodes'][to_node_id]['incoming_edges'].append(edge_id)
        
        return agent_scm
    
    def update_function_params(self, agent_scm, edge_id, function_params):
        """
        Update function parameters for an edge.
        
        Args:
            agent_scm (dict): The existing SCM
            edge_id (str): ID of the edge to update
            function_params (dict): New function parameters
            
        Returns:
            dict: Updated SCM
        """
        # Ensure edge exists
        if 'edges' not in agent_scm or edge_id not in agent_scm['edges']:
            return agent_scm
        
        edge = agent_scm['edges'][edge_id]
        
        # Update function type if provided
        if 'function_type' in function_params:
            edge['function']['function_type'] = function_params['function_type']
        
        # Update parameters if provided
        if 'parameters' in function_params:
            for param_name, param_value in function_params['parameters'].items():
                edge['function']['parameters'][param_name] = param_value
        
        # Update noise if provided
        if 'noise_std' in function_params:
            edge['function']['noise_std'] = function_params['noise_std']
        
        # Update confidence if provided
        if 'confidence' in function_params:
            edge['function']['confidence'] = function_params['confidence']
        
        return agent_scm
    
    def add_qa_to_graph(self, agent_scm, qa_pair, parsed_belief=None):
        """
        Add a QA pair to the SCM graph.
        
        Args:
            agent_scm (dict): The existing SCM
            qa_pair (dict): QA pair to add
            parsed_belief (dict, optional): Parsed belief from the QA pair
            
        Returns:
            dict: Updated SCM
        """
        # Ensure qas list exists
        if 'qas' not in agent_scm:
            agent_scm['qas'] = []
        
        # Format the QA ID if needed
        qa_id = qa_pair.get('id')
        if not qa_id or not isinstance(qa_id, str):
            qa_id = f"qa_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        elif not qa_id.startswith("qa_"):
            qa_id = f"qa_{qa_id}"
        
        # Create QA entry
        qa_entry = {
            "qa_id": qa_id,
            "question": qa_pair.get('question', ''),
            "answer": qa_pair.get('answer', '')
        }
        
        # Always include parsed_belief field to comply with schema
        # If parsed_belief is None or empty, use an empty object
        if parsed_belief:
            qa_entry["parsed_belief"] = parsed_belief
        else:
            # Empty parsed_belief object that complies with schema
            qa_entry["parsed_belief"] = {}
        
        # Check if this QA pair already exists
        existing_qa_index = None
        for i, qa in enumerate(agent_scm['qas']):
            if qa['qa_id'] == qa_id:
                existing_qa_index = i
                break
        
        if existing_qa_index is not None:
            # Update existing QA
            agent_scm['qas'][existing_qa_index] = qa_entry
        else:
            # Add new QA
            agent_scm['qas'].append(qa_entry)
        
        return agent_scm
    
    def check_termination(self, agent_scm):
        """
        Check if the interview should be terminated based on SCM state.
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            bool: True if the interview should be terminated, False otherwise
        """
        # Check for structural convergence
        structure_converged = self._check_structure_convergence(agent_scm)
        
        # Check for information gain saturation
        info_gain_saturated = self._check_info_gain_saturation(agent_scm)
        
        # Check for redundancy saturation
        redundancy_saturated = self._check_redundancy_saturation(agent_scm)
        
        # Terminate if all conditions are met
        if structure_converged and info_gain_saturated and redundancy_saturated:
            self.terminate_interview = True
        
        return self.terminate_interview
    
    def get_next_phase(self, agent_scm):
        """
        Determine the next phase based on the current SCM state.
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            int: The phase to transition to (1, 2, or 3)
        """
        # If we're in Phase 1 and have enough anchor nodes, move to Phase 2
        if self.current_phase == 1 and len(self.anchor_queue) >= 3:
            self.current_phase = 2
        
        # If we're in Phase 2 and all anchors have been expanded, move to Phase 3
        elif self.current_phase == 2 and self._all_anchors_expanded(agent_scm):
            self.current_phase = 3
        
        # If we're in Phase 3 and new nodes have been discovered, go back to Phase 1
        elif self.current_phase == 3 and len(self.node_candidate_queue) > 0:
            self.current_phase = 1
        
        return self.current_phase
    
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
        # Update appearance information
        if 'appearance' not in existing_node:
            existing_node['appearance'] = {'qa_ids': [], 'frequency': 0}
        
        # Add new QA IDs
        for qa_id in new_node.get('appearance', {}).get('qa_ids', []):
            if qa_id not in existing_node['appearance']['qa_ids']:
                existing_node['appearance']['qa_ids'].append(qa_id)
        
        # Update frequency
        existing_node['appearance']['frequency'] = len(existing_node['appearance']['qa_ids'])
        
        # Promote the node if it meets the criteria
        if existing_node['appearance']['frequency'] >= 2 and existing_node.get('status') == 'proposed':
            existing_node['status'] = 'confirmed'
    
    def _check_node_promotion(self, agent_scm):
        """
        Check if any nodes should be promoted to anchors.
        
        Args:
            agent_scm (dict): The current SCM
        """
        for node_id, node in agent_scm['nodes'].items():
            # Promote to anchor if:
            # 1. It appears in at least 2 QA pairs
            # 2. It has a status of 'confirmed'
            # 3. It's not already an anchor
            # 4. We haven't exceeded the maximum number of anchors
            if (node.get('appearance', {}).get('frequency', 0) >= 2 and
                node.get('status') == 'confirmed' and
                node_id not in self.anchor_queue and
                len(self.anchor_queue) < self.max_anchors):
                
                # Promote to anchor
                node['status'] = 'anchor'
                self.anchor_queue.append(node_id)
                
                # Remove from candidate queue if present
                if node_id in self.node_candidate_queue:
                    self.node_candidate_queue.remove(node_id)
    
    def _check_structure_convergence(self, agent_scm):
        """
        Check if the structure has converged (no new meaningful changes).
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            bool: True if structure has converged, False otherwise
        """
        # Simple check: No new nodes or edges in the last few rounds
        if len(self.node_candidate_queue) == 0 and self.stable_rounds >= 3:
            return True
        
        # If there are still candidates, structure hasn't converged
        if len(self.node_candidate_queue) > 0:
            self.stable_rounds = 0
            return False
        
        # Increment stable rounds counter if no new candidates
        self.stable_rounds += 1
        return False
    
    def _check_info_gain_saturation(self, agent_scm):
        """
        Check if information gain has saturated.
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            bool: True if information gain has saturated, False otherwise
        """
        # Simplified check: All anchor nodes have multiple edges
        for node_id in self.anchor_queue:
            if node_id in agent_scm['nodes']:
                node = agent_scm['nodes'][node_id]
                edge_count = len(node.get('incoming_edges', [])) + len(node.get('outgoing_edges', []))
                if edge_count < 2:
                    return False
        
        # If all anchor nodes have multiple edges, info gain has saturated
        return len(self.anchor_queue) > 0
    
    def _check_redundancy_saturation(self, agent_scm):
        """
        Check if redundancy has saturated (no new unique information being added).
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            bool: True if redundancy has saturated, False otherwise
        """
        # Simplified: Check if all anchors have been fully expanded
        return self._all_anchors_expanded(agent_scm)
    
    def _all_anchors_expanded(self, agent_scm):
        """
        Check if all anchor nodes have been fully expanded.
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            bool: True if all anchors have been fully expanded, False otherwise
        """
        for node_id in self.anchor_queue:
            if node_id in agent_scm['nodes']:
                node = agent_scm['nodes'][node_id]
                # An anchor is fully expanded if it has connections to at least 3 other nodes
                total_connections = len(node.get('incoming_edges', [])) + len(node.get('outgoing_edges', []))
                if total_connections < 3:
                    return False
        
        # If we have no anchors, consider them "all expanded"
        return len(self.anchor_queue) > 0 