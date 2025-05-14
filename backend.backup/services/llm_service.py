from typing import Dict, List, Any, Optional
import os

# Use absolute imports instead of relative imports
from config import config
from utils.logging import logger, debug_dump
from services.question_service import QuestionService

class LLMService:
    """Minimal LLM service for CBN construction using a two-step interview framework."""
    
    def __init__(self, session_id=None):
        """
        Initialize the LLM service.
        
        Args:
            session_id (str, optional): Session identifier for persistently tracking node candidates.
        """
        try:
            from llm_extractor import QwenLLMExtractor
            
            self.extractor = QwenLLMExtractor(
                api_key=config.DASHSCOPE_API_KEY,
                model=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE
            )
            logger.info(f"Initialized LLM service with model: {config.LLM_MODEL}")
            
            # Store session ID
            self.session_id = session_id
            if session_id:
                logger.info(f"LLM service initialized with session ID: {session_id}")
            
            # Initialize the question service
            self.question_service = QuestionService()
            
            # Track initial extraction
            self.initial_extraction_done = False
        except ImportError as e:
            logger.error(f"Import error initializing LLM service: {str(e)}")
            self.extractor = None
            self.question_service = None
            self.initial_extraction_done = False
            self.session_id = None
    
    def extract_causal_data(self, qa_pair: Dict[str, Any], step: int = 1) -> Dict[str, Any]:
        """
        Extract causal data for CBN construction based on the current step.
        
        Args:
            qa_pair: The QA pair to extract causal data from
            step: Current interview step (1=Node Discovery, 2=Relationship Construction)
            
        Returns:
            Dict[str, Any]: Dictionary containing nodes and relations
        """
        if not self.extractor:
            logger.error("LLM extractor not initialized")
            return {"nodes": {}, "relations": []}
        
        # Log basic input information
        if config.DEBUG_LLM_IO:
            debug_dump(f"LLM INPUT (Step {step}): Question", qa_pair.get('question', '')[:100])
            debug_dump(f"LLM INPUT (Step {step}): Answer", qa_pair.get('answer', '')[:100])
        
        try:
            # Step-specific extraction strategy
            if step == 1:
                # Check if this is the initial extraction
                ensure_stance = not self.initial_extraction_done
                
                # Mark that we've done the initial extraction
                if not self.initial_extraction_done:
                    self.initial_extraction_done = True
                    logger.info("Initial extraction - will create stance node if needed")
                
                # Step 1: Node Discovery & Establishment - focus on extracting key entities
                return self._extract_step1_data(qa_pair, ensure_stance)
            elif step == 2:
                # Step 2: Relationship Construction - focus on causal relationships and their properties
                return self._extract_step2_data(qa_pair)
            else:
                logger.warning(f"Unknown step {step}, defaulting to step 1")
                return self._extract_step1_data(qa_pair, False)  # Don't ensure stance for unknown steps
                
        except Exception as e:
            logger.error(f"Error extracting causal data: {str(e)}")
            return {"nodes": {}, "relations": []}
    
    def _extract_step1_data(self, qa_pair: Dict[str, Any], ensure_stance: bool = False) -> Dict[str, Any]:
        """
        Step 1: Node Discovery & Establishment
        Focus on extracting key entities and ensuring stance node creation
        
        Args:
            qa_pair: The QA pair to extract data from
            ensure_stance: Whether to ensure a stance node is created (only for first extraction)
        """
        # Extract nodes with stance prioritization only on initial extraction
        nodes_result = self.extractor.extract_nodes(qa_pair, ensure_stance_node=ensure_stance, session_id=self.session_id)
        
        # Prepare results in simplified format
        nodes = {}
        relations = []
        
        # Process nodes with basic granularity control
        for node_id, node_data in nodes_result.items():
            label = node_data.get('label', '').lower()
            
            # Basic semantic role classification
            semantic_role = node_data.get('semantic_role', 'unknown')
            is_stance = node_data.get('is_stance', False)
            
            # Add node with confidence and metadata (simplified schema)
            nodes[label] = {
                'confidence': node_data.get('confidence', 0.9),
                'is_stance': is_stance
            }
        
        return {
            'nodes': nodes,
            'relations': relations
        }
    
    def _extract_step2_data(self, qa_pair: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Relationship Construction
        Focus on causal relationships between established nodes and their properties
        """
        # First extract nodes to ensure they exist (but don't create stance node)
        nodes_result = self.extractor.extract_nodes(qa_pair, ensure_stance_node=False, session_id=self.session_id)
        
        # Then extract edges with directional information
        edge_result = self.extractor.extract_edge(qa_pair, session_id=self.session_id)
        
        # Prepare results with simplified schema
        nodes = {}
        relations = []
        
        # Process nodes
        for node_id, node_data in nodes_result.items():
            label = node_data.get('label', '').lower()
            nodes[label] = {
                'confidence': node_data.get('confidence', 0.9)
            }
        
        # Process relation if found
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
                
                # Create relation with simplified schema
                relation = {
                    'source_label': from_label,
                    'target_label': to_label,
                    'confidence': edge_result.get('strength', 0.9),
                    'modifier': min(max(edge_result.get('strength', 0.5) * 2 - 1, -1.0), 1.0)
                }
                
                relations.append(relation)
        
        return {
            'nodes': nodes,
            'relations': relations
        }
    
    def generate_follow_up_questions(self, cbn: Dict[str, Any], current_question_texts: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generate follow-up questions based on the current CBN.
        
        Args:
            cbn: Current state of the CBN
            current_question_texts: List of existing questions to avoid duplication
            
        Returns:
            List[Dict[str, Any]]: List of generated questions with metadata
        """
        if not self.question_service:
            logger.error("Question service not initialized")
            return []
            
        # Convert dictionary CBN to CausalBayesianNetwork if needed
        from models.cbn import CausalBayesianNetwork
        if isinstance(cbn, dict) and not isinstance(cbn, CausalBayesianNetwork):
            try:
                # Create temporary CBN object for question generation
                agent_id = cbn.get('agent_id', 'temp_agent')
                temp_cbn = CausalBayesianNetwork(agent_id, cbn)
            except Exception as e:
                logger.error(f"Error converting CBN dict to object: {str(e)}")
                return []
        else:
            temp_cbn = cbn
            
        # Use QuestionService to generate questions
        try:
            if not current_question_texts:
                current_question_texts = []
                
            follow_up_questions = self.question_service.generate_follow_up_questions(
                temp_cbn, 
                current_question_texts
            )
            
            return follow_up_questions
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
            return []
    
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
        nodes = self.extractor.extract_nodes(qa_pair, ensure_stance_node=ensure_stance_node, session_id=self.session_id)
        
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
        edge = self.extractor.extract_edge(qa_pair, session_id=self.session_id)
        
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