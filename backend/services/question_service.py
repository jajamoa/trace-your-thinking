from typing import Dict, List, Any, Optional, Union

# Use absolute imports instead of relative imports
from models.cbn import CausalBayesianNetwork
from utils.logging import logger
from utils.helpers import filter_valid_questions

class QuestionService:
    """Service for generating follow-up questions based on CBN state."""
    
    def __init__(self):
        """Initialize the question service."""
        # Import here to avoid circular imports
        try:
            from question_generator import QuestionGenerator
            self.generator = QuestionGenerator()
            logger.info("Initialized question service with QuestionGenerator")
        except ImportError:
            logger.error("Failed to import QuestionGenerator. Using built-in question generation.")
            self.generator = None
    
    def generate_follow_up_questions(self, cbn: CausalBayesianNetwork, 
                                     current_question_texts: List[str]) -> List[Dict[str, Any]]:
        """
        Generate follow-up questions based on CBN state.
        
        Args:
            cbn: Current CBN
            current_question_texts: Texts of existing questions to avoid duplication
            
        Returns:
            List[Dict[str, Any]]: List of follow-up questions
        """
        logger.info(f"Generating follow-up questions for CBN with {len(cbn.nodes)} nodes and {len(cbn.edges)} edges")
        
        # Determine phase based on CBN state
        phase_num = 1 if len(cbn.nodes) < 5 else 2  # Use phase 1 for node discovery, phase 2 for edge construction
        
        # Generate questions using external generator if available
        if self.generator:
            try:
                # Call external generator
                follow_up_questions = self.generator.generate_follow_up_questions(
                    cbn.to_dict(),
                    "node_discovery" if phase_num == 1 else "edge_construction",
                    list(cbn.nodes.keys()),  # Use node IDs as anchor nodes
                    current_question_texts
                )
                
                # Ensure we have a valid list
                if not isinstance(follow_up_questions, list):
                    logger.error(f"Generator returned non-list: {type(follow_up_questions)}")
                    follow_up_questions = []
                    
                # Filter valid questions
                follow_up_questions = filter_valid_questions(follow_up_questions, phase_num)
                
            except Exception as e:
                logger.error(f"Error generating follow-up questions: {str(e)}")
                follow_up_questions = []
                
        else:
            # Built-in simple question generation
            follow_up_questions = self._generate_default_questions(cbn, current_question_texts, phase_num)
        
        # Only log if we actually have questions to avoid redundant logs
        if follow_up_questions:
            logger.info(f"Generated {len(follow_up_questions)} follow-up questions")
        
        return follow_up_questions
    
    def generate_additional_questions(self, cbn: CausalBayesianNetwork, 
                                      current_question_texts: List[str],
                                      force_generate: bool = False,
                                      focus_on_nodes: bool = False) -> List[Dict[str, Any]]:
        """
        Generate additional questions when needed.
        
        Args:
            cbn: Current CBN
            current_question_texts: Texts of existing questions to avoid duplication
            force_generate: Whether to force question generation
            focus_on_nodes: Whether to focus on node discovery
            
        Returns:
            List[Dict[str, Any]]: List of additional questions
        """
        # Determine phase to use
        phase_num = 1 if focus_on_nodes or len(cbn.nodes) < 5 else 2
        phase_name = "node_discovery" if phase_num == 1 else "edge_construction"
        
        logger.info(f"Generating additional questions for phase: {phase_name} (force: {force_generate})")
        
        # Generate questions using external generator if available
        if self.generator:
            try:
                if focus_on_nodes or force_generate:
                    # Use focused generation
                    additional_questions = self.generator.generate_additional_questions(
                        cbn.to_dict(),
                        phase_name,
                        current_question_texts,
                        focus_on_nodes=focus_on_nodes,
                        force_generate=force_generate
                    )
                else:
                    # Use standard generation
                    additional_questions = self.generator.generate_follow_up_questions(
                        cbn.to_dict(),
                        phase_name,
                        list(cbn.nodes.keys()),  # Use node IDs as anchor nodes
                        current_question_texts
                    )
                
                # Ensure we have a valid list
                if not isinstance(additional_questions, list):
                    logger.error(f"Generator returned non-list: {type(additional_questions)}")
                    additional_questions = []
                    
                # Filter valid questions
                additional_questions = filter_valid_questions(additional_questions, phase_num)
                
            except Exception as e:
                logger.error(f"Error generating additional questions: {str(e)}")
                additional_questions = []
                
        else:
            # Built-in simple question generation
            additional_questions = self._generate_default_questions(cbn, current_question_texts, phase_num)
        
        # Only log if we have questions to return
        if additional_questions:
            logger.info(f"Generated {len(additional_questions)} additional questions")
        
        return additional_questions
    
    def _generate_default_questions(self, cbn: CausalBayesianNetwork, 
                                  current_question_texts: List[str],
                                  phase_num: int) -> List[Dict[str, Any]]:
        """
        Generate default questions when external generator is not available.
        
        Args:
            cbn: Current CBN
            current_question_texts: Texts of existing questions to avoid duplication
            phase_num: Current phase number
            
        Returns:
            List[Dict[str, Any]]: List of default questions
        """
        questions = []
        
        if phase_num == 1:  # Node discovery
            # Generate questions about potential nodes
            if len(cbn.nodes) < 3:
                # Initial questions to establish nodes
                generic_questions = [
                    "What factors do you think influence this issue the most?",
                    "What are the key considerations in your decision-making about this topic?",
                    "Could you explain what aspects of this situation are most important to you?"
                ]
                
                for q in generic_questions:
                    if q not in current_question_texts:
                        questions.append({
                            "question": q,
                            "shortText": "About key factors"
                        })
                        if len(questions) >= 2:
                            break
            else:
                # Questions about specific nodes
                for node_id, node in list(cbn.nodes.items())[:5]:
                    node_label = node.get('label', '')
                    if len(node_label) > 2:
                        q = f"Could you tell me more about how {node_label} factors into your thinking?"
                        if q not in current_question_texts:
                            questions.append({
                                "question": q,
                                "shortText": f"About {node_label}",
                                "node_id": node_id,
                                "node_label": node_label
                            })
                            if len(questions) >= 2:
                                break
                                
        elif phase_num == 2:  # Edge construction
            # Generate questions about relationships between nodes
            node_list = list(cbn.nodes.items())
            
            if len(node_list) >= 2:
                for i in range(min(3, len(node_list))):
                    node1_id, node1 = node_list[i]
                    for j in range(i+1, min(5, len(node_list))):
                        node2_id, node2 = node_list[j]
                        
                        node1_label = node1.get('label', '')
                        node2_label = node2.get('label', '')
                        
                        if len(node1_label) > 2 and len(node2_label) > 2:
                            q = f"How do you think {node1_label} and {node2_label} relate to each other?"
                            if q not in current_question_texts:
                                questions.append({
                                    "question": q,
                                    "shortText": f"About {node1_label} & {node2_label}",
                                    "node_id": node1_id,
                                    "node_label": node1_label
                                })
                                if len(questions) >= 2:
                                    break
                    if len(questions) >= 2:
                        break
        
        # Ensure we have at least one question
        if not questions:
            questions.append({
                "question": "Could you share more about your thoughts on this topic?",
                "shortText": "Additional insights"
            })
        
        return questions 