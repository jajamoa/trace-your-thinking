"""
Run experiments with synthetic agents
Orchestrates conversations between chatbot and synthetic agents for all topics
"""
import sys
import os
import json
import csv
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import random

# Configure logging to only show errors by default
logging.basicConfig(level=logging.ERROR)

# Load environment variables
parent_dir = Path(__file__).parent.parent
env_path = parent_dir / '.env'
env_local_path = parent_dir / '.env.local'

if env_local_path.exists():
    load_dotenv(dotenv_path=env_local_path)
elif env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Add parent directory to path
sys.path.append(str(parent_dir))

from conversation_manager import ConversationManager
from synthetic_agent import SyntheticAgent


def process_single_agent_topic(args):
    """Process a single agent-topic combination in a separate process"""
    agent_id, topic, agent_data_path, max_qa_count, verbose = args
    
    # Suppress INFO logs in worker processes
    logging.getLogger().setLevel(logging.ERROR)
    
    try:
        # Create agent and conversation manager
        agent = SyntheticAgent(agent_id, agent_data_path)
        agent.set_topic(topic)
        
        conversation_manager = ConversationManager(
            topic=topic,
            max_qa_count=max_qa_count
        )
        
        # Get initial question
        current_question = conversation_manager.generate_initial_question()
        
        # Store transcript data in reference format
        transcript_data = [
            ["Session ID", f"session_{int(datetime.now().timestamp() * 1000)}_{agent_id[:8]}"],
            ["Prolific ID", agent_id],
            ["Status", "completed"],
            ["Progress", f"{max_qa_count}/{max_qa_count}"],
            ["Created At", datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")],
            ["Updated At", ""],
            ["Completed At", ""],
            [""],
            ["Question Number", "Question", "Answer"]
        ]
        
        conversation_complete = False
        round_num = 1
        
        while not conversation_complete:
            # Agent processes question
            answer = agent.process_question(current_question)
            agent.add_to_history(current_question, answer)
            
            # Add to transcript in reference format
            transcript_data.append([
                str(round_num),
                current_question["question"],
                answer
            ])
            
            if verbose:
                print(f"    Q{round_num}: {current_question['question']}")
                print(f"    A{round_num}: {answer}")
                print()
            
            # Process answer and get follow-up
            response = conversation_manager.process_answer(current_question, answer)
            
            # Check if conversation should end
            follow_up_questions = response.get("followUpQuestions", [])
            qa_count = response.get("qaCount", 0)
            max_count = response.get("maxQaCount", max_qa_count)
            
            if qa_count >= max_count or not follow_up_questions:
                conversation_complete = True
            else:
                # Select next question
                current_question = follow_up_questions[0]
                round_num += 1
        
        # Update completed time
        completed_time = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
        transcript_data[5] = ["Updated At", completed_time]
        transcript_data[6] = ["Completed At", completed_time]
        
        # Get final CBN
        final_cbn = conversation_manager.get_cbn()
        
        # Save transcript in reference format
        transcript_dir = Path(agent_data_path) / "transcript" / "raw"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        # Map surveillance back to camera for file naming
        file_topic = "camera" if topic == "surveillance" else topic
        
        transcript_file = transcript_dir / f"{file_topic}.csv"
        with open(transcript_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row in transcript_data:
                writer.writerow(row)
        
        # Save captured CBN
        cbn_dir = Path(agent_data_path) / "cbn_capture"
        cbn_dir.mkdir(parents=True, exist_ok=True)
        
        cbn_file = cbn_dir / f"captured_cbn_{file_topic}.json"
        with open(cbn_file, 'w', encoding='utf-8') as f:
            json.dump(final_cbn, f, indent=2, ensure_ascii=False)
        
        # Process survey after interview
        survey_results = process_agent_survey(agent, topic, agent_data_path)
        
        return {
            "agent_id": agent_id,
            "topic": topic,
            "qa_count": round_num,
            "transcript_file": str(transcript_file),
            "cbn_file": str(cbn_file),
            "survey_file": survey_results.get("file") if survey_results else None,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "agent_id": agent_id,
            "topic": topic,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def process_agent_survey(agent, topic, agent_data_path):
    """Process survey questions for an agent after interview"""
    try:
        # Load survey questions and reason mappings
        survey_file = Path(__file__).parent / "agent_data" / "ref_data" / "survey_content" / "surveys.json"
        with open(survey_file, 'r', encoding='utf-8') as f:
            surveys = json.load(f)
        
        # Load reason mappings
        reason_mapping_files = {
            "zoning": "housing_reason_mapping.json",
            "healthcare": "healthcare_reason_mapping.json", 
            "surveillance": "surveillance_reason_mapping.json"
        }
        
        mapping_file = Path(__file__).parent / "agent_data" / "ref_data" / "survey_content" / reason_mapping_files.get(topic)
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                reason_mapping = json.load(f)
                reverse_mapping = reason_mapping.get("reverse_mapping", {})
        else:
            reverse_mapping = {}
        
        # Map topic to survey topic
        topic_map = {
            "zoning": "upzoning",
            "healthcare": "universal_healthcare",
            "surveillance": "surveillance_camera"
        }
        survey_topic = topic_map.get(topic, topic)
        
        if survey_topic not in surveys["topics"]:
            return None
        
        survey_questions = surveys["topics"][survey_topic]["questions"]
        
        # Process survey responses
        opinions = {}
        reasons = {}
        
        # Get agent's CBN beliefs for generating responses
        stance_value = 5  # default neutral
        
        if agent.current_cbn_prompt:
            # Handle new prompt CBN format where nodes is a dict
            nodes_dict = agent.current_cbn_prompt.get("nodes", {})
            stance_node_id = agent.current_cbn_prompt.get("stance_node")
            
            if stance_node_id and stance_node_id in nodes_dict:
                stance_node = nodes_dict[stance_node_id]
                label = stance_node.get("label", "").lower()
                
                # Determine stance from label
                if any(word in label for word in ["strongly support", "strong support", "firmly support"]):
                    stance_value = 9
                elif any(word in label for word in ["support", "favor", "pro", "advocate"]):
                    stance_value = 7
                elif any(word in label for word in ["strongly oppose", "strong opposition", "firmly against"]):
                    stance_value = 2
                elif any(word in label for word in ["oppose", "against", "anti", "resist", "opposition"]):
                    stance_value = 3
                else:
                    stance_value = 5  # neutral
        
        # Process each survey question
        for q in survey_questions:
            q_id = q["id"]
            
            if q["type"] in ["stance", "opinion", "scenario"]:
                # Generate opinion score based on agent's beliefs
                if q["type"] == "stance":
                    score = stance_value
                elif q["type"] == "scenario":
                    # Scenarios shift from base stance
                    if "rent" in q["text"].lower() or "affordable" in q["text"].lower():
                        score = min(10, stance_value + random.randint(0, 2))
                    elif "design" in q["text"].lower() or "shadow" in q["text"].lower():
                        score = max(1, stance_value - random.randint(0, 2))
                    else:
                        score = stance_value + random.randint(-1, 1)
                else:
                    # Opinion questions vary around stance
                    score = max(1, min(10, stance_value + random.randint(-2, 2)))
                
                opinions[q_id] = score
                
                # Process follow-up reason questions
                if q.get("has_reason_followup") and "followup" in q:
                    followup = q["followup"]
                    reasons[followup["id"]] = {}
                    
                    for reason_code in followup.get("reasons", []):
                        # Get actual reason text
                        reason_text = reverse_mapping.get(reason_code, "")
                        
                        # Generate score based on reason content and agent stance
                        if stance_value > 5:  # Supportive agent
                            if any(word in reason_text.lower() for word in 
                                 ["benefit", "help", "affordable", "equity", "access", "opportunity"]):
                                reason_score = random.randint(4, 5)
                            elif any(word in reason_text.lower() for word in 
                                   ["concern", "worry", "traffic", "property value", "crowding"]):
                                reason_score = random.randint(1, 2)
                            else:
                                reason_score = 3
                        else:  # Opposing agent
                            if any(word in reason_text.lower() for word in 
                                 ["concern", "worry", "traffic", "property value", "crowding", "inefficient"]):
                                reason_score = random.randint(4, 5)
                            elif any(word in reason_text.lower() for word in 
                                   ["benefit", "help", "affordable", "equity", "access"]):
                                reason_score = random.randint(1, 2)
                            else:
                                reason_score = 3
                        
                        reasons[followup["id"]][reason_code] = reason_score
            
            elif q["type"] == "reason_evaluation":
                # Direct reason evaluation questions
                if q_id not in reasons:
                    reasons[q_id] = {}
                
                for reason_code in q.get("reasons", []):
                    reason_text = reverse_mapping.get(reason_code, "")
                    
                    # Similar logic as above for scoring
                    if stance_value > 5:
                        if any(word in reason_text.lower() for word in 
                             ["benefit", "help", "affordable", "equity", "access", "opportunity"]):
                            reason_score = random.randint(4, 5)
                        elif any(word in reason_text.lower() for word in 
                               ["concern", "worry", "traffic", "property value", "crowding"]):
                            reason_score = random.randint(1, 2)
                        else:
                            reason_score = 3
                    else:
                        if any(word in reason_text.lower() for word in 
                             ["concern", "worry", "traffic", "property value", "crowding", "inefficient"]):
                            reason_score = random.randint(4, 5)
                        elif any(word in reason_text.lower() for word in 
                               ["benefit", "help", "affordable", "equity", "access"]):
                            reason_score = random.randint(1, 2)
                        else:
                            reason_score = 3
                    
                    reasons[q_id][reason_code] = reason_score
        
        # Save survey results
        survey_dir = Path(agent_data_path) / "survey"
        survey_dir.mkdir(parents=True, exist_ok=True)
        
        # Map topic for file naming
        file_topic = "camera" if topic == "surveillance" else topic
        
        survey_result = {
            agent.agent_id: {
                "opinions": opinions,
                "reasons": reasons
            }
        }
        
        survey_file = survey_dir / f"{file_topic}_reaction.json"
        with open(survey_file, 'w', encoding='utf-8') as f:
            json.dump(survey_result, f, indent=2, ensure_ascii=False)
        
        return {"file": str(survey_file), "responses": len(opinions)}
        
    except Exception as e:
        print(f"Error processing survey for {agent.agent_id}: {e}")
        return None


class SyntheticExperimentRunner:
    """Runs experiments with synthetic agents"""
    
    def __init__(self, agent_data_dir="agent_data/synthetic_agents", 
                 topics=None, max_qa_count=20, verbose=True, max_workers=None):
        """
        Initialize experiment runner
        
        Args:
            agent_data_dir: Directory containing synthetic agent data
            topics: List of topics to run (default: all)
            max_qa_count: Maximum QA pairs per conversation
            verbose: Whether to print detailed output
            max_workers: Maximum number of parallel workers (default: CPU count)
        """
        self.agent_data_dir = Path(agent_data_dir)
        self.topics = topics or ["zoning", "healthcare", "surveillance"]
        self.max_qa_count = max_qa_count
        self.verbose = verbose
        self.max_workers = max_workers or multiprocessing.cpu_count()
        
    def run_all_experiments(self):
        """Run experiments for all agents and topics"""
        # Get all agent directories
        agent_dirs = [d for d in self.agent_data_dir.iterdir() 
                     if d.is_dir() and not d.name.endswith('.json')]
        
        if not agent_dirs:
            print("No synthetic agents found!")
            return
        
        print(f"Found {len(agent_dirs)} synthetic agents")
        print(f"Topics to process: {', '.join(self.topics)}")
        print(f"Max QA pairs per conversation: {self.max_qa_count}")
        print(f"Using {self.max_workers} parallel workers")
        print("=" * 60)
        
        # Prepare all agent-topic combinations
        tasks = []
        for agent_dir in agent_dirs:
            agent_id = agent_dir.name
            for topic in self.topics:
                tasks.append((agent_id, topic, str(agent_dir), self.max_qa_count, False))
        
        print(f"\nProcessing {len(tasks)} agent-topic combinations in parallel...")
        print("-" * 60)
        
        # Process in parallel
        results = []
        successful = 0
        failed = 0
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(process_single_agent_topic, task): task 
                            for task in tasks}
            
            # Process completed tasks
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                agent_id, topic = task[0], task[1]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result["status"] == "success":
                        successful += 1
                        if self.verbose:
                            print(f"✓ {agent_id} - {topic} (QA: {result['qa_count']})")
                    else:
                        failed += 1
                        print(f"✗ {agent_id} - {topic}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    failed += 1
                    print(f"✗ {agent_id} - {topic}: {str(e)}")
                    results.append({
                        "agent_id": agent_id,
                        "topic": topic,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Save summary
        self._save_summary(results)
        
        print("\n" + "=" * 60)
        print(f"Completed: {successful} successful, {failed} failed")
        print(f"Total time: {datetime.now()}")
        
        return results
        
    def _save_summary(self, results):
        """Save experiment summary"""
        summary_file = self.agent_data_dir / "experiment_summary.json"
        
        # Calculate statistics
        stats = {
            "total_experiments": len(results),
            "successful": len([r for r in results if r.get("status") == "success"]),
            "failed": len([r for r in results if r.get("status") == "error"]),
            "by_topic": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Group by topic
        for topic in self.topics:
            topic_results = [r for r in results if r.get("topic") == topic and r.get("status") == "success"]
            if topic_results:
                stats["by_topic"][topic] = {
                    "count": len(topic_results),
                    "avg_qa_count": sum(r.get("qa_count", 0) for r in topic_results) / len(topic_results)
                }
        
        summary = {
            "statistics": stats,
            "results": results
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
            
        if self.verbose:
            print(f"\nSaved experiment summary to: {summary_file}")
            print("\nSummary Statistics:")
            print(f"  Total experiments: {stats['total_experiments']}")
            for topic, info in stats["by_topic"].items():
                print(f"  {topic}: {info['count']} conversations, avg {info['avg_qa_count']:.1f} QA pairs")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run synthetic agent experiments')
    parser.add_argument('--topics', nargs='+', 
                      choices=['zoning', 'healthcare', 'surveillance'],
                      help='Topics to run (default: all)')
    parser.add_argument('--max-qa', type=int, default=20,
                      help='Maximum QA pairs per conversation')
    parser.add_argument('--agent-dir', default='agent_data/synthetic_agents',
                      help='Directory containing synthetic agent data')
    parser.add_argument('--workers', type=int,
                      help='Number of parallel workers (default: CPU count)')
    parser.add_argument('--quiet', action='store_true',
                      help='Reduce output verbosity')
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("ERROR: DASHSCOPE_API_KEY environment variable not set")
        sys.exit(1)
    
    # Configure logging based on verbosity
    if args.quiet:
        logging.basicConfig(level=logging.ERROR)
    
    # Create runner and run experiments
    runner = SyntheticExperimentRunner(
        agent_data_dir=args.agent_dir,
        topics=args.topics,
        max_qa_count=args.max_qa,
        verbose=not args.quiet,
        max_workers=args.workers
    )
    
    results = runner.run_all_experiments()
    
    print(f"\n\nAll experiments completed successfully!")
    print(f"Processed {len(results)} agent-topic combinations")


if __name__ == "__main__":
    main()