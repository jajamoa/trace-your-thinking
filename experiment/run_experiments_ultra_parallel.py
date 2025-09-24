#!/usr/bin/env python3
"""
Ultra-parallel experiment runner with threaded LLM requests and parallel survey processing
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
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed, TimeoutError
import multiprocessing
import random
import time
import signal
import threading

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
from llm_agent_threaded import create_synthetic_agent, ThreadSafeLLMAgent


def process_agent_survey_parallel(agent, topic, agent_data_path):
    """Process survey questions for an agent with parallel LLM requests"""
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
        
        # Process survey responses in parallel if using LLM
        opinions = {}
        reasons = {}
        
        if isinstance(agent, ThreadSafeLLMAgent) and agent.use_llm:
            # Use thread pool for parallel survey processing
            with ThreadPoolExecutor(max_workers=4, thread_name_prefix="Survey") as survey_executor:
                # Submit all survey questions
                future_to_question = {}
                
                for q in survey_questions:
                    if q["type"] in ["stance", "opinion", "scenario"]:
                        future = survey_executor.submit(agent.process_survey_question, q)
                        future_to_question[future] = q
                
                # Collect results
                for future in as_completed(future_to_question, timeout=60):
                    q = future_to_question[future]
                    q_id = q["id"]
                    
                    try:
                        result = future.result()
                        if "score" in result:
                            opinions[q_id] = result["score"]
                        elif "choice" in result:
                            opinions[q_id] = result["choice"]
                        elif "response" in result:
                            # If response is text, try to extract score using keyword analysis
                            if isinstance(result["response"], str):
                                scale = q.get("scale", [1, 10])
                                extracted_score = agent._extract_score_from_text(result["response"], scale)
                                opinions[q_id] = extracted_score
                            else:
                                opinions[q_id] = result["response"]
                    except Exception as e:
                        print(f"Survey question {q_id} failed: {e}")
                        # Fallback to template response
                        opinions[q_id] = 5  # Default neutral
        else:
            # Fallback to sequential template-based processing
            stance_value = _get_stance_value_from_agent(agent)
            
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
        
        # Generate reasons based on opinions (can be done in parallel too)
        _generate_reasons_for_opinions(opinions, survey_questions, reverse_mapping, reasons, agent)
        
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


def _get_stance_value_from_agent(agent):
    """Extract stance value from agent's CBN"""
    stance_value = 5  # default neutral
    
    if agent.current_cbn_prompt:
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
    
    return stance_value


def _generate_reasons_for_opinions(opinions, survey_questions, reverse_mapping, reasons, agent):
    """Generate reasons based on opinions"""
    stance_value = _get_stance_value_from_agent(agent)
    
    for q in survey_questions:
        q_id = q["id"]
        
        # Process follow-up reason questions
        if q.get("has_reason_followup") and "followup" in q and q_id in opinions:
            followup = q["followup"]
            # Use the main question ID (remove 'r' suffix) for reasons
            main_q_id = q_id
            reasons[main_q_id] = {}
            
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
                
                # Use the main question ID (remove 'r' suffix) for reasons
                main_q_id = q_id
                reasons[main_q_id][reason_code] = reason_score
        
        # Process standalone reason_evaluation questions
        elif q["type"] == "reason_evaluation":
            reasons[q_id] = {}
            
            for reason_code in q.get("reasons", []):
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
                
                reasons[q_id][reason_code] = reason_score


