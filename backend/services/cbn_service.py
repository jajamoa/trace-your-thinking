from typing import Dict, List, Any, Optional, Union
import json
import requests

# Use absolute imports instead of relative imports
from models.cbn import CausalBayesianNetwork
from utils.logging import logger, log_section_header, log_separator
from config import config

class CBNService:
    """Service for managing Causal Bayesian Networks."""
    
    def __init__(self):
        """Initialize the CBN service."""
        # Store CBNs for each session
        self.cbn_store = {}
    
    def _sanitize_topic(self, topic: str) -> str:
        """
        Sanitize the topic name to avoid problematic labels like "none".
        
        Args:
            topic: The original topic string
            
        Returns:
            str: Sanitized topic string
        """
        # Handle case where topic might not be a string
        if not topic:
            return "policy"  # Default fallback
        
        # Convert to string if not already
        if not isinstance(topic, str):
            logger.warning(f"Expected string for topic but got {type(topic)}")
            return "policy"
            
        if topic.lower() == "none" or topic.strip() == "":
            return "policy"  # Default fallback
        return topic
    
    def _get_default_topic(self) -> str:
        """
        Get the default topic from the interview settings.
        
        Returns:
            str: The default topic, or "policy" if not found
        """
        try:
            # Try to fetch from MongoDB via API (to avoid direct DB dependency)
            # This uses the internal API route that doesn't require authentication
            api_url = f"{config.API_BASE_URL}/api/admin/settings"
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("settings") and data["settings"].get("defaultTopic"):
                    topic = data["settings"]["defaultTopic"]
                    logger.info(f"Using default topic from settings: '{topic}'")
                    return self._sanitize_topic(topic)
            
            # If we can't get the topic, use default
            logger.warning("Could not fetch default topic from settings, using 'policy'")
            return "policy"
        except Exception as e:
            logger.error(f"Error fetching default topic: {str(e)}")
            return "policy"  # Default fallback
    
    def get_cbn(self, session_id: str, agent_id: str, topic: str = None,
               existing_causal_graph: Optional[Dict[str, Any]] = None) -> CausalBayesianNetwork:
        """
        Get or create a CBN for a session.
        
        Args:
            session_id: ID of the session
            agent_id: ID of the agent/user
            topic: Optional parameter kept for backwards compatibility but not used
            existing_causal_graph: Optional existing causal graph
            
        Returns:
            CausalBayesianNetwork: CBN instance
        """
        cbn_key = f"{session_id}_{agent_id}"
        
        # Always get the topic from database settings - ignore any passed topic parameter
        database_topic = self._get_default_topic()
        
        # Sanitize the topic to avoid problematic labels
        sanitized_topic = self._sanitize_topic(database_topic)
        
        if cbn_key in self.cbn_store:
            # Use existing CBN from store
            cbn = self.cbn_store[cbn_key]
            logger.info(f"Using existing CBN from memory store with {len(cbn.nodes)} nodes and {len(cbn.edges)} edges")
            
            # Check for and fix any "none" stance nodes - ALWAYS use the database topic
            self._fix_stance_node_labels(cbn, sanitized_topic)
        elif existing_causal_graph and isinstance(existing_causal_graph, dict):
            # Create CBN from existing causal graph
            cbn = CausalBayesianNetwork(agent_id, existing_causal_graph)
            logger.info(f"Using causal graph from API request with {len(cbn.nodes)} nodes and {len(cbn.edges)} edges")
            
            # Check for and fix any stance nodes - ALWAYS use the database topic
            self._fix_stance_node_labels(cbn, sanitized_topic)
            
            self.cbn_store[cbn_key] = cbn
        else:
            # Create new CBN (will automatically include a stance node)
            cbn = CausalBayesianNetwork(agent_id)
            
            # Get stance node ID
            stance_node_id = cbn.get_stance_node_id()
            if stance_node_id:
                # Update stance node label with topic from database
                stance_label = f"Support for {sanitized_topic}"
                cbn.data["nodes"][stance_node_id]["label"] = stance_label
                logger.info(f"Created new CBN with stance node: '{stance_label}'")
            
            logger.info(f"Created new CBN for user {agent_id}")
            self.cbn_store[cbn_key] = cbn
        
        return cbn
    
    def update_cbn_with_qa(self, cbn: CausalBayesianNetwork, qa_pair: Dict[str, Any], 
                          llm_service, verbose_logging: bool = False) -> CausalBayesianNetwork:
        """
        Update a CBN with information extracted from a QA pair.
        
        Args:
            cbn: CBN to update
            qa_pair: QA pair to process
            llm_service: LLM service for extraction
            verbose_logging: Whether to log detailed processing steps
            
        Returns:
            CausalBayesianNetwork: Updated CBN
        """
        if verbose_logging:
            logger.info("Starting CBN update with QA pair")
            log_separator()
        
        # Log current CBN state
        logger.info(f"Current CBN stats: {len(cbn.nodes)} nodes and {len(cbn.edges)} edges")
        
        # 1. Extract nodes and relations from the QA pair
        if verbose_logging:
            log_section_header("1. Node and Relation Extraction")
        
        extracted_data = llm_service.extract_causal_data(qa_pair)
        extracted_nodes = extracted_data.get('nodes', {})
        extracted_relations = extracted_data.get('relations', [])
        
        # 2. Process nodes
        if extracted_nodes:
            logger.info(f"Extracted {len(extracted_nodes)} nodes")
            
            # Create QA entry first to get QA ID
            extracted_pairs = []
            for relation in extracted_relations:
                extracted_pairs.append({
                    "source": relation.get('source_label', ''),
                    "target": relation.get('target_label', ''),
                    "confidence": relation.get('confidence', 0.9)
                })
            
            qa_id = cbn.add_qa(qa_pair, extracted_pairs)
            logger.info(f"Added QA entry with ID: {qa_id}")
            
            # Check if any node is a stance node (from the extraction)
            has_stance_belief = False
            for label, node_data in extracted_nodes.items():
                if self._is_stance_belief(label):
                    has_stance_belief = True
                    break
            
            # Add nodes to CBN
            node_map = {}  # Map from labels to node IDs
            for label, node_data in extracted_nodes.items():
                confidence = node_data.get('confidence', 0.9)
                is_stance = self._is_stance_belief(label)
                
                # Check if node with this label already exists
                existing_node_id = cbn.get_node_by_label(label)
                
                if existing_node_id:
                    # Update existing node
                    cbn.data['nodes'][existing_node_id]['source_qa'].append(qa_id)
                    # Potentially update confidence if higher
                    if confidence > cbn.data['nodes'][existing_node_id]['confidence']:
                        cbn.data['nodes'][existing_node_id]['confidence'] = confidence
                    
                    node_map[label] = existing_node_id
                    logger.info(f"Updated existing node: '{label}' (confidence: {confidence})")
                else:
                    # Add new node
                    node_id = cbn.add_node(
                        label, 
                        confidence, 
                        [qa_id], 
                        is_stance=is_stance
                    )
                    node_map[label] = node_id
                    logger.info(f"Added new node: '{label}' (confidence: {confidence})")
            
            # 3. Process relations
            if verbose_logging:
                log_section_header("2. Relation Processing")
            
            if extracted_relations:
                logger.info(f"Processing {len(extracted_relations)} relations")
                
                for relation in extracted_relations:
                    source_label = relation.get('source_label')
                    target_label = relation.get('target_label')
                    confidence = relation.get('confidence', 0.9)
                    modifier = relation.get('modifier', 1.0)
                    
                    # Skip if source or target is missing
                    if not source_label or not target_label:
                        continue
                    
                    # Get node IDs
                    source_id = node_map.get(source_label) or cbn.get_node_by_label(source_label)
                    target_id = node_map.get(target_label) or cbn.get_node_by_label(target_label)
                    
                    if not source_id or not target_id:
                        logger.warning(f"Cannot create edge: nodes not found in CBN: {source_label} or {target_label}")
                        continue
                    
                    # Check if edge already exists
                    existing_edge_id = cbn.get_edge_by_nodes(source_id, target_id)
                    
                    if existing_edge_id:
                        # Update existing edge with new evidence
                        cbn.update_edge(existing_edge_id, qa_id, confidence)
                        logger.info(f"Updated existing edge: {source_label} → {target_label}")
                    else:
                        # Add new edge
                        edge_id = cbn.add_edge(source_id, target_id, confidence, modifier, qa_id)
                        logger.info(f"Added new edge: {source_label} → {target_label}")
                        
                # 4. If no stance belief was extracted, try to connect to stance node
                if not has_stance_belief:
                    stance_node_id = cbn.get_stance_node_id()
                    if stance_node_id:
                        # Look for potential connections to the stance node
                        self._connect_to_stance_node(cbn, stance_node_id, extracted_nodes, node_map, qa_id)
        else:
            logger.warning("No nodes extracted from QA pair")
        
        # Log current state
        if verbose_logging:
            log_section_header("CBN Update Summary")
        logger.info(f"Updated CBN now has {len(cbn.nodes)} nodes and {len(cbn.edges)} edges")
        
        if verbose_logging:
            log_separator()
        
        return cbn
    
    def _is_stance_belief(self, label: str) -> bool:
        """
        Check if a label represents a stance belief.
        
        Args:
            label: The node label to check
            
        Returns:
            bool: True if the label indicates a stance belief
        """
        label_lower = label.lower()
        stance_keywords = [
            "support", "oppose", "agree", "disagree", "approve", "disapprove", 
            "in favor", "against", "pro", "anti", "endorse", "reject", "stance",
            "position", "opinion", "view", "vote", "choose", "decision"
        ]
        
        return any(keyword in label_lower for keyword in stance_keywords)
    
    def _connect_to_stance_node(self, cbn: CausalBayesianNetwork, stance_node_id: str, 
                              extracted_nodes: Dict[str, Any], node_map: Dict[str, str], 
                              qa_id: str) -> None:
        """
        Attempt to connect an extracted belief to the stance node.
        
        Args:
            cbn: The CBN to update
            stance_node_id: The ID of the stance node
            extracted_nodes: Dictionary of extracted node labels and data
            node_map: Mapping of labels to node IDs
            qa_id: The QA ID for evidence
        """
        # Find a potential node to connect to the stance node
        for label, node_id in node_map.items():
            label_lower = label.lower()
            
            # These keywords often indicate beliefs that influence stance
            influence_keywords = [
                "impact", "effect", "benefit", "harm", "consequence", "result",
                "outcome", "change", "improve", "worsen", "increase", "decrease"
            ]
            
            if any(keyword in label_lower for keyword in influence_keywords):
                # Check if connection already exists
                existing_edge = cbn.get_edge_by_nodes(node_id, stance_node_id)
                
                if not existing_edge:
                    # Create a causal connection with modest confidence
                    edge_id = cbn.add_edge(
                        node_id,  # from the belief node
                        stance_node_id,  # to the stance node
                        confidence=0.7,  # moderate confidence
                        modifier=0.8,  # positive causal influence
                        qa_id=qa_id
                    )
                    
                    stance_label = cbn.data["nodes"][stance_node_id]["label"]
                    node_label = cbn.data["nodes"][node_id]["label"]
                    logger.info(f"Added inferred connection from '{node_label}' to stance '{stance_label}'")
                    return  # Only create one connection
    
    def check_termination(self, cbn: CausalBayesianNetwork) -> bool:
        """
        Check if the CBN has enough information and interview should be terminated.
        
        Args:
            cbn: CBN to check
            
        Returns:
            bool: True if termination criteria are met, False otherwise
        """
        # Basic termination criteria
        # At least 5 nodes and 8 edges
        if (len(cbn.nodes) >= 5 and len(cbn.edges) >= 8):
            return True
        
        return False

    def _fix_stance_node_labels(self, cbn: CausalBayesianNetwork, topic: str = "policy") -> None:
        """
        Fix any stance nodes with problematic labels like "Support for none".
        
        Args:
            cbn: The CBN to check
            topic: The sanitized topic to use for stance node labels
        """
        for node_id, node in cbn.nodes.items():
            if node.get("is_stance", False):
                label = node.get("label", "")
                
                # Handle case where label might not be a string
                if not isinstance(label, str):
                    logger.warning(f"Node {node_id} has non-string label: {type(label)}")
                    new_label = f"Support for {topic}"
                    cbn.data["nodes"][node_id]["label"] = new_label
                    logger.info(f"Fixed stance node with non-string label to '{new_label}'")
                    continue
                
                # Handle empty labels    
                if not label.strip():
                    new_label = f"Support for {topic}"
                    cbn.data["nodes"][node_id]["label"] = new_label
                    logger.info(f"Fixed empty stance node label to '{new_label}'")
                    continue
                
                # ONLY fix labels containing "none"
                if "none" in label.lower():
                    new_label = f"Support for {topic}"
                    cbn.data["nodes"][node_id]["label"] = new_label
                    logger.info(f"Fixed stance node label from '{label}' to '{new_label}'")
                    continue
                
                # Handle case where label isn't in "Support for X" format,
                # but preserve the existing information as the topic
                if not label.lower().startswith("support for "):
                    new_label = f"Support for {label}"
                    cbn.data["nodes"][node_id]["label"] = new_label
                    logger.info(f"Standardized stance node format from '{label}' to '{new_label}'")
                    continue
                
                # At this point, we have a label that starts with "Support for "
                # If it's exactly "Support for" with nothing after, fix it
                if label.lower() == "support for":
                    new_label = f"Support for {topic}"
                    cbn.data["nodes"][node_id]["label"] = new_label
                    logger.info(f"Fixed incomplete stance node label '{label}' to '{new_label}'")
                
                # Otherwise, it's a good label like "Support for open science" - keep it!
                    
        # Ensure there's at least one stance node with a good label
        stance_label = f"Support for {topic}"
        cbn._ensure_stance_node(stance_label) 