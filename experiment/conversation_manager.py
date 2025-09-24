"""
Conversation Manager for Chatbot-Agent Interaction Experiment
Manages the conversation flow between the chatbot and a custom Python agent
"""
import json
import uuid
import time
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Configure logging to only show errors
logging.basicConfig(level=logging.ERROR)

# Load environment variables from .env files
parent_dir = Path(__file__).parent.parent
env_path = parent_dir / '.env'
env_local_path = parent_dir / '.env.local'

if env_local_path.exists():
    load_dotenv(dotenv_path=env_local_path)
elif env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Add parent directory to path to import backend modules
parent_dir_str = str(parent_dir)
sys.path.append(parent_dir_str)
sys.path.append(os.path.join(parent_dir_str, 'backend'))

from llm_extractor import QwenLLMExtractor
from cbn_manager import CBNManager
from question_generator import QuestionGenerator
from guiding_questions import GuidingQuestionsManager


class ConversationManager:
    """Manages conversation between chatbot and agent"""
    
    def __init__(self, topic="climate change", max_qa_count=20):
        """
        Initialize conversation manager
        
        Args:
            topic: The topic for the conversation
            max_qa_count: Maximum number of QA pairs before ending
        """
        self.topic = topic
        self.max_qa_count = max_qa_count
        self.session_id = f"exp_{uuid.uuid4().hex[:8]}"
        self.qa_pairs = []
        self.cbn = None
        self.current_index = 0
        
        # Initialize backend components
        self.extractor = QwenLLMExtractor(
            api_key=os.getenv('DASHSCOPE_API_KEY'),
            model="qwen-flash",
            temperature=0.01
        )
        self.cbn_manager = CBNManager()
        self.cbn_manager.set_llm_extractor(self.extractor)
        self.question_generator = QuestionGenerator()
        self.guiding_questions_manager = GuidingQuestionsManager()
        
        # Track used guiding questions
        self.used_guiding_questions = set()
        
        # Initialize CBN with stance node
        self._initialize_cbn()
        
    def _initialize_cbn(self):
        """Initialize CBN with stance node"""
        stance_node_id = "n1"
        stance_label = f"Support for {self.topic}"
        
        self.cbn = {
            "agent_id": "experiment_agent",
            "timestamp": int(time.time() * 1000),
            "nodes": {
                stance_node_id: {
                    "label": stance_label,
                    "aggregate_confidence": 1.0,
                    "evidence": [{"qa_id": "system", "confidence": 1.0, "importance": 1.0}],
                    "importance": 1.0,
                    "incoming_edges": [],
                    "outgoing_edges": [],
                    "status": "anchor",
                    "frequency": 1,
                    "is_stance": True
                }
            },
            "edges": {},
            "qa_history": {},
            "stance_node_id": stance_node_id,
            "step": "node_discovery",
            "anchor_queue": [stance_node_id],
            "node_counter": 1,
            "edge_counter": 0,
            "qa_counter": 0
        }
        
    def generate_initial_question(self):
        """Generate the initial question using guiding questions"""
        # Map camera to surveillance
        topic_key = "surveillance" if self.topic == "camera" else self.topic
        return self.guiding_questions_manager.get_initial_question(topic_key)
        
    def process_answer(self, question, answer):
        """
        Process an answer and generate follow-up questions
        
        Args:
            question: The question that was asked
            answer: The agent's answer
            
        Returns:
            dict: Response containing follow-up questions and updated causal graph
        """
        # Create QA pair
        qa_pair = {
            "id": f"qa_{self.current_index}",
            "question": question["question"],
            "answer": answer,
            "shortText": question.get("shortText", "")
        }
        
        self.qa_pairs.append(qa_pair)
        
        # Update CBN with QA pair
        self.cbn = self._update_cbn_with_qa(qa_pair)
        
        # Generate follow-up questions
        follow_up_questions = self._generate_follow_up_questions()
        
        self.current_index += 1
        
        return {
            "followUpQuestions": follow_up_questions,
            "causalGraph": self.cbn,
            "qaCount": len(self.qa_pairs),
            "maxQaCount": self.max_qa_count
        }
        
    def _update_cbn_with_qa(self, qa_pair):
        """Update CBN with QA pair (simplified from backend)"""
        # Determine current step
        current_step = self.cbn.get("step", "node_discovery")
        
        # Generate QA ID
        self.cbn["qa_counter"] = self.cbn.get("qa_counter", 0) + 1
        qa_id = f"qa{self.cbn['qa_counter']}"
        qa_pair["id"] = qa_id
        
        # Extract nodes
        new_nodes = self.extractor.extract_nodes(qa_pair, ensure_stance_node=False)
        
        # Process new nodes
        if new_nodes:
            for node_id, node in new_nodes.items():
                node_label = node.get('label', '')
                
                # Check if similar node exists
                existing_node_id = None
                for existing_id, existing_node in self.cbn['nodes'].items():
                    if existing_node.get('label', '').lower() == node_label.lower():
                        existing_node_id = existing_id
                        break
                
                if existing_node_id:
                    # Update existing node
                    existing_node = self.cbn['nodes'][existing_node_id]
                    existing_node['frequency'] = existing_node.get('frequency', 1) + 1
                    
                    # Add evidence
                    if 'evidence' not in existing_node:
                        existing_node['evidence'] = []
                    
                    existing_node['evidence'].append({
                        "qa_id": qa_id,
                        "confidence": node.get('aggregate_confidence', 0.5),
                        "importance": node.get('importance', 0.5)
                    })
                else:
                    # Create new node
                    self.cbn['node_counter'] += 1
                    new_node_id = f"n{self.cbn['node_counter']}"
                    
                    self.cbn['nodes'][new_node_id] = {
                        "label": node_label,
                        "aggregate_confidence": node.get('aggregate_confidence', 0.5),
                        "importance": node.get('importance', 0.5),
                        "evidence": [{
                            "qa_id": qa_id,
                            "confidence": node.get('aggregate_confidence', 0.5),
                            "importance": node.get('importance', 0.5)
                        }],
                        "incoming_edges": [],
                        "outgoing_edges": [],
                        "status": "candidate",
                        "frequency": 1,
                        "is_stance": False
                    }
        
        # Extract edge if we have enough nodes
        if len(new_nodes) >= 2:
            edge = self.extractor.extract_edge(qa_pair, new_nodes)
            if edge:
                self.cbn, edge_id = self.cbn_manager.add_edge(self.cbn, edge)
        
        # Merge graph components
        self.cbn = self.cbn_manager.merge_graph_components(self.cbn)
        
        # Check for node promotion
        self.cbn_manager._check_node_promotion(self.cbn)
        
        # Add QA to history
        self.cbn['qa_history'][qa_id] = {
            "question": qa_pair["question"],
            "answer": qa_pair["answer"],
            "shortText": qa_pair.get("shortText", ""),
            "timestamp": int(time.time())
        }
        
        return self.cbn
        
    def _generate_follow_up_questions(self):
        """Generate follow-up questions, prioritizing guiding questions"""
        # Check if we've reached max QA count
        if len(self.qa_pairs) >= self.max_qa_count:
            return []
        
        follow_up_questions = []
        
        # First, try to use remaining guiding questions
        topic_key = "surveillance" if self.topic == "camera" else self.topic
        guiding_questions = self.guiding_questions_manager.get_follow_up_questions(
            topic_key, self.used_guiding_questions
        )
        
        if guiding_questions and len(self.qa_pairs) < 8:  # Use guiding questions for first 8 QAs
            # Take the next guiding question
            next_guiding = guiding_questions[0]
            self.used_guiding_questions.add(next_guiding["id"])
            follow_up_questions.append(next_guiding)
        
        # If no guiding questions available or we've used enough, generate dynamic questions
        if not follow_up_questions:
            # Get current step
            current_step = self.cbn_manager.get_next_step(self.cbn)
            
            # Collect existing questions
            existing_question_info = []
            for qa in self.qa_pairs:
                existing_question_info.append({
                    "id": qa.get("id", ""),
                    "question": qa.get("question", ""),
                    "shortText": qa.get("shortText", "")
                })
            
            # Generate follow-up questions
            dynamic_questions = self.question_generator.generate_follow_up_questions(
                self.cbn,
                current_step,
                self.cbn.get("anchor_queue", []),
                existing_question_info,
                current_qa_count=len(self.qa_pairs),
                max_qa_count=self.max_qa_count,
                current_index=self.current_index,
                total_qa_count=self.max_qa_count
            )
            follow_up_questions.extend(dynamic_questions)
        
        return follow_up_questions
        
    def is_conversation_complete(self):
        """Check if conversation should end"""
        return len(self.qa_pairs) >= self.max_qa_count or (
            hasattr(self, 'last_response') and 
            not self.last_response.get('followUpQuestions')
        )
    
    def get_cbn(self):
        """Get the current CBN state"""
        return self.cbn
        
    def export_conversation(self, output_dir="experiment/exports"):
        """Export conversation and causal graph"""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export conversation
        conversation_file = f"{output_dir}/conversation_{self.session_id}_{timestamp}.json"
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump({
                "session_id": self.session_id,
                "topic": self.topic,
                "timestamp": timestamp,
                "qa_pairs": self.qa_pairs,
                "total_qa_count": len(self.qa_pairs)
            }, f, indent=2, ensure_ascii=False)
            
        # Export causal graph
        graph_file = f"{output_dir}/causal_graph_{self.session_id}_{timestamp}.json"
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(self.cbn, f, indent=2, ensure_ascii=False)
            
        print(f"Exported conversation to: {conversation_file}")
        print(f"Exported causal graph to: {graph_file}")
        
        return conversation_file, graph_file
