"""
Python Agent Interface for Chatbot Interaction
This is a base interface that users can extend to implement custom agent logic
"""
from abc import ABC, abstractmethod
import json
import time


class BaseAgent(ABC):
    """Base class for custom Python agents"""
    
    def __init__(self, agent_id="custom_agent"):
        """
        Initialize the agent
        
        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id
        self.conversation_history = []
        
    @abstractmethod
    def process_question(self, question):
        """
        Process a question and generate a response
        This method must be implemented by custom agents
        
        Args:
            question: dict containing:
                - id: Question ID
                - question: The actual question text
                - shortText: Short description of the question
                - type: Question type
                
        Returns:
            str: The agent's answer to the question
        """
        pass
        
    def add_to_history(self, question, answer):
        """Add QA pair to conversation history"""
        self.conversation_history.append({
            "timestamp": time.time(),
            "question": question,
            "answer": answer
        })
        
    def get_conversation_history(self):
        """Get the full conversation history"""
        return self.conversation_history


class SimpleAgent(BaseAgent):
    """
    Simple example agent implementation
    This agent gives basic responses based on keywords
    """
    
    def __init__(self, agent_id="simple_agent"):
        super().__init__(agent_id)
        
    def process_question(self, question):
        """
        Simple implementation that generates basic responses
        
        Args:
            question: Question dict
            
        Returns:
            str: Simple answer
        """
        q_text = question.get("question", "").lower()
        
        # Simple keyword-based responses
        if "climate change" in q_text:
            return "I believe climate change is a significant global challenge that requires immediate action through both policy changes and individual responsibility."
            
        elif "factors" in q_text or "influence" in q_text:
            return "Several factors influence this issue, including economic considerations, scientific evidence, political will, and public awareness."
            
        elif "relationship" in q_text or "affect" in q_text:
            if "economic" in q_text:
                return "Economic factors have a strong positive influence on policy decisions, as they determine feasibility and public support."
            elif "scientific" in q_text:
                return "Scientific evidence strongly supports the need for action, though its influence on policy can be moderated by political factors."
            else:
                return "These factors are interconnected, with each having varying degrees of influence depending on the context."
                
        elif "important" in q_text:
            return "The most important aspect is finding a balance between environmental protection and economic sustainability."
            
        else:
            return "This is a complex issue with multiple dimensions that need to be considered holistically."


class InteractiveAgent(BaseAgent):
    """
    Interactive agent that can be controlled manually
    Useful for testing and debugging
    """
    
    def __init__(self, agent_id="interactive_agent"):
        super().__init__(agent_id)
        
    def process_question(self, question):
        """
        Display question and wait for manual input
        
        Args:
            question: Question dict
            
        Returns:
            str: User-provided answer
        """
        print("\n" + "="*50)
        print(f"AGENT RECEIVED QUESTION:")
        print(f"Type: {question.get('type', 'unknown')}")
        print(f"Short: {question.get('shortText', '')}")
        print(f"Question: {question.get('question', '')}")
        print("="*50)
        
        # Get answer from user
        print("\nPlease provide the agent's answer:")
        answer = input("> ")
        
        if not answer.strip():
            answer = "I need more time to think about this question."
            
        return answer