def process_single_agent_topic_ultra(args):
    """Process a single agent-topic combination with ultra parallelization"""
    agent_id, topic, agent_data_path, max_qa_count, verbose = args
    
    # Suppress INFO logs in worker processes
    logging.getLogger().setLevel(logging.ERROR)
    
    try:
        # Check if already processed
        cbn_capture_file = Path(agent_data_path) / "cbn_capture" / f"captured_cbn_{topic}.json"
        if cbn_capture_file.exists():
            return {
                "agent_id": agent_id,
                "topic": topic,
                "status": "skipped",
                "message": "Already processed",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create agent and conversation manager
        agent = create_synthetic_agent(agent_id, agent_data_path, use_llm=True)
        agent.set_topic(topic)
        
        conversation_manager = ConversationManager(
            topic=topic,
            max_qa_count=max_qa_count
        )
        
        # Get initial question
        current_question = conversation_manager.generate_initial_question()
        
        # Validate question format
        if not isinstance(current_question, dict):
            raise ValueError(f"Initial question is not a dict: {type(current_question)}")
        
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
        
        # Run conversation with threaded LLM requests
        conversation_complete = False
        round_num = 1
        
        # For LLM agents, we can potentially parallelize multiple question processing
        while not conversation_complete:
            # Validate question format before processing
            if not isinstance(current_question, dict):
                raise ValueError(f"Question is not a dict at round {round_num}: {type(current_question)}")
            
            # Agent processes question (this can use thread pool internally)
            answer = agent.process_question(current_question)
            agent.add_to_history(current_question, answer)
            
            # Add to transcript in reference format
            question_text = current_question.get("question", "")
            if not question_text:
                raise ValueError(f"Question dict missing 'question' field: {current_question}")
            
            transcript_data.append([
                str(round_num),
                question_text,
                answer
            ])
            
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
                next_question = follow_up_questions[0]
                
                # Validate next question format
                if not isinstance(next_question, dict):
                    # If it's a string, wrap it in a dict
                    if isinstance(next_question, str):
                        next_question = {
                            "id": f"followup_{round_num}",
                            "question": next_question,
                            "shortText": "Follow-up question",
                            "type": "followup"
                        }
                    else:
                        raise ValueError(f"Follow-up question is not a dict: {type(next_question)}")
                
                current_question = next_question
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
        
        # Process survey after interview with parallel processing
        survey_results = process_agent_survey_parallel(agent, topic, agent_data_path)
        
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
        import traceback
        return {
            "agent_id": agent_id,
            "topic": topic,
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }


class UltraParallelExperimentRunner:
    """Runs experiments with maximum parallelization"""
    
    def __init__(self, agent_data_dir="agent_data/synthetic_agents", 
                 topics=None, max_qa_count=20, verbose=True, max_workers=None,
                 specific_agents=None, llm_threads=8):
        """
        Initialize ultra-parallel experiment runner
        
        Args:
            agent_data_dir: Directory containing synthetic agent data
            topics: List of topics to run (default: all)
            max_qa_count: Maximum QA pairs per conversation
            verbose: Whether to print detailed output
            max_workers: Maximum number of parallel workers (default: CPU count)
            specific_agents: List of specific agent IDs to process (default: all)
            llm_threads: Number of threads for LLM requests (default: 8)
        """
        self.agent_data_dir = Path(agent_data_dir)
        self.topics = topics or ["zoning", "healthcare", "surveillance"]
        self.max_qa_count = max_qa_count
        self.verbose = verbose
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.specific_agents = specific_agents
        self.llm_threads = llm_threads
        
        # Initialize the shared LLM thread pool
        if os.getenv('DASHSCOPE_API_KEY'):
            ThreadSafeLLMAgent.get_llm_executor(max_workers=llm_threads)
            print(f"Initialized LLM thread pool with {llm_threads} threads")
        
    def run_all_experiments(self):
        """Run experiments for all agents and topics with ultra parallelization"""
        # Get all agent directories
        agent_dirs = []
        
        if self.specific_agents:
            # Process only specified agents
            for agent_id in self.specific_agents:
                agent_dir = self.agent_data_dir / agent_id
                if agent_dir.is_dir():
                    agent_dirs.append(agent_dir)
                else:
                    print(f"Warning: Agent directory not found: {agent_dir}")
        else:
            # Process all agents
            agent_dirs = [d for d in self.agent_data_dir.iterdir() 
                         if d.is_dir() and not d.name.endswith('.json') and d.name != 'experiment_summary']
        
        if not agent_dirs:
            print("No synthetic agents found!")
            return
        
        print(f"Found {len(agent_dirs)} synthetic agents")
        print(f"Topics to process: {', '.join(self.topics)}")
        print(f"Max QA pairs per conversation: {self.max_qa_count}")
        print(f"Using {self.max_workers} parallel processes")
        print(f"Using {self.llm_threads} LLM request threads")
        print("=" * 60)
        
        # Prepare all agent-topic combinations
        tasks = []
        for agent_dir in agent_dirs:
            agent_id = agent_dir.name
            for topic in self.topics:
                tasks.append((agent_id, topic, str(agent_dir), self.max_qa_count, False))
        
        print(f"\nProcessing {len(tasks)} agent-topic combinations with ultra parallelization...")
        print("-" * 60)
        
        # Progress tracking
        start_time = time.time()
        
        # Process in parallel with maximum concurrency
        results = []
        successful = 0
        failed = 0
        skipped = 0
        completed = 0
        total_tasks = len(tasks)
        
        # Setup signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal. Shutting down gracefully...")
            ThreadSafeLLMAgent.shutdown_llm_executor()
            raise KeyboardInterrupt()
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                print(f"Submitting {len(tasks)} tasks to {self.max_workers} processes...")
                future_to_task = {}
                for i, task in enumerate(tasks):
                    future = executor.submit(process_single_agent_topic_ultra, task)
                    future_to_task[future] = task
                
                print("All tasks submitted, processing results...")
                
                # Process completed tasks
                try:
                    for future in as_completed(future_to_task):
                        task = future_to_task[future]
                        agent_id, topic = task[0], task[1]
                        completed += 1
                        
                        # Calculate progress
                        elapsed_time = time.time() - start_time
                        progress_pct = (completed / total_tasks) * 100
                        
                        try:
                            # Use timeout for individual task result
                            result = future.result(timeout=180)  # 3 minute timeout per task
                            results.append(result)
                            
                            if result["status"] == "success":
                                successful += 1
                                print(f"SUCCESS: {agent_id} - {topic} (QA: {result['qa_count']}) [{completed}/{total_tasks} {progress_pct:.1f}%]")
                            elif result["status"] == "skipped":
                                skipped += 1
                                print(f"SKIP: {agent_id} - {topic} (already processed) [{completed}/{total_tasks} {progress_pct:.1f}%]")
                            else:
                                failed += 1
                                error_msg = result.get('error', 'Unknown error')
                                print(f"ERROR: {agent_id} - {topic}: {error_msg} [{completed}/{total_tasks} {progress_pct:.1f}%]")
                                
                        except TimeoutError:
                            failed += 1
                            print(f"TIMEOUT: {agent_id} - {topic} (exceeded 3 minutes) [{completed}/{total_tasks} {progress_pct:.1f}%]")
                            results.append({
                                "agent_id": agent_id,
                                "topic": topic,
                                "status": "error",
                                "error": "Task timeout",
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            failed += 1
                            print(f"ERROR: {agent_id} - {topic}: {str(e)} [{completed}/{total_tasks} {progress_pct:.1f}%]")
                            results.append({
                                "agent_id": agent_id,
                                "topic": topic,
                                "status": "error",
                                "error": str(e),
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        # Show progress every 3 completions
                        if completed % 3 == 0 and completed < total_tasks:
                            avg_time_per_task = elapsed_time / completed
                            estimated_remaining = (total_tasks - completed) * avg_time_per_task
                            throughput = completed / elapsed_time
                            print(f"Progress: {completed}/{total_tasks} ({progress_pct:.1f}%) - Est. remaining: {estimated_remaining/60:.1f}min - Throughput: {throughput:.2f} tasks/sec")
                
                except KeyboardInterrupt:
                    print("\nShutting down executor...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
        
        except KeyboardInterrupt:
            print("\nExperiment interrupted by user")
            return results
        finally:
            # Always shutdown LLM thread pool
            ThreadSafeLLMAgent.shutdown_llm_executor()
        
        # Save summary
        self._save_summary(results)
        
        # Final summary
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"Completed: {successful} successful, {failed} failed, {skipped} skipped")
        print(f"Total time: {total_time/60:.1f} minutes ({total_time:.1f} seconds)")
        if successful > 0:
            print(f"Average time per successful task: {total_time/successful:.1f} seconds")
        print(f"Overall throughput: {total_tasks/total_time:.2f} tasks/second")
        
        return results
        
    def _save_summary(self, results):
        """Save experiment summary"""
        summary_file = self.agent_data_dir / "experiment_summary.json"
        
        # Calculate statistics
        stats = {
            "total_experiments": len(results),
            "successful": len([r for r in results if r.get("status") == "success"]),
            "failed": len([r for r in results if r.get("status") == "error"]),
            "skipped": len([r for r in results if r.get("status") == "skipped"]),
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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run synthetic agent experiments (ultra-parallel)')
    parser.add_argument('--topics', nargs='+', 
                      choices=['zoning', 'healthcare', 'surveillance'],
                      help='Topics to run (default: all)')
    parser.add_argument('--max-qa', type=int, default=20,
                      help='Maximum QA pairs per conversation')
    parser.add_argument('--agent-dir', default='agent_data/synthetic_agents',
                      help='Directory containing synthetic agent data')
    parser.add_argument('--workers', type=int,
                      help='Number of parallel processes (default: CPU count)')
    parser.add_argument('--llm-threads', type=int, default=8,
                      help='Number of LLM request threads (default: 8)')
    parser.add_argument('--agents', nargs='+',
                      help='Specific agent IDs to process (default: all)')
    parser.add_argument('--quiet', action='store_true',
                      help='Reduce output verbosity')
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("WARNING: DASHSCOPE_API_KEY environment variable not set. Using template responses.")
    
    # Configure logging based on verbosity
    if args.quiet:
        logging.basicConfig(level=logging.ERROR)
    
    # Create runner and run experiments
    runner = UltraParallelExperimentRunner(
        agent_data_dir=args.agent_dir,
        topics=args.topics,
        max_qa_count=args.max_qa,
        verbose=not args.quiet,
        max_workers=args.workers,
        specific_agents=args.agents,
        llm_threads=args.llm_threads
    )
    
    results = runner.run_all_experiments()
    
    print(f"\n\nAll experiments completed with ultra parallelization!")
    print(f"Processed {len(results)} agent-topic combinations")


if __name__ == "__main__":
    main()
