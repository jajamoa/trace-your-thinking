"""
Question Generator Module
Responsible for generating follow-up questions based on the current state of the SCM.
"""
import uuid
import time
import random


class QuestionGenerator:
    """
    Generate follow-up questions based on the current state of the SCM.
    """
    
    def __init__(self):
        """Initialize the question generator"""
        # Templates for different question types
        self.phase1_templates = [
            "Could you tell me more about {node}?",
            "What factors do you think influence {node}?",
            "How would you describe {node} in your own words?",
            "Is {node} a significant factor in your thinking about this issue?",
            "What comes to mind when you think about {node}?"
        ]
        
        self.phase2_upstream_templates = [
            "What factors do you think influence {node}?",
            "What causes changes in {node}?",
            "What might lead to increases or decreases in {node}?",
            "What do you think are the root causes of {node}?",
            "What factors might affect how {node} develops or changes?"
        ]
        
        self.phase2_downstream_templates = [
            "How does {node} affect other aspects of this issue?",
            "What consequences might result from changes in {node}?",
            "What happens when {node} increases or decreases?",
            "How does {node} influence your overall stance?",
            "What effects does {node} have on other factors you've mentioned?"
        ]
        
        self.phase3_function_templates = [
            "How strong is the influence of {from_node} on {to_node}?",
            "Is the effect of {from_node} on {to_node} immediate or does it only happen under certain conditions?",
            "Would you say the relationship between {from_node} and {to_node} is linear, or does it have a threshold?",
            "How confident are you about the connection between {from_node} and {to_node}?",
            "Can small changes in {from_node} lead to large changes in {to_node}, or is the effect more proportional?"
        ]
        
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
    
    def generate_follow_up_questions(self, agent_scm, current_phase, anchor_queue, existing_question_texts=None):
        """
        Generate follow-up questions based on the current SCM state and phase.
        
        Args:
            agent_scm (dict): The current SCM
            current_phase (int): The current interview phase (1, 2, or 3)
            anchor_queue (list): List of anchor node IDs
            existing_question_texts (list, optional): List of existing question texts to avoid duplicates
            
        Returns:
            list: List of follow-up question objects
        """
        if existing_question_texts is None:
            existing_question_texts = []
        
        follow_up_questions = []
        
        # Generate questions based on the current phase
        if current_phase == 1:
            # Phase 1: Node Discovery
            questions = self._generate_phase1_questions(agent_scm, existing_question_texts)
            follow_up_questions.extend(questions)
        
        elif current_phase == 2:
            # Phase 2: Anchor Expansion
            questions = self._generate_phase2_questions(agent_scm, anchor_queue, existing_question_texts)
            follow_up_questions.extend(questions)
        
        elif current_phase == 3:
            # Phase 3: Function Fitting
            questions = self._generate_phase3_questions(agent_scm, existing_question_texts)
            follow_up_questions.extend(questions)
        
        # Always check for potential motifs to complete
        motif_questions = self._generate_motif_questions(agent_scm, existing_question_texts)
        follow_up_questions.extend(motif_questions)
        
        # Limit number of questions based on phase
        max_questions = 3 if current_phase == 1 else (2 if current_phase == 2 else 1)
        if len(follow_up_questions) > max_questions:
            follow_up_questions = follow_up_questions[:max_questions]
        
        # Ensure each question has required fields
        for q in follow_up_questions:
            q["id"] = q.get("id") or f"followup_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            q["shortText"] = q.get("shortText") or q["question"][:50] + "..."
            q["answer"] = q.get("answer") or ""
        
        return follow_up_questions
    
    def _generate_phase1_questions(self, agent_scm, existing_question_texts):
        """
        Generate questions for Phase 1 (Node Discovery).
        
        Args:
            agent_scm (dict): The current SCM
            existing_question_texts (list): List of existing question texts
            
        Returns:
            list: List of Phase 1 questions
        """
        questions = []
        
        # Find potential nodes to ask about
        candidates = []
        for node_id, node in agent_scm.get('nodes', {}).items():
            # Focus on nodes with frequency = 1 (mentioned but not confirmed)
            if node.get('appearance', {}).get('frequency', 0) == 1:
                candidates.append((node_id, node))
        
        # Sort by frequency (higher first) and select top 3
        candidates.sort(key=lambda x: x[1].get('appearance', {}).get('frequency', 0), reverse=True)
        
        # Generate a question for each candidate (up to 3)
        for node_id, node in candidates[:3]:
            template = random.choice(self.phase1_templates)
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
    
    def _generate_phase2_questions(self, agent_scm, anchor_queue, existing_question_texts):
        """
        Generate questions for Phase 2 (Anchor Expansion).
        
        Args:
            agent_scm (dict): The current SCM
            anchor_queue (list): List of anchor node IDs
            existing_question_texts (list): List of existing question texts
            
        Returns:
            list: List of Phase 2 questions
        """
        questions = []
        
        # Skip if no anchors
        if not anchor_queue:
            return questions
        
        # Select an anchor to focus on
        # Prioritize anchors with fewer connections
        anchor_connections = {}
        for anchor_id in anchor_queue:
            if anchor_id in agent_scm.get('nodes', {}):
                node = agent_scm['nodes'][anchor_id]
                connections = len(node.get('incoming_edges', [])) + len(node.get('outgoing_edges', []))
                anchor_connections[anchor_id] = connections
        
        # Sort by connections (fewer first)
        sorted_anchors = sorted(anchor_connections.items(), key=lambda x: x[1])
        
        # Get the anchor with fewest connections
        if sorted_anchors:
            anchor_id, _ = sorted_anchors[0]
            anchor_node = agent_scm['nodes'][anchor_id]
            
            # Generate upstream question (what affects this anchor)
            upstream_template = random.choice(self.phase2_upstream_templates)
            upstream_question = upstream_template.format(node=anchor_node.get('label', 'this factor'))
            
            if not any(self._similar_questions(upstream_question, existing) for existing in existing_question_texts):
                questions.append({
                    "question": upstream_question,
                    "shortText": f"Influences on {anchor_node.get('label', 'factor')}",
                    "type": "anchor_upstream",
                    "node_id": anchor_id
                })
            
            # Generate downstream question (what does this anchor affect)
            downstream_template = random.choice(self.phase2_downstream_templates)
            downstream_question = downstream_template.format(node=anchor_node.get('label', 'this factor'))
            
            if not any(self._similar_questions(downstream_question, existing) for existing in existing_question_texts):
                questions.append({
                    "question": downstream_question,
                    "shortText": f"Effects of {anchor_node.get('label', 'factor')}",
                    "type": "anchor_downstream",
                    "node_id": anchor_id
                })
        
        return questions
    
    def _generate_phase3_questions(self, agent_scm, existing_question_texts):
        """
        Generate questions for Phase 3 (Function Fitting).
        
        Args:
            agent_scm (dict): The current SCM
            existing_question_texts (list): List of existing question texts
            
        Returns:
            list: List of Phase 3 questions
        """
        questions = []
        
        # Find edges that could use function fitting
        candidates = []
        for edge_id, edge in agent_scm.get('edges', {}).items():
            # Focus on edges with minimal function information
            if edge.get('function', {}).get('function_type') == 'sigmoid':  # Default type
                from_node_id = edge.get('from')
                to_node_id = edge.get('to')
                
                if from_node_id in agent_scm.get('nodes', {}) and to_node_id in agent_scm.get('nodes', {}):
                    from_node = agent_scm['nodes'][from_node_id]
                    to_node = agent_scm['nodes'][to_node_id]
                    candidates.append((edge_id, from_node, to_node))
        
        # Generate a question for a random candidate
        if candidates:
            edge_id, from_node, to_node = random.choice(candidates)
            template = random.choice(self.phase3_function_templates)
            question_text = template.format(
                from_node=from_node.get('label', 'the first factor'),
                to_node=to_node.get('label', 'the second factor')
            )
            
            if not any(self._similar_questions(question_text, existing) for existing in existing_question_texts):
                questions.append({
                    "question": question_text,
                    "shortText": f"Relationship: {from_node.get('label', 'factor')} → {to_node.get('label', 'factor')}",
                    "type": "function_fitting",
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