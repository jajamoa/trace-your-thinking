import time
from typing import Dict, List, Any, Optional, Tuple

def get_timestamp() -> int:
    """
    Get current timestamp in seconds.
    
    Returns:
        int: Current timestamp
    """
    return int(time.time())

def validate_request_data(data: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
    """
    Validate request data for required fields.
    
    Args:
        data: Request data to validate
        
    Returns:
        Tuple containing:
            bool: Whether the data is valid
            Optional[List[str]]: List of missing parameters if any
    """
    missing_params = []
    required_fields = ['sessionId', 'prolificId', 'qaPair']
    
    for field in required_fields:
        if field not in data or not data[field]:
            missing_params.append(field)
    
    return (len(missing_params) == 0, missing_params)

def extract_question_texts(qa_pair: Dict[str, Any], qa_pairs: List[Dict[str, Any]]) -> List[str]:
    """
    Extract all question texts from QA pairs to avoid duplication.
    
    Args:
        qa_pair: Current QA pair
        qa_pairs: All QA pairs in session
        
    Returns:
        List[str]: List of unique question texts
    """
    question_texts = []
    
    # Add current question if present
    if qa_pair and qa_pair.get('question'):
        question_texts.append(qa_pair.get('question'))
    
    # Add all questions from the session
    for pair in qa_pairs:
        if pair and pair.get('question') and pair.get('question') not in question_texts:
            question_texts.append(pair.get('question'))
    
    return question_texts

def filter_valid_questions(questions: List[Dict[str, Any]], 
                           current_phase: int) -> List[Dict[str, Any]]:
    """
    Filter out invalid or empty questions.
    
    Args:
        questions: List of question objects
        current_phase: Current SCM phase
        
    Returns:
        List[Dict[str, Any]]: Filtered list of valid questions
    """
    valid_questions = []
    
    for question in questions:
        if not isinstance(question, dict):
            continue
            
        question_text = question.get('question', '').strip()
        node_id = question.get('node_id')
        node_label = question.get('node_label')
        
        # Check for valid content
        has_valid_content = (len(question_text) > 15 and 
                            not question_text.startswith("placeholder") and
                            not question_text.startswith("TODO"))
        
        has_node_reference = node_id is not None or node_label is not None
        
        # Add default short text if missing
        if has_valid_content and not question.get('shortText'):
            if has_node_reference and node_label:
                question['shortText'] = f"About {node_label}"
            else:
                # Set a default topic based on current phase
                if current_phase == 1:
                    question['shortText'] = "About a new factor"
                elif current_phase == 2:
                    question['shortText'] = "About connections between factors"
                elif current_phase == 3:
                    question['shortText'] = "About factor relationships"
                else:
                    question['shortText'] = "Additional question"
                
        # Add node reference to question if available but not present
        if has_valid_content and node_label and node_label.lower() not in question_text.lower():
            question['question'] = f"Regarding {node_label}: {question_text}"
            
        # Only include valid questions
        if has_valid_content:
            valid_questions.append(question)
                
    return valid_questions 