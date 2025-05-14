"""
Session Manager for CBN System
Manages session-specific data including CBNs and node candidate queues.
"""

import logging
from collections import Counter, defaultdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Singleton class to manage session data across the application.
    Stores CBNs and node candidate queues for each session.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            # Initialize data structures
            cls._instance._session_cbns = {}
            cls._instance._session_node_candidates = defaultdict(Counter)
            cls._instance._session_last_activity = {}
            cls._instance._cleanup_threshold = 24 * 60 * 60  # 24 hours in seconds
            logger.info("Session Manager initialized")
        return cls._instance

    def get_cbn(self, session_id):
        """
        Get the CBN for a specific session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            object: The CBN for the session or None if not found
        """
        self._update_session_activity(session_id)
        return self._session_cbns.get(session_id)

    def set_cbn(self, session_id, cbn):
        """
        Set the CBN for a specific session.
        
        Args:
            session_id (str): Session identifier
            cbn (object): The CBN object to store
        """
        self._update_session_activity(session_id)
        self._session_cbns[session_id] = cbn
        logger.info(f"CBN updated for session {session_id}")

    def get_node_candidates(self, session_id):
        """
        Get the node candidates for a specific session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            Counter: The node candidates counter for the session
        """
        self._update_session_activity(session_id)
        return self._session_node_candidates[session_id]

    def update_node_candidates(self, session_id, node_candidates):
        """
        Update the node candidates for a specific session.
        
        Args:
            session_id (str): Session identifier
            node_candidates (Counter): The node candidates counter
        """
        self._update_session_activity(session_id)
        self._session_node_candidates[session_id] = node_candidates
        logger.info(f"Node candidates updated for session {session_id}")

    def increment_node_candidate(self, session_id, node_label, count=1):
        """
        Increment a specific node candidate count for a session.
        
        Args:
            session_id (str): Session identifier
            node_label (str): The node label to increment
            count (int, optional): The count to increment by. Defaults to 1.
        """
        self._update_session_activity(session_id)
        self._session_node_candidates[session_id][node_label] += count
        logger.info(f"Incremented node '{node_label}' for session {session_id}")
        return self._session_node_candidates[session_id]

    def clear_session(self, session_id):
        """
        Clear all data for a specific session.
        
        Args:
            session_id (str): Session identifier
        """
        if session_id in self._session_cbns:
            del self._session_cbns[session_id]
        
        if session_id in self._session_node_candidates:
            del self._session_node_candidates[session_id]
            
        if session_id in self._session_last_activity:
            del self._session_last_activity[session_id]
            
        logger.info(f"Cleared data for session {session_id}")

    def cleanup_inactive_sessions(self):
        """
        Remove data for inactive sessions to prevent memory leaks.
        """
        current_time = time.time()
        inactive_sessions = []
        
        for session_id, last_activity in self._session_last_activity.items():
            if current_time - last_activity > self._cleanup_threshold:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            self.clear_session(session_id)
            
        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
            logger.info(f"Current active sessions: {len(self._session_last_activity)}")
        
        return inactive_sessions

    def _update_session_activity(self, session_id):
        """
        Update the last activity timestamp for a session.
        
        Args:
            session_id (str): Session identifier
        """
        self._session_last_activity[session_id] = time.time()


# Global session manager instance
session_manager = SessionManager() 