from typing import Dict, List, Any, Optional, Union
import uuid

class CausalBayesianNetwork:
    """Causal Bayesian Network (CBN) representation."""
    
    def __init__(self, agent_id: str, existing_model: Optional[Dict[str, Any]] = None):
        """
        Initialize a new CBN or load an existing one.
        
        Args:
            agent_id: Unique identifier for the agent/user
            existing_model: Optional existing CBN data to load
        """
        # Define default structure
        default_structure = {
            "agent_id": agent_id,
            "nodes": {},
            "edges": {},
            "qa_history": {}
        }
        
        if existing_model:
            # Load from existing model
            self.data = existing_model
            
            # Ensure agent_id is set
            if 'agent_id' not in self.data or not self.data['agent_id']:
                self.data['agent_id'] = agent_id
            
            # Ensure all required keys exist
            for key, default_value in default_structure.items():
                if key not in self.data:
                    self.data[key] = default_value
        else:
            # Create new CBN with default structure
            self.data = default_structure
            
        # Always ensure there's a stance node
        self._ensure_stance_node()
    
    def _ensure_stance_node(self, default_label: str = "Support for policy"):
        """
        Ensure the CBN has exactly one stance node with a valid label.
        
        Args:
            default_label: Default label for stance node if one needs to be created
        """
        # Collect all stance nodes
        stance_nodes = []
        
        # Check for existing stance nodes
        for node_id, node in self.data["nodes"].items():
            if node.get("is_stance", False):
                stance_nodes.append(node_id)
        
        # Extract topic from default_label if possible (for consistency)
        topic = "policy"  # Default fallback
        if default_label.startswith("Support for "):
            extracted_topic = default_label[len("Support for "):]
            if extracted_topic and extracted_topic.lower() != "none":
                topic = extracted_topic
        
        # Handle based on number of stance nodes found
        if len(stance_nodes) == 0:
            # No stance node found, create a default one
            stance_node_id = f"n_{uuid.uuid4().hex[:8]}"
            self.data["nodes"][stance_node_id] = {
                "id": stance_node_id,
                "label": default_label,
                "is_stance": True,
                "confidence": 1.0,
                "source_qa": [],
                "incoming_edges": [],
                "outgoing_edges": []
            }
        elif len(stance_nodes) > 1:
            # Multiple stance nodes found, keep the best one
            # Sort nodes based on more sophisticated criteria
            def node_score(node_id):
                node = self.data["nodes"][node_id]
                label = node.get("label", "")
                
                # Start with a base score
                score = 0
                
                # Ensure label is a string
                if not isinstance(label, str):
                    return -100  # Heavy penalty for non-string labels
                
                # Score based on label content and format
                lower_label = label.lower()
                has_none = "none" in lower_label
                has_proper_format = lower_label.startswith("support for ")
                
                # Penalize "none" in label
                if has_none:
                    score -= 100
                
                # Prefer proper "Support for X" format
                if has_proper_format:
                    score += 50
                
                # Prefer nodes with specific topics
                if has_proper_format and len(lower_label) > 12:  # "support for " is 12 chars
                    score += 25  # Bonus for having a specific topic
                
                # Prefer nodes with more connections
                incoming_edges = len(node.get("incoming_edges", []))
                score += incoming_edges * 5
                
                return score
            
            # Sort by score in descending order
            sorted_stance_nodes = sorted(stance_nodes, key=node_score, reverse=True)
            
            # Keep the highest scoring node
            keep_node_id = sorted_stance_nodes[0]
            keep_node = self.data["nodes"][keep_node_id]
            keep_node_label = keep_node.get("label", "")
            
            # ONLY fix truly problematic labels, preserve valid topics
            if not isinstance(keep_node_label, str):
                # Non-string label needs fixing
                self.data["nodes"][keep_node_id]["label"] = f"Support for {topic}"
            elif "none" in keep_node_label.lower():
                # "none" in label needs fixing
                self.data["nodes"][keep_node_id]["label"] = f"Support for {topic}"
            elif not keep_node_label.lower().startswith("support for "):
                # Format needs standardizing but preserve the content as topic
                self.data["nodes"][keep_node_id]["label"] = f"Support for {keep_node_label}"
            # Otherwise preserve the existing valid label (e.g., "Support for open science")
            
            # Remove all other stance nodes
            for node_id in sorted_stance_nodes[1:]:
                # Redirect any incoming edges to the kept node
                node_to_remove = self.data["nodes"][node_id]
                for edge_id in node_to_remove.get("incoming_edges", []):
                    if edge_id in self.data["edges"]:
                        # Update edge to point to kept node
                        self.data["edges"][edge_id]["target"] = keep_node_id
                        
                        # Add to incoming edges of kept node
                        if edge_id not in self.data["nodes"][keep_node_id]["incoming_edges"]:
                            self.data["nodes"][keep_node_id]["incoming_edges"].append(edge_id)
                
                # Remove the node
                del self.data["nodes"][node_id]
                
                # Clean up any edges that pointed to this node
                edges_to_remove = []
                for edge_id, edge in self.data["edges"].items():
                    if edge.get("source") == node_id or edge.get("target") == node_id:
                        edges_to_remove.append(edge_id)
                
                for edge_id in edges_to_remove:
                    del self.data["edges"][edge_id]
        else:
            # Only one stance node, ensure it has a valid label
            stance_node_id = stance_nodes[0]
            node = self.data["nodes"][stance_node_id]
            node_label = node.get("label", "")
            
            # ONLY fix truly problematic labels
            if not isinstance(node_label, str):
                # Non-string label needs fixing
                self.data["nodes"][stance_node_id]["label"] = f"Support for {topic}"
            elif "none" in node_label.lower() or not node_label:
                # "none" in label or empty label needs fixing
                self.data["nodes"][stance_node_id]["label"] = f"Support for {topic}"
            elif not node_label.lower().startswith("support for "):
                # Format needs standardizing but preserve the content as topic
                self.data["nodes"][stance_node_id]["label"] = f"Support for {node_label}"
            # Otherwise preserve the existing valid label
    
    @property
    def agent_id(self) -> str:
        """Get the agent ID."""
        return self.data.get("agent_id", "")
    
    @property
    def nodes(self) -> Dict[str, Dict[str, Any]]:
        """Get all nodes in the CBN."""
        return self.data.get("nodes", {})
    
    @property
    def edges(self) -> Dict[str, Dict[str, Any]]:
        """Get all edges in the CBN."""
        return self.data.get("edges", {})
    
    @property
    def qa_history(self) -> Dict[str, Dict[str, Any]]:
        """Get all QA pairs in the CBN."""
        return self.data.get("qa_history", {})
    
    def get_stance_node_id(self) -> Optional[str]:
        """Get the ID of the stance node."""
        for node_id, node in self.nodes.items():
            if node.get("is_stance", False):
                return node_id
        return None
    
    def add_qa(self, qa_pair: Dict[str, Any], extracted_pairs: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Add a QA pair to the qa_history.
        
        Args:
            qa_pair: The QA pair to add with question and answer
            extracted_pairs: Optional list of extracted source-target pairs
            
        Returns:
            str: ID of the added QA pair
        """
        qa_id = f"qa_{uuid.uuid4().hex[:8]}"
        
        qa_entry = {
            "question": qa_pair.get("question", ""),
            "answer": qa_pair.get("answer", ""),
            "extracted_pairs": extracted_pairs or []
        }
        
        self.data["qa_history"][qa_id] = qa_entry
        return qa_id
    
    def add_node(self, label: str, confidence: float = 0.9, 
                source_qa: Optional[List[str]] = None, is_stance: bool = False) -> str:
        """
        Add a node to the CBN.
        
        Args:
            label: Label of the node
            confidence: Confidence score (0.0-1.0)
            source_qa: List of source QA IDs
            is_stance: Whether this is a stance node
            
        Returns:
            str: ID of the added node
        """
        node_id = f"n_{uuid.uuid4().hex[:8]}"
        
        self.data["nodes"][node_id] = {
            "id": node_id,
            "label": label,
            "is_stance": is_stance,
            "confidence": confidence,
            "source_qa": source_qa or [],
            "incoming_edges": [],
            "outgoing_edges": []
        }
        
        return node_id
    
    def add_edge(self, source_node_id: str, target_node_id: str, 
                confidence: float = 0.9, modifier: float = 1.0,
                qa_id: Optional[str] = None) -> str:
        """
        Add an edge to the CBN.
        
        Args:
            source_node_id: ID of the source node
            target_node_id: ID of the target node
            confidence: Confidence score (0.0-1.0)
            modifier: Causal direction and strength (-1.0 to 1.0)
            qa_id: ID of the QA pair providing evidence
            
        Returns:
            str: ID of the added edge
        """
        edge_id = f"e_{uuid.uuid4().hex[:8]}"
        
        evidence = []
        if qa_id:
            evidence.append({"qa_id": qa_id, "confidence": confidence})
        
        self.data["edges"][edge_id] = {
            "source": source_node_id,
            "target": target_node_id,
            "aggregate_confidence": confidence,
            "evidence": evidence,
            "modifier": modifier
        }
        
        # Update node references to this edge
        if source_node_id in self.data["nodes"]:
            self.data["nodes"][source_node_id]["outgoing_edges"].append(edge_id)
        
        if target_node_id in self.data["nodes"]:
            self.data["nodes"][target_node_id]["incoming_edges"].append(edge_id)
        
        return edge_id
    
    def update_edge(self, edge_id: str, qa_id: str, confidence: float) -> None:
        """
        Update an existing edge with new evidence.
        
        Args:
            edge_id: ID of the edge to update
            qa_id: QA ID providing new evidence
            confidence: Confidence score for this evidence (0.0-1.0)
        """
        if edge_id not in self.data["edges"]:
            return
        
        # Add new evidence
        self.data["edges"][edge_id]["evidence"].append({
            "qa_id": qa_id,
            "confidence": confidence
        })
        
        # Recalculate aggregate confidence (average of all evidence)
        evidences = self.data["edges"][edge_id]["evidence"]
        total_confidence = sum(evidence["confidence"] for evidence in evidences)
        self.data["edges"][edge_id]["aggregate_confidence"] = total_confidence / len(evidences)
    
    def get_node_by_label(self, label: str) -> Optional[str]:
        """
        Find node ID by label.
        
        Args:
            label: Label of the node
            
        Returns:
            Optional[str]: Node ID if found, None otherwise
        """
        label_lower = label.lower()
        
        for node_id, node in self.nodes.items():
            if node.get("label", "").lower() == label_lower:
                return node_id
        
        return None
    
    def get_edge_by_nodes(self, source_id: str, target_id: str) -> Optional[str]:
        """
        Find edge ID by source and target node IDs.
        
        Args:
            source_id: ID of source node
            target_id: ID of target node
            
        Returns:
            Optional[str]: Edge ID if found, None otherwise
        """
        for edge_id, edge in self.edges.items():
            if edge.get("source") == source_id and edge.get("target") == target_id:
                return edge_id
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert CBN to dictionary.
        
        Returns:
            Dict[str, Any]: CBN data as dictionary
        """
        return self.data 