"""
Experiment Runner for Chatbot-Agent Conversation
Orchestrates the conversation between chatbot and agent
"""
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env files
parent_dir = Path(__file__).parent.parent
env_path = parent_dir / '.env'
env_local_path = parent_dir / '.env.local'

if env_local_path.exists():
    load_dotenv(dotenv_path=env_local_path)
elif env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Add parent directory to path for imports
sys.path.append(str(parent_dir))

from conversation_manager import ConversationManager
from agent_interface import SimpleAgent, InteractiveAgent


class ExperimentRunner:
    """Runs the chatbot-agent conversation experiment"""
    
    def __init__(self, agent, topic="climate change", max_qa_count=20, verbose=True):
        """
        Initialize experiment runner
        
        Args:
            agent: The agent instance to use
            topic: Conversation topic
            max_qa_count: Maximum number of QA pairs
            verbose: Whether to print detailed output
        """
        self.agent = agent
        self.topic = topic
        self.max_qa_count = max_qa_count
        self.verbose = verbose
        
        # Initialize conversation manager
        self.conversation_manager = ConversationManager(
            topic=topic,
            max_qa_count=max_qa_count
        )
        
    def run(self):
        """Run the conversation experiment"""
        print(f"\n{'='*60}")
        print(f"Starting Chatbot-Agent Conversation Experiment")
        print(f"Topic: {self.topic}")
        print(f"Max QA Count: {self.max_qa_count}")
        print(f"Agent: {self.agent.agent_id}")
        print(f"{'='*60}\n")
        
        # Generate initial question
        current_question = self.conversation_manager.generate_initial_question()
        
        conversation_complete = False
        round_num = 1
        
        while not conversation_complete:
            if self.verbose:
                print(f"\n--- Round {round_num} ---")
                print(f"Chatbot: {current_question['question']}")
            
            # Agent processes question and generates answer
            answer = self.agent.process_question(current_question)
            self.agent.add_to_history(current_question, answer)
            
            if self.verbose:
                print(f"Agent: {answer}")
            
            # Process answer and get follow-up questions
            response = self.conversation_manager.process_answer(current_question, answer)
            
            # Check if conversation should end
            follow_up_questions = response.get("followUpQuestions", [])
            qa_count = response.get("qaCount", 0)
            max_count = response.get("maxQaCount", self.max_qa_count)
            
            if not follow_up_questions or qa_count >= max_count:
                conversation_complete = True
                if self.verbose:
                    print(f"\n--- Conversation Complete ---")
                    print(f"Total QA pairs: {qa_count}")
            else:
                # Select next question (take the first follow-up)
                current_question = follow_up_questions[0]
                round_num += 1
                
        # Export results
        print(f"\n{'='*60}")
        print("Exporting conversation and causal graph...")
        conversation_file, graph_file = self.conversation_manager.export_conversation()
        
        # Print summary
        self._print_summary()
        
        return conversation_file, graph_file
        
    def _print_summary(self):
        """Print conversation summary"""
        cbn = self.conversation_manager.cbn
        
        print(f"\n{'='*60}")
        print("CONVERSATION SUMMARY")
        print(f"{'='*60}")
        
        print(f"\nTotal QA Pairs: {len(self.conversation_manager.qa_pairs)}")
        print(f"Total Nodes: {len(cbn.get('nodes', {}))}")
        print(f"Total Edges: {len(cbn.get('edges', {}))}")
        print(f"Anchor Nodes: {len(cbn.get('anchor_queue', []))}")
        
        # List nodes
        print("\nNodes in Causal Graph:")
        for node_id, node in cbn.get('nodes', {}).items():
            status = node.get('status', 'unknown')
            label = node.get('label', 'unknown')
            freq = node.get('frequency', 0)
            print(f"  - [{status}] {label} (frequency: {freq})")
            
        # List edges
        if cbn.get('edges'):
            print("\nEdges in Causal Graph:")
            for edge_id, edge in cbn.get('edges', {}).items():
                source_id = edge.get('source')
                target_id = edge.get('target')
                
                source_label = cbn['nodes'][source_id].get('label', 'unknown') if source_id in cbn['nodes'] else 'unknown'
                target_label = cbn['nodes'][target_id].get('label', 'unknown') if target_id in cbn['nodes'] else 'unknown'
                
                direction = edge.get('direction', 'unknown')
                strength = edge.get('strength', 0)
                
                arrow = "→" if direction == 'positive' else "⊣"
                print(f"  - {source_label} {arrow} {target_label} (strength: {strength:.2f})")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run chatbot-agent conversation experiment')
    parser.add_argument('--agent', choices=['simple', 'interactive'], default='simple',
                      help='Agent type to use')
    parser.add_argument('--topic', default='climate change',
                      help='Conversation topic')
    parser.add_argument('--max-qa', type=int, default=20,
                      help='Maximum number of QA pairs')
    parser.add_argument('--quiet', action='store_true',
                      help='Reduce output verbosity')
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("ERROR: DASHSCOPE_API_KEY environment variable not set")
        print("Please set it before running the experiment")
        sys.exit(1)
    
    # Create agent
    if args.agent == 'simple':
        agent = SimpleAgent()
    else:
        agent = InteractiveAgent()
    
    # Run experiment
    runner = ExperimentRunner(
        agent=agent,
        topic=args.topic,
        max_qa_count=args.max_qa,
        verbose=not args.quiet
    )
    
    try:
        conversation_file, graph_file = runner.run()
        print(f"\nExperiment completed successfully!")
        print(f"Results saved to:")
        print(f"  - {conversation_file}")
        print(f"  - {graph_file}")
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
