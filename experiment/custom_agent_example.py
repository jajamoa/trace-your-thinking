"""
Example of a custom agent implementation
Shows how to create an agent with specific behavior patterns
"""
from agent_interface import BaseAgent
import random


class CustomAgent(BaseAgent):
    """
    Example custom agent with configurable responses
    """
    
    def __init__(self, agent_id="custom_agent", stance="supportive"):
        """
        Initialize custom agent
        
        Args:
            agent_id: Agent identifier
            stance: Agent's stance on the topic ('supportive', 'opposed', 'neutral')
        """
        super().__init__(agent_id)
        self.stance = stance
        
        # Define response patterns based on stance
        self.response_patterns = self._initialize_response_patterns()
        
    def _initialize_response_patterns(self):
        """Initialize response patterns based on stance"""
        if self.stance == "supportive":
            return {
                "initial": [
                    "I strongly believe this is a critical issue that requires immediate attention.",
                    "This topic is one of the most important challenges we face today."
                ],
                "factors": [
                    "Key factors include policy effectiveness, public awareness, and technological innovation.",
                    "Economic incentives, regulatory frameworks, and social movements all play crucial roles."
                ],
                "relationships": {
                    "positive": "This has a strong positive effect, driving progress forward.",
                    "negative": "This creates significant barriers that we need to overcome."
                }
            }
        elif self.stance == "opposed":
            return {
                "initial": [
                    "I have serious concerns about the current approach to this issue.",
                    "I believe we need to reconsider our assumptions about this topic."
                ],
                "factors": [
                    "We should consider economic impacts, individual freedoms, and unintended consequences.",
                    "Cost-benefit analysis, market dynamics, and personal choice are key factors."
                ],
                "relationships": {
                    "positive": "This relationship is often overstated in the current discourse.",
                    "negative": "The negative impacts here are more significant than commonly acknowledged."
                }
            }
        else:  # neutral
            return {
                "initial": [
                    "This is a complex issue with valid arguments on multiple sides.",
                    "I see both benefits and drawbacks to different approaches here."
                ],
                "factors": [
                    "We need to balance environmental, economic, and social considerations.",
                    "Scientific evidence, economic feasibility, and public opinion all matter."
                ],
                "relationships": {
                    "positive": "There's a moderate positive correlation, though context matters.",
                    "negative": "This presents challenges, but they may be manageable with proper planning."
                }
            }
            
    def process_question(self, question):
        """
        Process question and generate stance-appropriate response
        
        Args:
            question: Question dict
            
        Returns:
            str: Agent's response
        """
        q_text = question.get("question", "").lower()
        q_type = question.get("type", "")
        
        # Initial thoughts question
        if q_type == "initial" or "thoughts" in q_text or "perspective" in q_text:
            return random.choice(self.response_patterns["initial"])
            
        # Factor-related questions
        elif "factors" in q_text or "influence" in q_text or "affect" in q_text:
            base_response = random.choice(self.response_patterns["factors"])
            
            # Add specific examples based on what's being asked
            if "economic" in q_text:
                if self.stance == "supportive":
                    return base_response + " Economic factors particularly drive innovation and job creation in new sectors."
                elif self.stance == "opposed":
                    return base_response + " Economic costs often outweigh the proposed benefits."
                else:
                    return base_response + " Economic impacts vary significantly across different sectors and regions."
            else:
                return base_response
                    
        # Relationship questions
        elif "relationship" in q_text or "effect" in q_text or "connection" in q_text:
            # Determine if asking about positive or negative relationship
            if any(word in q_text for word in ["increase", "support", "promote", "positive"]):
                response = self.response_patterns["relationships"]["positive"]
            elif any(word in q_text for word in ["decrease", "hinder", "negative", "reduce"]):
                response = self.response_patterns["relationships"]["negative"]
            else:
                # Mix of both
                response = f"{self.response_patterns['relationships']['positive']} However, {self.response_patterns['relationships']['negative'].lower()}"
                
            return response
            
        # Default response
        else:
            if self.stance == "supportive":
                return "This aspect reinforces the importance of taking comprehensive action."
            elif self.stance == "opposed":
                return "This raises additional concerns about the current approach."
            else:
                return "This adds another layer of complexity to consider."


# Example usage
if __name__ == "__main__":
    # Create agents with different stances
    supportive_agent = CustomAgent(agent_id="supporter", stance="supportive")
    opposed_agent = CustomAgent(agent_id="opponent", stance="opposed")
    neutral_agent = CustomAgent(agent_id="neutral", stance="neutral")
    
    # Test question
    test_question = {
        "id": "q1",
        "question": "What are your thoughts on climate change?",
        "shortText": "Initial thoughts",
        "type": "initial"
    }
    
    print("Same question, different agents:\n")
    print(f"Supportive Agent: {supportive_agent.process_question(test_question)}")
    print(f"\nOpposed Agent: {opposed_agent.process_question(test_question)}")
    print(f"\nNeutral Agent: {neutral_agent.process_question(test_question)}")
