from typing import Dict, List, Any, Optional
import os

# Use absolute imports instead of relative imports
from config import config
from utils.logging import logger, debug_dump

class LLMService:
    """Service for interacting with LLM for causal information extraction."""
    
    def __init__(self):
        """Initialize the LLM service."""
        # Import here to avoid circular imports
        # This is a placeholder - in production this would be replaced with actual LLM client
        try:
            from llm_extractor import QwenLLMExtractor
            
            self.extractor = QwenLLMExtractor(
                api_key=config.DASHSCOPE_API_KEY,
                model=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE
            )
            logger.info(f"Initialized LLM service with model: {config.LLM_MODEL}")
        except ImportError:
            logger.error("Failed to import QwenLLMExtractor. LLM functions will not work.")
            self.extractor = None
    
    def extract_causal_data(self, qa_pair: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract causal data (nodes and relations) from a QA pair for CBN.
        
        Args:
            qa_pair: The QA pair to extract causal data from
            
        Returns:
            Dict[str, Any]: Dictionary containing nodes and relations
        """
        if not self.extractor:
            logger.error("LLM extractor not initialized")
            return {"nodes": {}, "relations": []}
        
        # Log input for debugging
        if config.DEBUG_LLM_IO:
            debug_dump("LLM INPUT (extract_causal_data): Question", qa_pair.get('question', '')[:100])
            debug_dump("LLM INPUT (extract_causal_data): Answer", qa_pair.get('answer', '')[:100])
        
        # Extract causal data
        try:
            # For now, we'll use the existing methods and adapt them
            nodes_result = self.extractor.extract_nodes(qa_pair)
            edge_result = self.extractor.extract_edge(qa_pair)
            
            # Convert to the new format
            nodes = {}
            relations = []
            
            # Process nodes
            for node_id, node_data in nodes_result.items():
                nodes[node_data.get('label', '').lower()] = {
                    'confidence': 0.9  # Default confidence
                }
            
            # Process relations
            if edge_result:
                from_label = edge_result.get('from_label', '').lower()
                to_label = edge_result.get('to_label', '').lower()
                
                # Only add if both labels are present
                if from_label and to_label:
                    # Ensure nodes exist
                    if from_label not in nodes:
                        nodes[from_label] = {'confidence': 0.8}
                    if to_label not in nodes:
                        nodes[to_label] = {'confidence': 0.8}
                    
                    # Create relation
                    relation = {
                        'source_label': from_label,
                        'target_label': to_label,
                        'confidence': edge_result.get('strength', 0.9),
                        'modifier': min(max(edge_result.get('strength', 0.5) * 2 - 1, -1.0), 1.0)  # Convert 0-1 to -1 to 1
                    }
                    
                    relations.append(relation)
            
            result = {
                'nodes': nodes,
                'relations': relations
            }
            
            # Log output for debugging
            if config.DEBUG_LLM_IO:
                debug_dump("LLM OUTPUT (extract_causal_data)", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting causal data: {str(e)}")
            return {"nodes": {}, "relations": []}
    
    # Keep existing methods for backward compatibility
    def extract_nodes(self, qa_pair: Dict[str, Any], ensure_stance_node: bool = False) -> Dict[str, Any]:
        """
        Extract nodes from a QA pair.
        
        Args:
            qa_pair: The QA pair to extract nodes from
            ensure_stance_node: Whether to ensure a stance node is extracted
            
        Returns:
            Dict[str, Any]: Extracted nodes
        """
        if not self.extractor:
            logger.error("LLM extractor not initialized")
            return {}
            
        # Log input for debugging
        if config.DEBUG_LLM_IO:
            debug_dump("LLM INPUT (extract_nodes): Question", qa_pair.get('question', '')[:100])
            debug_dump("LLM INPUT (extract_nodes): Answer", qa_pair.get('answer', '')[:100])
        
        # Extract nodes
        nodes = self.extractor.extract_nodes(qa_pair, ensure_stance_node=ensure_stance_node)
        
        # Log output for debugging
        if config.DEBUG_LLM_IO and nodes:
            debug_dump("LLM OUTPUT (extract_nodes)", nodes)
        
        return nodes
    
    def extract_edge(self, qa_pair: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract edge from a QA pair.
        
        Args:
            qa_pair: The QA pair to extract edge from
            
        Returns:
            Optional[Dict[str, Any]]: Extracted edge if found, None otherwise
        """
        if not self.extractor:
            logger.error("LLM extractor not initialized")
            return None
            
        # Log input for debugging
        if config.DEBUG_LLM_IO:
            debug_dump("LLM INPUT (extract_edge): Question", qa_pair.get('question', '')[:100])
            debug_dump("LLM INPUT (extract_edge): Answer", qa_pair.get('answer', '')[:100])
        
        # Extract edge
        edge = self.extractor.extract_edge(qa_pair)
        
        # Log output for debugging
        if config.DEBUG_LLM_IO and edge:
            debug_dump("LLM OUTPUT (extract_edge)", edge)
        
        return edge
    
    def extract_function_params(self, qa_pair: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract function parameters from a QA pair.
        
        Args:
            qa_pair: The QA pair to extract function parameters from
            
        Returns:
            Optional[Dict[str, Any]]: Extracted function parameters if found, None otherwise
        """
        if not self.extractor:
            logger.error("LLM extractor not initialized")
            return None
            
        # Log input for debugging
        if config.DEBUG_LLM_IO:
            debug_dump("LLM INPUT (extract_function_params): Question", qa_pair.get('question', '')[:100])
            debug_dump("LLM INPUT (extract_function_params): Answer", qa_pair.get('answer', '')[:100])
        
        # Extract function parameters
        function_params = self.extractor.extract_function_params(qa_pair)
        
        # Log output for debugging
        if config.DEBUG_LLM_IO and function_params:
            debug_dump("LLM OUTPUT (extract_function_params)", function_params)
        
        return function_params
    
    def extract_parsed_belief(self, qa_pair: Dict[str, Any], from_node_id: str, to_node_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract parsed belief from a QA pair.
        
        Args:
            qa_pair: The QA pair to extract parsed belief from
            from_node_id: ID of the source node
            to_node_id: ID of the target node
            
        Returns:
            Optional[Dict[str, Any]]: Extracted parsed belief if found, None otherwise
        """
        if not self.extractor:
            logger.error("LLM extractor not initialized")
            return None
            
        # Log input for debugging
        if config.DEBUG_LLM_IO:
            debug_dump("LLM INPUT (extract_parsed_belief): Question", qa_pair.get('question', '')[:100])
            debug_dump("LLM INPUT (extract_parsed_belief): Answer", qa_pair.get('answer', '')[:100])
            debug_dump("LLM INPUT (extract_parsed_belief): from_node_id", from_node_id)
            debug_dump("LLM INPUT (extract_parsed_belief): to_node_id", to_node_id)
        
        # Extract parsed belief
        parsed_belief = self.extractor.extract_parsed_belief(qa_pair, from_node_id, to_node_id)
        
        # Log output for debugging
        if config.DEBUG_LLM_IO and parsed_belief:
            debug_dump("LLM OUTPUT (extract_parsed_belief)", parsed_belief)
        
        return parsed_belief 