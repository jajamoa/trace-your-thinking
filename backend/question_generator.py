"""
Question Generator Module
Responsible for generating follow-up questions based on the current state of the SCM.
"""
import uuid
import time
import random
import logging
from llm_logger import llm_logger

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    Generate follow-up questions based on the current state of the SCM.
    """
    
    def __init__(self):
        """Initialize the question generator"""
        # Templates for different question types
        self.step1_templates = [
            "Could you tell me more about {node}?",
            "What factors do you think influence {node}?",
            "How would you describe {node} in your own words?",
            "Is {node} a significant factor in your thinking about this issue?",
            "What comes to mind when you think about {node}?"
        ]
        
        # Combined templates for Step 2 that cover both relationship discovery and strength
        self.step2_combined_templates = {
            # Upstream templates (what affects this node)
            "upstream": [
                "What factors do you think influence {node}, and how strong is their impact?",
                "What causes changes in {node}? Are these influences strong or weak?",
                "What might lead to increases or decreases in {node}, and how significant are these effects?",
                "What do you think are the main causes of {node}, and how certain are you about these relationships?",
                "What factors affect {node}, and which ones have the strongest influence?"
            ],
            # Downstream templates (what does this node affect)
            "downstream": [
                "How does {node} affect other aspects of this issue, and how strong are these effects?",
                "What consequences might result from changes in {node}? Which effects are most significant?",
                "What happens when {node} increases or decreases? How direct are these relationships?",
                "How does {node} influence your overall stance, and how important is this connection?",
                "What effects does {node} have on other factors, and how would you rate the strength of these relationships?"
            ],
            # Relationship strength/modifier templates (for existing edges)
            "relationship": [
                "How would you describe the relationship between {from_node} and {to_node}? Is it a strong or weak connection?",
                "Does {from_node} have a positive or negative effect on {to_node}, and how significant is this effect?",
                "How confident are you that changes in {from_node} lead to changes in {to_node}?",
                "Is the effect of {from_node} on {to_node} immediate, or does it take time to develop?",
                "Would small changes in {from_node} lead to noticeable changes in {to_node}, or would it take larger shifts?"
            ]
        }
        
        self.clarification_templates = [
            "When you mention {node}, do you mean {specific_concept} or something else?",
            "Could you clarify what you mean by {node}?",
            "Is {node} different from {related_node}, or are they related concepts?",
            "Could you provide an example of what you mean by {node}?",
            "How would you define {node} in this context?"
        ]
        
        # Motif-based templates for graph completion
        self.motif_templates = {
            "triad": "You've mentioned that {node1} affects {node2}, and {node2} affects {node3}. Do you think there's a direct relationship between {node1} and {node3} as well?",
            "mediator": "You've said that {node1} affects {node3}. Do you think there might be some intermediate factors between them?",
            "chain": "You've mentioned that {node1} influences {node2}. What do you think {node2} might affect in turn?",
            "common_cause": "Both {node1} and {node2} seem important in your thinking. Do you think they might have a common cause?"
        }
    
    def generate_follow_up_questions(self, agent_scm, current_step, anchor_queue, existing_question_texts=None, current_qa_count=0, max_qa_count=None, current_index=0, total_qa_count=0):
        """
        Generate follow-up questions based on the current SCM state and step.
        
        Args:
            agent_scm (dict): The current SCM
            current_step (int): The current interview step (1 or 2)
            anchor_queue (list): List of anchor node IDs
            existing_question_texts (list, optional): List of existing question texts to avoid duplicates
            current_qa_count (int, optional): Current number of QA pairs
            max_qa_count (int, optional): Maximum number of QA pairs allowed
            current_index (int, optional): Current question index in the interview
            total_qa_count (int, optional): Total number of questions in the interview
            
        Returns:
            list: List of follow-up question objects
        """
        if existing_question_texts is None:
            existing_question_texts = []
        
        llm_logger.log_separator("QUESTION GENERATION START")
        logger.info(f"Generating follow-up questions for step {current_step}")
        
        # Check if we've reached the maximum QA count
        if max_qa_count and current_qa_count >= max_qa_count:
            logger.info(f"Maximum QA count reached ({current_qa_count}/{max_qa_count}). No follow-up questions will be generated.")
            llm_logger.log_separator("QUESTION GENERATION CANCELLED - MAX QA COUNT REACHED")
            return []
        
        # Generate prioritized candidate questions
        candidate_questions = self.generate_prioritized_candidates(
            agent_scm, 
            current_step, 
            anchor_queue,
            current_index,
            total_qa_count
        )
        
        # Log the candidate questions
        self._log_candidate_questions(candidate_questions)
        
        # Prepare candidate info - ensure each candidate has required fields
        candidate_info = []
        for i, q in enumerate(candidate_questions):
            # Ensure each question has shortText field
            if "shortText" not in q:
                if "type" in q and "node_id" in q and q["type"] == "node_discovery" and q["node_id"] in agent_scm.get("nodes", {}):
                    # For node discovery questions
                    node_label = agent_scm["nodes"][q["node_id"]].get("label", "factor")
                    q["shortText"] = f"About {node_label}"
                elif "type" in q and "edge_id" in q and q["type"] == "relationship_qualification":
                    # For relationship questions
                    q["shortText"] = "Relationship qualification"
                elif "type" in q:
                    # For other typed questions
                    q["shortText"] = f"{q['type']} question"
                else:
                    # Default shortText is first 50 chars of question
                    q["shortText"] = q["question"][:50] + "..." if len(q["question"]) > 50 else q["question"]
            
            # Generate temporary ID if needed
            q_id = q.get("id", f"temp_{i}_{int(time.time())}")
            
            candidate_info.append({
                "id": q_id,
                "shortText": q["shortText"],
                "index": i  # Keep track of original index
            })
        
        # Extract existing question metadata from existing_question_texts
        # Assume existing_question_texts is a list of objects with id and shortText
        existing_info = []
        for i, q in enumerate(existing_question_texts):
            if isinstance(q, dict) and "id" in q and "shortText" in q:
                existing_info.append({
                    "id": q["id"],
                    "shortText": q["shortText"]
                })
            elif isinstance(q, str):
                # If it's just a string, create a simple entry
                existing_info.append({
                    "id": f"existing_{i}",
                    "shortText": q[:50] + "..." if len(q) > 50 else q
                })
        
        # Use logic to filter and select the best questions
        selected_indices = self.filter_questions_with_llm(candidate_info, existing_info)
        
        # Get the full question objects for the selected indices
        follow_up_questions = []
        for idx in selected_indices:
            if 0 <= idx < len(candidate_questions):
                follow_up_questions.append(candidate_questions[idx])
        
        # Limit number of questions based on step
        max_questions = 1 if current_step == 1 else 2
        if len(follow_up_questions) > max_questions:
            logger.info(f"Limiting questions from {len(follow_up_questions)} to {max_questions} for step {current_step}")
            follow_up_questions = follow_up_questions[:max_questions]
        
        # Ensure each question has required fields
        for q in follow_up_questions:
            q["id"] = q.get("id") or f"followup_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            q["shortText"] = q.get("shortText") or q["question"][:50] + "..."
            q["answer"] = q.get("answer") or ""
        
        logger.info(f"Generated {len(follow_up_questions)} follow-up questions")
        llm_logger.log_separator("QUESTION GENERATION COMPLETE")
        return follow_up_questions
    
    def generate_prioritized_candidates(self, agent_scm, current_step, anchor_queue, current_index=0, total_qa_count=0):
        """
        Generate a prioritized list of candidate questions based on the current SCM state.
        
        Args:
            agent_scm (dict): The current SCM
            current_step (int): The current interview step (1 or 2)
            anchor_queue (list): List of anchor node IDs
            current_index (int, optional): Current question index in the interview
            total_qa_count (int, optional): Total number of questions in the interview
            
        Returns:
            list: List of candidate question objects sorted by priority
        """
        llm_logger.log_separator("GENERATING PRIORITIZED CANDIDATES")
        logger.info(f"Generating prioritized candidates for step {current_step}")
        
        # Calculate remaining questions in the interview
        remaining_qa = total_qa_count - current_index
        logger.info(f"Current question index: {current_index}/{total_qa_count}, Remaining QAs: {remaining_qa}")
        
        candidates = []
        
        # Add questions based on the current step
        if current_step == 1:
            # Step 1: Node Discovery (pass empty list to get all possible questions)
            node_discovery_questions = self._generate_step1_questions(agent_scm, [])
            
            # Enhance shortText for node discovery questions
            for q in node_discovery_questions:
                if "node_id" in q and q["node_id"] in agent_scm.get("nodes", {}):
                    node_label = agent_scm["nodes"][q["node_id"]].get("label", "factor")
                    q["shortText"] = f"About {node_label}"
                else:
                    q["shortText"] = "Node discovery"
                q["priority"] = 2
                
            candidates.extend(node_discovery_questions)
        
        elif current_step == 2:
            # Step 2: Relationships
            
            # Get stance relationship questions (highest priority)
            stance_questions = []
            stance_node_id = agent_scm.get("stance_node_id")
            if stance_node_id and stance_node_id in agent_scm.get("nodes", {}):
                # Find anchor nodes with out-degree 0 that need connection to stance node
                for node_id in anchor_queue:
                    if node_id != stance_node_id and node_id in agent_scm.get("nodes", {}):
                        node = agent_scm["nodes"][node_id]
                        if len(node.get("outgoing_edges", [])) == 0:
                            # Check if no edge to stance node
                            connected_to_stance = False
                            for edge in agent_scm.get("edges", {}).values():
                                if edge.get("source") == node_id and edge.get("target") == stance_node_id:
                                    connected_to_stance = True
                                    break
                            
                            if not connected_to_stance:
                                # Create question
                                node_label = node.get("label", "factor")
                                stance_label = agent_scm["nodes"][stance_node_id].get("label", "stance")
                                
                                template = random.choice(self.step2_combined_templates["relationship"])
                                question_text = template.format(
                                    from_node=node_label,
                                    to_node=stance_label
                                )
                                
                                # Add guidance
                                modifier_guidance = " Does it have a positive effect (increasing it) or a negative effect (decreasing it)? How strong is this effect?"
                                if not question_text.endswith("?"):
                                    modifier_guidance = "?" + modifier_guidance
                                
                                stance_questions.append({
                                    "question": question_text + modifier_guidance,
                                    "shortText": f"Relationship: {node_label} → {stance_label}",
                                    "type": "stance_relationship",
                                    "node_id": node_id,
                                    "stance_node_id": stance_node_id,
                                    "priority": 1  # Highest priority
                                })
            
            candidates.extend(stance_questions)
            
            # Add other relationship questions
            relationship_questions = self._generate_step2_combined_questions(agent_scm, anchor_queue, [])
            
            # Enhance shortText for relationship questions
            for q in relationship_questions:
                q_type = q.get("type", "")
                
                # Set priority based on question type
                if q_type == "stance_relationship":
                    q["priority"] = 1  # Highest priority
                    
                    # Ensure shortText is set correctly
                    if "node_id" in q and "stance_node_id" in q:
                        from_node = agent_scm["nodes"].get(q["node_id"], {}).get("label", "factor")
                        to_node = agent_scm["nodes"].get(q["stance_node_id"], {}).get("label", "stance")
                        q["shortText"] = f"Relationship: {from_node} → {to_node}"
                        
                elif q_type == "anchor_upstream_with_strength":
                    q["priority"] = 2  # Medium priority
                    
                    # Set shortText for upstream questions
                    if "node_id" in q and q["node_id"] in agent_scm.get("nodes", {}):
                        node_label = agent_scm["nodes"][q["node_id"]].get("label", "factor")
                        q["shortText"] = f"Factors affecting {node_label}"
                        
                elif q_type == "relationship_qualification":
                    q["priority"] = 3  # Lower priority
                    
                    # Set shortText for relationship qualification
                    if "edge_id" in q and q["edge_id"] in agent_scm.get("edges", {}):
                        edge = agent_scm["edges"][q["edge_id"]]
                        from_id = edge.get("source")
                        to_id = edge.get("target")
                        
                        if from_id in agent_scm.get("nodes", {}) and to_id in agent_scm.get("nodes", {}):
                            from_label = agent_scm["nodes"][from_id].get("label", "source")
                            to_label = agent_scm["nodes"][to_id].get("label", "target")
                            q["shortText"] = f"Relationship: {from_label} → {to_label}"
                        else:
                            q["shortText"] = "Relationship qualification"
                else:
                    q["priority"] = 3  # Default lower priority
                    q["shortText"] = q.get("shortText", q_type + " question")
            
            candidates.extend(relationship_questions)
        
        # Add motif questions (medium priority)
        motif_questions = self._generate_motif_questions(agent_scm, [])
        
        # Enhance shortText for motif questions
        for q in motif_questions:
            q["priority"] = 3
            q_type = q.get("type", "")
            
            # Set detailed shortText for motif questions
            if q_type == "motif_triad" and "nodes" in q and len(q["nodes"]) >= 3:
                node1_id, node2_id, node3_id = q["nodes"][:3]
                if all(node_id in agent_scm.get("nodes", {}) for node_id in [node1_id, node2_id, node3_id]):
                    node1 = agent_scm["nodes"][node1_id].get("label", "node1")
                    node2 = agent_scm["nodes"][node2_id].get("label", "node2")
                    node3 = agent_scm["nodes"][node3_id].get("label", "node3")
                    q["shortText"] = f"Complete triad: {node1} → {node2} → {node3}"
                else:
                    q["shortText"] = "Complete relationship pattern"
            elif q_type == "motif_mediator" and "nodes" in q and len(q["nodes"]) >= 2:
                node1_id, node3_id = q["nodes"][:2]
                if node1_id in agent_scm.get("nodes", {}) and node3_id in agent_scm.get("nodes", {}):
                    node1 = agent_scm["nodes"][node1_id].get("label", "node1")
                    node3 = agent_scm["nodes"][node3_id].get("label", "node3")
                    q["shortText"] = f"Mediator between: {node1} and {node3}"
                else:
                    q["shortText"] = "Intermediate factors"
            else:
                q["shortText"] = q.get("shortText", "Graph pattern question")
                
        candidates.extend(motif_questions)
        
        # Only add general questions if there are 3 or fewer remaining QAs
        # and we still don't have enough candidates
        if remaining_qa <= 3 and len(candidates) < 2:
            logger.info(f"Only {remaining_qa} QAs remaining, considering adding general questions")
            
            # Add at most 1 general question as fallback (lowest priority)
            general_questions = self._generate_general_questions([])
            if general_questions:
                # Select the best general question
                best_general = general_questions[0] if general_questions else None
                
                if best_general:
                    # Format as dictionary if it's a string
                    if isinstance(best_general, str):
                        general_question = {
                            "question": best_general,
                            "shortText": f"General: {best_general[:30]}..." if len(best_general) > 30 else f"General: {best_general}",
                            "type": "general",
                            "priority": 4  # Lowest priority
                        }
                    else:
                        general_question = best_general
                        general_question["priority"] = 4
                        if "shortText" not in general_question:
                            general_question["shortText"] = f"General: {general_question.get('question', '')[:30]}..." if len(general_question.get('question', '')) > 30 else f"General: {general_question.get('question', '')}"
                    
                    logger.info(f"Adding 1 general question as fallback: {general_question.get('shortText')}")
                    candidates.append(general_question)
                    
            else:
                logger.info("No general questions could be generated")
        else:
            logger.info(f"{remaining_qa} QAs remaining, skipping general questions")
        
        # Sort candidates by priority (lower number = higher priority)
        candidates.sort(key=lambda x: x.get("priority", 10))
        
        logger.info(f"Generated {len(candidates)} candidates with priorities:")
        for priority in range(1, 5):
            count = sum(1 for q in candidates if q.get("priority") == priority)
            logger.info(f"  Priority {priority}: {count} questions")
        
        llm_logger.log_separator("PRIORITIZED CANDIDATES GENERATION COMPLETE")
        return candidates
    
    def filter_questions_with_llm(self, candidate_info, existing_info):
        """
        Select the best questions from candidates that don't duplicate existing questions.
        Uses pure logic instead of LLM to compare questions based on their shortText.
        
        Args:
            candidate_info (list): List of candidate question info (id, shortText, index)
            existing_info (list): List of existing question info (id, shortText)
            
        Returns:
            list: Indices of selected questions
        """
        llm_logger.log_separator("FILTERING QUESTIONS WITH PURE LOGIC")
        logger.info(f"Filtering {len(candidate_info)} candidates against {len(existing_info)} existing questions")
        
        # Log the shortText values being compared
        logger.info("Existing question purposes:")
        for i, existing in enumerate(existing_info):
            logger.info(f"  {i+1}. {existing.get('shortText', 'Unknown')}")
            
        logger.info("Candidate question purposes:")
        for i, candidate in enumerate(candidate_info):
            logger.info(f"  {i+1}. {candidate.get('shortText', 'Unknown')} (original index: {candidate.get('index', i)})")
        
        # If no candidates, return empty list
        if not candidate_info:
            return []
            
        # If no existing questions, just return top candidates (up to 2)
        if not existing_info:
            # Return indices of top 2 candidates (or fewer if less than 2)
            selected = [info.get("index", i) for i, info in enumerate(candidate_info[:2])]
            logger.info(f"No existing questions, selected top candidates: {selected}")
            return selected
        
        # Create a list of existing shortTexts (lowercase for case-insensitive comparison)
        existing_shorttexts = [
            existing.get("shortText", "").lower() 
            for existing in existing_info 
            if existing.get("shortText")
        ]
        
        # Initialize list of selected indices and their shortTexts
        selected_indices = []
        selected_shorttexts = []
        
        # Process candidates in order (already sorted by priority)
        for i, candidate in enumerate(candidate_info):
            # Stop once we have 2 questions
            if len(selected_indices) >= 2:
                break
                
            original_idx = candidate.get("index", i)
            candidate_shorttext = candidate.get("shortText", "").lower()
            
            # Skip candidates without shortText
            if not candidate_shorttext:
                logger.info(f"Skipping candidate {i} (index {original_idx}): No shortText")
                continue
            
            # Check if this candidate is a duplicate of an existing question
            is_duplicate = False
            
            # First check against existing questions
            for existing_shorttext in existing_shorttexts:
                if self._is_similar_shorttext(candidate_shorttext, existing_shorttext):
                    is_duplicate = True
                    logger.info(f"Candidate {i} (index {original_idx}) '{candidate_shorttext}' is similar to existing '{existing_shorttext}'")
                    break
            
            # Then check against already selected candidates
            if not is_duplicate:
                for selected_shorttext in selected_shorttexts:
                    if self._is_similar_shorttext(candidate_shorttext, selected_shorttext):
                        is_duplicate = True
                        logger.info(f"Candidate {i} (index {original_idx}) '{candidate_shorttext}' is similar to already selected '{selected_shorttext}'")
                        break
            
            # If not a duplicate, select this candidate
            if not is_duplicate:
                selected_indices.append(original_idx)
                selected_shorttexts.append(candidate_shorttext)
                logger.info(f"Selected candidate {i} (index {original_idx}) '{candidate_shorttext}'")
        
        logger.info(f"Logic-based selection complete. Selected {len(selected_indices)} questions: {selected_indices}")
        return selected_indices
    
    def _is_similar_shorttext(self, shorttext1, shorttext2):
        """
        Compare two shortText strings to determine if they are similar.
        Only exact matches are considered similar.
        
        Args:
            shorttext1 (str): First shortText string
            shorttext2 (str): Second shortText string
            
        Returns:
            bool: True if the shortTexts are identical, False otherwise
        """
        # Only exact match is considered similar
        return shorttext1.lower() == shorttext2.lower()
    
    def _generate_step1_questions(self, agent_scm, existing_question_texts):
        """
        Generate questions for Step 1 (Node Discovery).
        
        Args:
            agent_scm (dict): The current SCM
            existing_question_texts (list): List of existing question texts
            
        Returns:
            list: List of Step 1 questions
        """
        questions = []
        
        # Find potential nodes to ask about - focus on candidate nodes
        candidates = []
        for node_id, node in agent_scm.get('nodes', {}).items():
            # Focus on nodes with status = 'candidate' 
            if node.get('status') == 'candidate':
                candidates.append((node_id, node))
        
        # Sort by frequency and importance (higher first) and select top candidates
        candidates.sort(key=lambda x: (x[1].get('frequency', 1), x[1].get('importance', 0)), reverse=True)
        
        # Generate a question for each candidate (up to 3)
        for node_id, node in candidates[:3]:
            template = random.choice(self.step1_templates)
            question_text = template.format(node=node.get('label', 'this factor'))
            
            # Skip if similar question already exists
            if any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                continue
            
            questions.append({
                "question": question_text,
                "shortText": f"About {node.get('label', 'factor')}",
                "type": "node_discovery",
                "node_id": node_id
            })
        
        # If no candidates, ask a general question to discover new nodes
        if not questions:
            general_questions = [
                "What other factors do you think are important in this issue?",
                "Are there any aspects we haven't discussed that influence your thinking on this topic?",
                "What else do you consider when thinking about this issue?"
            ]
            
            question_text = random.choice(general_questions)
            if not any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                questions.append({
                    "question": question_text,
                    "shortText": "Other factors",
                    "type": "general_discovery"
                })
        
        return questions
    
    def _generate_step2_combined_questions(self, agent_scm, anchor_queue, existing_question_texts):
        """
        Generate combined questions for Step 2 (Anchor Expansion & Relationship Qualification).
        This combines the previous Step 2 and Step 3 functionality.
        
        Args:
            agent_scm (dict): The current SCM
            anchor_queue (list): List of anchor node IDs
            existing_question_texts (list): List of existing question texts
            
        Returns:
            list: List of combined Step 2 questions
        """
        questions = []
        
        # Skip if no anchors
        if not anchor_queue:
            return questions
        
        # Check for stance node
        stance_node_id = agent_scm.get("stance_node_id")
        stance_node = None
        if stance_node_id and stance_node_id in agent_scm.get('nodes', {}):
            stance_node = agent_scm['nodes'][stance_node_id]
        
        # PRIORITY 1: Find anchor nodes with out-degree 0 that need connection to stance node
        if stance_node:
            zero_outdegree_anchors = []
            for node_id in anchor_queue:
                if node_id == stance_node_id:
                    continue
                    
                if node_id in agent_scm.get('nodes', {}):
                    node = agent_scm['nodes'][node_id]
                    outgoing_edges = node.get('outgoing_edges', [])
                    
                    # Check if this node has no outgoing edges and is not already connected to stance node
                    if len(outgoing_edges) == 0:
                        # Check if there's no edge from this node to stance node
                        connected_to_stance = False
                        for edge_id in agent_scm.get('edges', {}):
                            edge = agent_scm['edges'][edge_id]
                            if edge.get('source') == node_id and edge.get('target') == stance_node_id:
                                connected_to_stance = True
                                break
                        
                        if not connected_to_stance:
                            zero_outdegree_anchors.append(node_id)
            
            # If we found qualifying anchors, ask about their relationship to stance
            if zero_outdegree_anchors:
                # Select the first qualifying anchor
                anchor_id = zero_outdegree_anchors[0]
                anchor_node = agent_scm['nodes'][anchor_id]
                
                # Create a question about relationship with stance node, including modifier guidance
                template = random.choice(self.step2_combined_templates['relationship'])
                question_text = template.format(
                    from_node=anchor_node.get('label', 'this factor'),
                    to_node=stance_node.get('label', 'your stance')
                )
                
                # Add modifier guidance
                modifier_guidance = " Does it have a positive effect (increasing it) or a negative effect (decreasing it)? How strong is this effect?"
                if not question_text.endswith('?'):
                    modifier_guidance = "?" + modifier_guidance
                
                if not any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                    questions.append({
                        "question": question_text + modifier_guidance,
                        "shortText": f"Relationship: {anchor_node.get('label', 'factor')} → Stance",
                        "type": "stance_relationship",
                        "node_id": anchor_id,
                        "stance_node_id": stance_node_id
                    })
        
        # PRIORITY 2: For existing anchor nodes, prioritize finding upstream relationships (what affects them)
        if len(questions) < 2:
            # Select an anchor to focus on (prioritize those with fewer incoming connections)
            anchor_incoming_connections = {}
            for anchor_id in anchor_queue:
                if anchor_id in agent_scm.get('nodes', {}) and agent_scm['nodes'][anchor_id].get('status') == 'anchor':
                    node = agent_scm['nodes'][anchor_id]
                    # Focus specifically on incoming edges (upstream)
                    incoming_connections = len(node.get('incoming_edges', []))
                    anchor_incoming_connections[anchor_id] = incoming_connections
            
            # Sort by incoming connections (fewer first)
            sorted_anchors = sorted(anchor_incoming_connections.items(), key=lambda x: x[1])
            
            # Get the anchor with fewest incoming connections
            if sorted_anchors:
                anchor_id, _ = sorted_anchors[0]
                anchor_node = agent_scm['nodes'][anchor_id]
                
                # Generate upstream question (what affects this anchor)
                template = random.choice(self.step2_combined_templates['upstream'])
                question_text = template.format(node=anchor_node.get('label', 'this factor'))
                
                # Add modifier guidance if needed
                if "strong" not in question_text.lower() or "weak" not in question_text.lower():
                    question_text += " Please also indicate if these influences are positive (increasing) or negative (decreasing)."
                
                if not any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                    questions.append({
                        "question": question_text,
                        "shortText": f"Factors affecting {anchor_node.get('label', 'factor')}",
                        "type": "anchor_upstream_with_strength",
                        "node_id": anchor_id
                    })
        
        # PRIORITY 3: Find edges that need qualification (strength/modifier info)
        if len(questions) < 2:
            edge_candidates = []
            for edge_id, edge in agent_scm.get('edges', {}).items():
                from_node_id = edge.get('source')
                to_node_id = edge.get('target')
                
                if from_node_id in agent_scm.get('nodes', {}) and to_node_id in agent_scm.get('nodes', {}):
                    from_node = agent_scm['nodes'][from_node_id]
                    to_node = agent_scm['nodes'][to_node_id]
                    
                    # Prioritize edges between anchor nodes
                    is_anchor_edge = (from_node.get('status') == 'anchor' and to_node.get('status') == 'anchor')
                    edge_candidates.append((edge_id, from_node, to_node, is_anchor_edge))
            
            # Sort edge candidates, prioritizing anchor-to-anchor edges
            edge_candidates.sort(key=lambda x: (0 if x[3] else 1))
            
            # If we have edge candidates, ask about relationship strength for one of them
            if edge_candidates:
                edge_id, from_node, to_node, _ = edge_candidates[0]  # Take the highest priority edge
                template = random.choice(self.step2_combined_templates['relationship'])
                question_text = template.format(
                    from_node=from_node.get('label', 'the first factor'),
                    to_node=to_node.get('label', 'the second factor')
                )
                
                # Add modifier guidance if not already present
                if "positive" not in question_text.lower() or "negative" not in question_text.lower():
                    modifier_guidance = " Is it a positive influence (increases) or negative influence (decreases)? How strong is this effect?"
                    if not question_text.endswith('?'):
                        modifier_guidance = "?" + modifier_guidance
                    question_text += modifier_guidance
                
                if not any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                    questions.append({
                        "question": question_text,
                        "shortText": f"Relationship: {from_node.get('label', 'factor')} → {to_node.get('label', 'factor')}",
                        "type": "relationship_qualification",
                        "edge_id": edge_id
                    })
        
        return questions

    def _generate_motif_questions(self, agent_scm, existing_question_texts):
        """
        Generate questions based on graph motifs to complete patterns.
        
        Args:
            agent_scm (dict): The current SCM
            existing_question_texts (list): List of existing question texts
            
        Returns:
            list: List of motif-based questions
        """
        questions = []
        
        # Find triads (A→B→C, potential A→C)
        triads = self._find_triads(agent_scm)
        if triads:
            triad = random.choice(triads)
            node1, node2, node3 = triad
            
            question_text = self.motif_templates['triad'].format(
                node1=agent_scm['nodes'][node1].get('label', 'the first factor'),
                node2=agent_scm['nodes'][node2].get('label', 'the second factor'),
                node3=agent_scm['nodes'][node3].get('label', 'the third factor')
            )
            
            if not any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                questions.append({
                    "question": question_text,
                    "shortText": "Complete relationship pattern",
                    "type": "motif_triad",
                    "nodes": [node1, node2, node3]
                })
        
        # Find potential mediators (A→C, potential A→B→C)
        mediators = self._find_potential_mediators(agent_scm)
        if mediators and not questions:  # Only add if no triad question
            mediator = random.choice(mediators)
            node1, node3 = mediator
            
            question_text = self.motif_templates['mediator'].format(
                node1=agent_scm['nodes'][node1].get('label', 'the first factor'),
                node3=agent_scm['nodes'][node3].get('label', 'the second factor')
            )
            
            if not any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                questions.append({
                    "question": question_text,
                    "shortText": "Intermediate factors",
                    "type": "motif_mediator",
                    "nodes": [node1, node3]
                })
        
        return questions
    
    def _find_triads(self, agent_scm):
        """
        Find potential triads (A→B→C) where A→C might exist.
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            list: List of triads as (node1_id, node2_id, node3_id)
        """
        triads = []
        edges = agent_scm.get('edges', {})
        
        # Map from node to its outgoing connections
        outgoing = {}
        for edge_id, edge in edges.items():
            from_node = edge.get('from')
            to_node = edge.get('to')
            if from_node and to_node:
                outgoing.setdefault(from_node, []).append(to_node)
        
        # Find chains A→B→C where A→C doesn't exist
        for node1, node1_targets in outgoing.items():
            for node2 in node1_targets:
                if node2 in outgoing:
                    for node3 in outgoing[node2]:
                        # Check if A→C doesn't exist
                        if node3 not in node1_targets:
                            # Check if nodes exist
                            if all(n in agent_scm.get('nodes', {}) for n in [node1, node2, node3]):
                                triads.append((node1, node2, node3))
        
        return triads
    
    def _find_potential_mediators(self, agent_scm):
        """
        Find potential mediators for A→C relationships.
        
        Args:
            agent_scm (dict): The current SCM
            
        Returns:
            list: List of relationships that might have mediators as (from_node_id, to_node_id)
        """
        mediators = []
        edges = agent_scm.get('edges', {})
        
        # Direct connections
        direct_connections = []
        for edge_id, edge in edges.items():
            from_node = edge.get('from')
            to_node = edge.get('to')
            if from_node and to_node:
                direct_connections.append((from_node, to_node))
        
        # Find direct connections that might have mediators
        # (ones with greater semantic distance)
        for from_node, to_node in direct_connections:
            # Simple heuristic: look at edge length (in real implementation, use semantic distance)
            if from_node in agent_scm.get('nodes', {}) and to_node in agent_scm.get('nodes', {}):
                from_label = agent_scm['nodes'][from_node].get('label', '')
                to_label = agent_scm['nodes'][to_node].get('label', '')
                
                # If semantic roles are different, might have mediator
                from_role = agent_scm['nodes'][from_node].get('semantic_role')
                to_role = agent_scm['nodes'][to_node].get('semantic_role')
                
                if from_role and to_role and from_role != to_role:
                    mediators.append((from_node, to_node))
        
        return mediators
    
    def _similar_questions(self, question1, question2, threshold=0.7):
        """
        Check if two questions are similar (simplified).
        
        Args:
            question1 (str): First question
            question2 (str): Second question
            threshold (float): Similarity threshold
            
        Returns:
            bool: True if questions are similar, False otherwise
        """
        # Simple word overlap for similarity (in real implementation, use embeddings)
        words1 = set(question1.lower().split())
        words2 = set(question2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        overlap = len(intersection) / max(len(words1), len(words2))
        
        return overlap >= threshold
    
    def generate_additional_questions(self, scm, current_step, current_questions, force_generate=False, focus_on_nodes=False, current_qa_count=0, max_qa_count=None):
        """
        Generate additional questions when more are needed to reach minimum requirements.
        
        Args:
            scm (dict): The current state of the Structural Causal Model
            current_step (str): The current step of the interview
            current_questions (list): List of questions already asked
            force_generate (bool): Whether to force generation of questions
            focus_on_nodes (bool): Whether to focus specifically on discovering more nodes
            current_qa_count (int, optional): Current number of QA pairs
            max_qa_count (int, optional): Maximum number of QA pairs allowed
            
        Returns:
            list: List of additional questions
        """
        llm_logger.log_separator("ADDITIONAL QUESTION GENERATION")
        logger.info(f"Generating additional questions (force={force_generate}, focus_on_nodes={focus_on_nodes})")
        
        # Check if we've reached the maximum QA count
        if max_qa_count and current_qa_count >= max_qa_count:
            logger.info(f"Maximum QA count reached ({current_qa_count}/{max_qa_count}). No additional questions will be generated.")
            llm_logger.log_separator("ADDITIONAL QUESTION GENERATION CANCELLED - MAX QA COUNT REACHED")
            return []
            
        additional_questions = []
        
        # If we're focusing on node discovery or forced to generate questions
        if focus_on_nodes or (force_generate and current_step == "node_discovery"):
            llm_logger.log_separator("FORCED NODE DISCOVERY QUESTIONS")
            try:
                # Generate more node discovery questions
                node_questions = self._generate_forced_node_discovery_questions(scm, current_questions)
                if isinstance(node_questions, list):
                    additional_questions.extend(node_questions)
                else:
                    logger.error(f"_generate_forced_node_discovery_questions returned non-list: {type(node_questions)}")
            except Exception as e:
                logger.error(f"Error generating node discovery questions: {str(e)}")
            
        # If we need to force generate questions for edge construction
        elif force_generate and current_step == "edge_construction":
            llm_logger.log_separator("FORCED EDGE CONSTRUCTION QUESTIONS")
            try:
                # Generate more edge construction questions
                edge_questions = self._generate_forced_edge_construction_questions(scm, current_questions)
                if isinstance(edge_questions, list):
                    additional_questions.extend(edge_questions)
                else:
                    logger.error(f"_generate_forced_edge_construction_questions returned non-list: {type(edge_questions)}")
            except Exception as e:
                logger.error(f"Error generating edge construction questions: {str(e)}")
            
        # If we still don't have enough questions, add some general questions
        if not additional_questions or force_generate:
            llm_logger.log_separator("GENERAL QUESTIONS")
            try:
                general_questions = self._generate_general_questions(current_questions)
                if isinstance(general_questions, list):
                    additional_questions.extend(general_questions)
                else:
                    logger.error(f"_generate_general_questions returned non-list: {type(general_questions)}")
            except Exception as e:
                logger.error(f"Error generating general questions: {str(e)}")
            
        # Ensure we have at least 1-3 questions
        if additional_questions:
            logger.info(f"Generated {len(additional_questions)} additional questions")
            # Make sure each question is a proper question object
            formatted_questions = []
            for q in additional_questions[:3]:
                if isinstance(q, str):
                    # Convert string questions to proper format
                    formatted_questions.append({
                        "id": f"followup_{uuid.uuid4().hex[:8]}_{int(time.time())}",
                        "question": q,
                        "shortText": q[:30] + "..." if len(q) > 30 else q,
                        "answer": ""
                    })
                elif isinstance(q, dict) and "question" in q:
                    # Add missing fields if needed
                    if "id" not in q:
                        q["id"] = f"followup_{uuid.uuid4().hex[:8]}_{int(time.time())}"
                    if "shortText" not in q:
                        q["shortText"] = q["question"][:30] + "..." if len(q["question"]) > 30 else q["question"]
                    if "answer" not in q:
                        q["answer"] = ""
                    formatted_questions.append(q)
            logger.info(f"Generated {len(formatted_questions)} additional questions")
            llm_logger.log_separator("ADDITIONAL QUESTION GENERATION COMPLETE")
            return formatted_questions
        
        # If max QA count is reached, don't return any fallback questions
        if max_qa_count and current_qa_count >= max_qa_count:
            logger.info("Maximum QA count reached, not adding fallback question")
            return []
            
        # Fallback to a single general question if nothing else worked
        fallback_question = {
            "id": f"followup_{uuid.uuid4().hex[:8]}_{int(time.time())}",
            "question": "Could you elaborate more on your previous answer?",
            "shortText": "Further elaboration",
            "answer": ""
        }
        logger.info("Using fallback question as no others were generated")
        llm_logger.log_separator("ADDITIONAL QUESTION GENERATION COMPLETE")
        return [fallback_question]  # Return as a list with a properly formatted question
    
    def _generate_forced_node_discovery_questions(self, scm, current_questions):
        """
        Generate additional node discovery questions when needed.
        """
        # More specific node discovery questions that probe deeper
        probe_questions = [
            "What underlying beliefs or values shape your perspective on this topic?",
            "Are there any external factors or constraints that influence your thinking?",
            "How do you think societal or cultural factors affect this issue?",
            "What personal experiences have shaped your understanding of this topic?",
            "Are there any technical or practical considerations we haven't discussed?",
            "How do ethical considerations factor into your thinking on this subject?",
            "What long-term implications do you see from this that we haven't covered?",
            "How might different stakeholders view this issue differently?",
            "What knowledge gaps or uncertainties affect your perspective?"
        ]
        
        # Filter questions that are too similar to what's been asked
        filtered_questions = [q for q in probe_questions 
                           if not any(self._is_similar_question(q, existing) for existing in current_questions)]
        
        # If we have a stance node, create targeted questions about it
        stance_node_id = scm.get("stance_node_id")
        if stance_node_id and stance_node_id in scm.get("nodes", {}):
            stance_label = scm["nodes"][stance_node_id].get("label", "your stance")
            
            stance_questions = [
                f"What do you think is the most important factor that shapes {stance_label}?",
                f"How did you first develop your views on {stance_label}?",
                f"What would make you reconsider your position on {stance_label}?",
                f"What concerns do you have related to {stance_label}?"
            ]
            
            # Add filtered stance questions
            for q in stance_questions:
                if not any(self._is_similar_question(q, existing) for existing in current_questions):
                    filtered_questions.append(q)
        
        # Randomize the order to get varied questions
        random.shuffle(filtered_questions)
        return filtered_questions
    
    def _generate_forced_edge_construction_questions(self, scm, current_questions):
        """
        Generate additional edge construction questions when needed.
        """
        questions = []
        
        # Find nodes with few or no connections
        node_connection_count = {}
        for node_id in scm.get("nodes", {}):
            node_connection_count[node_id] = 0
            
        for edge in scm.get("edges", {}).values():
            if edge.get("from") in node_connection_count:
                node_connection_count[edge.get("from")] += 1
            if edge.get("to") in node_connection_count:
                node_connection_count[edge.get("to")] += 1
        
        # Focus on nodes with fewer connections
        isolated_nodes = [node_id for node_id, count in node_connection_count.items() if count <= 1]
        
        # Generate questions about isolated nodes
        for node_id in isolated_nodes:
            if node_id in scm.get("nodes", {}):
                node_label = scm["nodes"][node_id].get("label", "")
                
                questions.extend([
                    f"What factors do you think influence {node_label}?",
                    f"How does {node_label} affect other aspects we've discussed?",
                    f"Could you elaborate on how {node_label} connects to your other views?"
                ])
        
        # Questions about causal chains
        if scm.get("edges"):
            questions.append("Do you see any chain of cause and effect across multiple factors we've discussed?")
            
        # Filter out questions that are too similar to existing ones
        filtered_questions = [q for q in questions 
                           if not any(self._is_similar_question(q, existing) for existing in current_questions)]
        
        # Randomize the order
        random.shuffle(filtered_questions)
        return filtered_questions
    
    def _generate_general_questions(self, current_questions):
        """
        Generate general questions that can work in any step.
        """
        general_questions = [
            "Could you elaborate more on your previous answer?",
            "Is there anything else important about this topic that we haven't covered?",
            "How confident are you in the views you've expressed so far?",
            "What nuances or complexities in this topic do you think are often overlooked?",
            "If you had to summarize your main points on this topic, what would they be?",
            "How have your views on this topic evolved over time?",
            "What sources of information have shaped your understanding of this issue?",
            "Are there any important distinctions or clarifications you'd like to make about what we've discussed?",
            "What questions do you think should be asked about this topic that we haven't covered?"
        ]
        
        # Filter out questions that are too similar to existing ones
        filtered_questions = [q for q in general_questions 
                           if not any(self._is_similar_question(q, existing) for existing in current_questions)]
        
        # Randomize the order
        random.shuffle(filtered_questions)
        return filtered_questions
    
    def _is_similar_question(self, q1, q2):
        """
        Check if two questions are similar enough to be considered duplicates.
        """
        # Simple text-based similarity check
        q1_lower = q1.lower()
        q2_lower = q2.lower()
        
        # Check for exact matches or significant overlap
        if q1_lower == q2_lower:
            return True
            
        # Check for significant word overlap
        words1 = set(q1_lower.split())
        words2 = set(q2_lower.split())
        
        # If more than 60% of words overlap, consider similar
        if len(words1) > 0 and len(words2) > 0:
            overlap = len(words1.intersection(words2))
            smaller_set = min(len(words1), len(words2))
            if overlap / smaller_set > 0.6:
                return True
                
        return False
    
    def _log_candidate_questions(self, candidate_questions):
        """
        Log the candidate questions with their priority information.
        
        Args:
            candidate_questions (list): List of candidate question objects
        """
        llm_logger.log_separator("CANDIDATE QUESTION QUEUE")
        logger.info(f"Candidate question queue contains {len(candidate_questions)} questions:")
        
        # Group questions by priority
        priority_groups = {}
        for i, q in enumerate(candidate_questions):
            priority = q.get("priority", 10)
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append((i, q))
        
        # Log questions by priority group
        for priority in sorted(priority_groups.keys()):
            questions = priority_groups[priority]
            logger.info(f"Priority {priority} ({len(questions)} questions):")
            
            for i, (idx, q) in enumerate(questions):
                # Get question type and shortened text
                q_type = q.get("type", "unknown")
                question_text = q.get("question", "")
                short_text = question_text[:80] + "..." if len(question_text) > 80 else question_text
                
                # Get the shortText field if available
                purpose_text = q.get("shortText", "")
                
                # Log the question with its index in the queue and shortText
                logger.info(f"  [{idx}] Type: {q_type}, ShortText: '{purpose_text}', Question: {short_text}")
        
        llm_logger.log_separator("END OF CANDIDATE QUESTION QUEUE") 