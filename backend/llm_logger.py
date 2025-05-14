import os
import logging
import json

# Configure logger
logger = logging.getLogger(__name__)

# Define LLM call types
LLM_CALL_TYPES = {
    "NODE_EXTRACTION": "node_extraction",
    "EDGE_EXTRACTION": "edge_extraction",
    "FUNCTION_PARAMS": "function_params",
    "BELIEF_EXTRACTION": "belief_extraction",
    "TOPIC_EXTRACTION": "topic_extraction"
}

class LLMLogger:
    """Simple logger for LLM calls that supports selective logging by call type."""
    
    def __init__(self):
        """Initialize the LLM logger with settings from environment variables."""
        self.settings = {}
        self._load_settings()
    
    def _load_settings(self):
        """Load logging settings from environment variables."""
        # Global override
        global_debug = os.getenv('DEBUG_LLM_IO', 'false').lower() == 'true'
        
        # Set defaults for all call types based on global setting
        for call_type in LLM_CALL_TYPES.values():
            env_var_name = f'DEBUG_LLM_IO_{call_type.upper()}'
            type_specific = os.getenv(env_var_name)
            
            if type_specific is not None:
                self.settings[call_type] = type_specific.lower() == 'true'
            else:
                self.settings[call_type] = global_debug
    
    def should_log(self, call_type):
        """Check if logging is enabled for a specific call type."""
        return self.settings.get(call_type, False)
    
    def log_prompt(self, call_type, prompt):
        """Log the prompt if enabled for call type."""
        if self.should_log(call_type):
            logger.info(f"[{call_type.upper()}] PROMPT: {prompt}")
    
    def log_response(self, call_type, response):
        """Log the response if enabled for call type."""
        if self.should_log(call_type):
            # For API response objects
            if hasattr(response, 'status_code'):
                logger.info(f"[{call_type.upper()}] RESPONSE STATUS: {response.status_code}")
                
                if hasattr(response, 'output'):
                    try:
                        logger.info(f"[{call_type.upper()}] RESPONSE: {json.dumps(response.output, indent=2)}")
                    except:
                        logger.info(f"[{call_type.upper()}] RESPONSE: {response.output}")
            else:
                # For parsed/processed responses
                try:
                    logger.info(f"[{call_type.upper()}] RESPONSE: {json.dumps(response, indent=2)}")
                except:
                    logger.info(f"[{call_type.upper()}] RESPONSE: {response}")
    
    def log_separator(self, label=""):
        """
        Log a separator line to visually separate different requests in logs.
        
        Args:
            label (str, optional): Label to include in the separator
        """
        # Create a more visible separator with multiple lines
        separator_line = "=" * 80  # Longer separator line
        dash_line = "-" * 80  # Alternative dash line
        
        if label:
            # Format with label in the middle
            logger.info(f"{dash_line}")
            logger.info(f"{separator_line}")
            logger.info(f"{label.center(80)}")
            logger.info(f"{separator_line}")
            logger.info(f"{dash_line}")
        else:
            # Simple double separator without label
            logger.info(f"{dash_line}")
            logger.info(f"{separator_line}")
            logger.info(f"{dash_line}")
    
    def log_settings(self):
        """Log the current logging settings."""
        logger.info("LLM Logging Settings:")
        for call_type, enabled in self.settings.items():
            logger.info(f"  - {call_type.upper()}: {'ENABLED' if enabled else 'DISABLED'}")

# Create a singleton instance
llm_logger = LLMLogger() 