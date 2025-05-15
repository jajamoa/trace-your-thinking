from typing import Dict, List, Any, Optional, Union
import json
import requests
from functools import lru_cache

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
        # Cache for default topic
        self._cached_default_topic = None
    
    def _sanitize_topic(self, topic: str) -> str:
        """
        Sanitize the topic name to avoid problematic labels like "none".
        
        Args:
            topic: The original topic string
            
        Returns:
            str: Sanitized topic string
        """
        if not topic or not isinstance(topic, str) or topic.lower() == "none" or topic.strip() == "":
            return "policy"  # Default fallback
        return topic
    
    def _get_default_topic(self, request_topic=None) -> str:
        """
        Get the default topic with priority: request topic > cached topic > environment variable > default.
        
        Args:
            request_topic (str, optional): Topic provided in the request
            
        Returns:
            str: The default topic, or "policy" if not found
        """
        # First try to use topic from request
        if request_topic:
            sanitized_topic = self._sanitize_topic(request_topic)
            self._cached_default_topic = sanitized_topic  # Cache it
            return sanitized_topic
            
        # Use cached value if available
        if self._cached_default_topic:
            return self._cached_default_topic
            
        try:
            # Try to get from environment variable
            env_topic = config.RESEARCH_TOPIC
            if env_topic and env_topic.strip() and env_topic.lower() != "none":
                sanitized_topic = self._sanitize_topic(env_topic)
                self._cached_default_topic = sanitized_topic  # Cache it
                return sanitized_topic
            
            # If we can't get the topic, use default
            logger.warning("No topic specified, using 'policy'")
            return "policy"
        except Exception as e:
            logger.error(f"Error getting default topic: {str(e)}")
            return "policy"  # Default fallback
    
    def get_cbn(self, session_id: str, agent_id: str,
               existing_causal_graph: Optional[Dict[str, Any]] = None,
               request_topic: str = None) -> CausalBayesianNetwork:
        """
        Get or create a CBN for a session.
        
        Args:
            session_id: ID of the session
            agent_id: ID of the agent/user
            existing_causal_graph: Optional existing causal graph
            request_topic: Optional topic provided in the request
            
        Returns:
            CausalBayesianNetwork: CBN instance
        """
        cbn_key = f"{session_id}_{agent_id}"
        
        # Get topic from request, cache or default
        sanitized_topic = self._get_default_topic(request_topic)
        
        if cbn_key in self.cbn_store:
            # Use existing CBN from store
            cbn = self.cbn_store[cbn_key]
            logger.info(f"Using existing CBN: {len(cbn.nodes)} nodes, {len(cbn.edges)} edges")
            self._fix_stance_node_labels(cbn, sanitized_topic)
        elif existing_causal_graph and isinstance(existing_causal_graph, dict):
            # Create CBN from existing causal graph
            cbn = CausalBayesianNetwork(agent_id, existing_causal_graph)
            logger.info(f"Using provided causal graph: {len(cbn.nodes)} nodes, {len(cbn.edges)} edges")
            self._fix_stance_node_labels(cbn, sanitized_topic)
            self.cbn_store[cbn_key] = cbn
        else:
            # Create new CBN (will automatically include a stance node)
            cbn = CausalBayesianNetwork(agent_id)
            
            # Update stance node label with topic from request
            stance_node_id = cbn.get_stance_node_id()
            if stance_node_id:
                stance_label = f"Support for {sanitized_topic}"
                cbn.data["nodes"][stance_node_id]["label"] = stance_label
            
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
            
            qa_id, node_map = self._process_extracted_nodes(cbn, qa_pair, extracted_nodes, extracted_relations)
            
            # 3. Process relations
            if verbose_logging:
                log_section_header("2. Relation Processing")
            
            if extracted_relations:
                logger.info(f"Processing {len(extracted_relations)} relations")
                
                self._process_relations(cbn, extracted_relations, node_map, qa_id)
        else:
            logger.warning("No nodes extracted from QA pair")
        
        # Log current state
        if verbose_logging:
            log_section_header("CBN Update Summary")
        logger.info(f"Updated CBN now has {len(cbn.nodes)} nodes and {len(cbn.edges)} edges")
        
        if verbose_logging:
            log_separator()
        
        return cbn
    
    def _process_extracted_nodes(self, cbn: CausalBayesianNetwork, qa_pair: Dict[str, Any], 
                                extracted_nodes: Dict[str, Any], extracted_relations: List[Dict[str, Any]]) -> tuple:
        """Process extracted nodes and add them to the CBN."""
        # Prepare extracted pairs for QA entry
        extracted_pairs = [{
            "source": relation.get('source_label', ''),
            "target": relation.get('target_label', ''),
            "confidence": relation.get('confidence', 0.9)
        } for relation in extracted_relations]
        
        # Add QA entry
        qa_id = cbn.add_qa(qa_pair, extracted_pairs)
        
        # Add or update nodes
        node_map = {}  # Map from labels to node IDs
        for label, node_data in extracted_nodes.items():
            confidence = node_data.get('confidence', 0.9)
            is_stance = node_data.get('is_stance', False)
            
            # Skip creating new stance nodes, we only use the initial one
            if is_stance and cbn.get_stance_node_id():
                continue
                
            # Check if node already exists
            existing_node_id = cbn.get_node_by_label(label)
            
            if existing_node_id:
                # Update existing node
                cbn.data['nodes'][existing_node_id]['source_qa'].append(qa_id)
                if confidence > cbn.data['nodes'][existing_node_id]['confidence']:
                    cbn.data['nodes'][existing_node_id]['confidence'] = confidence
                node_map[label] = existing_node_id
            else:
                # Add new node (not a stance node unless it's the initial one)
                node_id = cbn.add_node(label, confidence, [qa_id], is_stance=is_stance and not cbn.get_stance_node_id())
                node_map[label] = node_id
        
        return qa_id, node_map
    
    def _process_relations(self, cbn: CausalBayesianNetwork, relations: List[Dict[str, Any]], 
                          node_map: Dict[str, str], qa_id: str) -> None:
        """Process extracted relations and add them to the CBN."""
        logger.info(f"Processing {len(relations)} relations")
        
        for relation in relations:
            source_label = relation.get('source_label', '').lower()
            target_label = relation.get('target_label', '').lower()
            confidence = relation.get('confidence', 0.9)
            modifier = relation.get('modifier', 1.0)
            
            # Skip if source or target is missing
            if not source_label or not target_label:
                continue
            
            # Get node IDs
            source_id = node_map.get(source_label) or cbn.get_node_by_label(source_label)
            target_id = node_map.get(target_label) or cbn.get_node_by_label(target_label)
            
            if not source_id or not target_id:
                logger.warning(f"Cannot create edge: nodes not found: {source_label} or {target_label}")
                continue
            
            # Check if edge already exists
            existing_edge_id = cbn.get_edge_by_nodes(source_id, target_id)
            
            if existing_edge_id:
                # Update existing edge with new evidence
                cbn.update_edge(existing_edge_id, qa_id, confidence)
            else:
                # Add new edge
                cbn.add_edge(source_id, target_id, confidence, modifier, qa_id)
    
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
        stance_node_id = cbn.get_stance_node_id()
        
        if not stance_node_id:
            # No stance node found, create one
            stance_label = f"Support for {topic}"
            cbn.add_node(stance_label, 1.0, [], is_stance=True)
            return
            
        # Fix existing stance node if needed
        node = cbn.data["nodes"][stance_node_id]
        label = node.get("label", "")
        
        # Fix problematic labels
        if not isinstance(label, str) or not label.strip() or "none" in str(label).lower():
            node["label"] = f"Support for {topic}"
        # Handle non-standard format but preserve existing information
        elif not str(label).lower().startswith("support for "):
            node["label"] = f"Support for {label}"
        # Handle incomplete format
        elif label.lower() == "support for":
            node["label"] = f"Support for {topic}"
                
        # Ensure there's at least one stance node with a good label
        cbn._ensure_stance_node(f"Support for {topic}") 