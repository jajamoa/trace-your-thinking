from flask import Blueprint, request, jsonify, current_app
from typing import Dict, List, Any, Tuple, Optional
import time
import traceback

# Use absolute imports instead of relative imports
from config import config
from services.llm_service import LLMService
from services.cbn_service import CBNService
from services.question_service import QuestionService
from utils.logging import logger, debug_dump, log_exception, log_phase_header, log_section_header, log_separator
from utils.helpers import get_timestamp, validate_request_data, extract_question_texts, filter_valid_questions

# Create Blueprint
cbn_bp = Blueprint('cbn', __name__)

# Create a dictionary to store session-specific LLMService instances
_llm_services = {}
# Shared service instances
_cbn_service = None
_question_service = None
# Last cleanup timestamp
_last_cleanup_time = time.time()
# Cleanup interval (12 hours)
_cleanup_interval = 12 * 60 * 60

def cleanup_llm_services():
    """
    Remove inactive LLMService instances to prevent memory leaks.
    Called periodically during API requests.
    """
    global _llm_services, _last_cleanup_time
    
    current_time = time.time()
    # Only run cleanup if enough time has passed
    if current_time - _last_cleanup_time < _cleanup_interval:
        return
    
    # Import session manager to use its utilities
    from session_manager import session_manager
    
    # Trigger session manager cleanup and get inactive sessions
    inactive_sessions = session_manager.cleanup_inactive_sessions()
    
    # Remove inactive services
    services_removed = 0
    for session_id in inactive_sessions:
        if session_id in _llm_services:
            del _llm_services[session_id]
            services_removed += 1
    
    # Also check for any LLMServices without corresponding session data
    orphaned_services = []
    for session_id in _llm_services.keys():
        if session_id not in session_manager._session_last_activity:
            orphaned_services.append(session_id)
    
    # Remove orphaned services
    for session_id in orphaned_services:
        del _llm_services[session_id]
        services_removed += 1
    
    # Update cleanup timestamp
    _last_cleanup_time = current_time
    
    if services_removed > 0:
        logger.info(f"Cleaned up {services_removed} inactive LLMService instances (including {len(orphaned_services)} orphaned)")
        logger.info(f"Current active LLMService count: {len(_llm_services)}")

def get_services(session_id=None):
    """
    Get or initialize service instances.
    Always creates/retrieves a session-specific LLMService.
    
    Args:
        session_id (str, optional): Session identifier for persistent node tracking
    
    Returns:
        Tuple containing LLMService, CBNService, and QuestionService instances
    """
    global _llm_services, _cbn_service, _question_service
    
    # Periodically clean up inactive services
    cleanup_llm_services()
    
    # Create or retrieve session-specific LLMService
    if session_id:
        if session_id not in _llm_services:
            logger.info(f"Creating new LLMService for session: {session_id}")
            _llm_services[session_id] = LLMService(session_id=session_id)
        llm_service = _llm_services[session_id]
    else:
        # Fallback for requests without session_id
        logger.warning("No session_id provided, creating temporary LLMService")
        llm_service = LLMService()
    
    # Initialize shared services if needed
    if _cbn_service is None:
        _cbn_service = CBNService()
        
    if _question_service is None:
        _question_service = QuestionService()
        
    return llm_service, _cbn_service, _question_service

@cbn_bp.route('/api/process_answer', methods=['POST'])
def process_answer():
    """
    Process answer API - Implementing CBN construction from QA pairs.
    """
    try:
        # Use a single log header for the request
        request_id = f"req_{int(time.time()*1000)}"
        log_phase_header(f"PROCESS ANSWER API [{request_id}]")
        
        # Get request data
        data = request.json
        if not data:
            logger.warning("No data received")
            return jsonify({"error": "No data received"}), 400
        
        # Debug dump incoming request
        debug_dump("Incoming request data", data)
        
        # Validate required fields
        is_valid, missing_params = validate_request_data(data)
        if not is_valid:
            logger.warning(f"Missing required parameters: {', '.join(missing_params)}")
            return jsonify({"error": f"Missing required parameters: {', '.join(missing_params)}"}), 400
        
        # Extract parameters
        session_id = data.get('sessionId')
        prolific_id = data.get('prolificId')
        qa_pair = data.get('qaPair')
        qa_pairs = data.get('qaPairs', [])
        current_index = data.get('currentQuestionIndex', 0)
        existing_causal_graph = data.get('existingCausalGraph')
        
        # Get services with session_id
        llm_service, cbn_service, question_service = get_services(session_id=session_id)
        
        # Log processing info once
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        log_section_header(f"Processing QA Pair {current_index + 1}/{len(qa_pairs)}")
        logger.info(f"Session: {session_id}, User: {prolific_id}")
        logger.info(f"Question: {question[:50]}...")
        logger.info(f"Answer: {answer[:50]}...")
        
        # Get current question texts
        current_question_texts = extract_question_texts(qa_pair, qa_pairs)
        
        # CBN retrieval operation with one log header
        log_section_header("CBN Retrieval/Creation")
        cbn = cbn_service.get_cbn(session_id, prolific_id, existing_causal_graph)
        
        # Process QA pair and update CBN
        log_section_header("CBN Update")
        updated_cbn = cbn_service.update_cbn_with_qa(
            cbn, 
            qa_pair, 
            llm_service,
            verbose_logging=False
        )
        
        # Follow-up question generation
        log_section_header("Follow-up Question Generation")
        follow_up_questions = question_service.generate_follow_up_questions(
            updated_cbn,
            current_question_texts
        )
        
        # Process results
        total_qa_count = len(qa_pairs)
        
        logger.info(f"Current QA count: {total_qa_count}")
        
        # Check if more questions are needed
        if total_qa_count < 30:
            # If we haven't reached 30 QAs yet, ensure we have follow-ups
            if not follow_up_questions:
                logger.info("Forcing follow-up question generation to reach minimum QA count")
                follow_up_questions = question_service.generate_additional_questions(
                    updated_cbn,
                    current_question_texts,
                    force_generate=True
                )
                logger.info(f"Generated {len(follow_up_questions)} forced follow-up questions")
            
            logger.info(f"Generated {len(follow_up_questions)} follow-up questions (QA count: {total_qa_count}/30)")
        else:
            # Check if we should terminate based on CBN completeness
            should_terminate = cbn_service.check_termination(updated_cbn)
            
            # Limit follow-ups only if near the end AND CBN is complete
            remaining_questions = total_qa_count - current_index - 1
            if should_terminate and remaining_questions <= 3:
                follow_up_questions = []  # No more follow-ups when complete
                logger.info("CBN is complete, no more follow-up questions needed")
            elif remaining_questions <= 5:
                follow_up_questions = follow_up_questions[:1]  # Just one follow-up for near-end questions
                logger.info(f"Near end of interview, limited to 1 follow-up question")
            else:
                logger.info(f"Generated {len(follow_up_questions)} follow-up questions")
        
        # Return response
        log_section_header("API Response")
        response = {
            "success": True,
            "sessionId": session_id,
            "prolificId": prolific_id,
            "qaPair": qa_pair,
            "followUpQuestions": follow_up_questions,
            "causalGraph": updated_cbn.to_dict(),
            "timestamp": get_timestamp()
        }
        logger.info(f"Returning response with {len(follow_up_questions)} follow-up questions")
        log_separator()
        
        return jsonify(response)
        
    except Exception as e:
        # Log exception with traceback
        log_exception(e)
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "success": False
        }), 500 