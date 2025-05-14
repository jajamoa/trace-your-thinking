"""
Simplified LLM-based Node Extractor
Responsible for extracting nodes from QA pairs using DashScope API.
Also provides edge extraction and function parameter extraction functionality.
"""
import os
import json
import uuid
import time
import re
import logging
from collections import Counter
import dashscope
from pathlib import Path
from dotenv import load_dotenv

# Import session manager
from session_manager import session_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QwenLLMExtractor:
    """
    Simplified extractor that focuses on nodes with a stance node as starting point.
    Also provides edge extraction functionality.
    """
    
    def __init__(self, api_key=None, model="qwen-plus", temperature=0.1, node_candidates=None):
        """
        Initialize the LLM extractor with DashScope API configuration.
        
        Args:
            api_key (str, optional): DashScope API key. Defaults to environment variable.
            model (str, optional): Model name to use. Defaults to "qwen-plus".
            temperature (float, optional): Temperature parameter for LLM output. Lower values (0.01-0.1) produce more deterministic responses. Defaults to 0.1.
            node_candidates (Counter, optional): Existing node candidates counter. Defaults to new empty Counter.
        """
        # Try to load API key from parent directory .env or .env.local file
        parent_env_path = Path(__file__).parent.parent / '.env'
        parent_env_local_path = Path(__file__).parent.parent / '.env.local'
        
        if parent_env_local_path.exists():
            load_dotenv(dotenv_path=parent_env_local_path)
            logger.info(f"Loaded environment variables from {parent_env_local_path}")
        elif parent_env_path.exists():
            load_dotenv(dotenv_path=parent_env_path)
            logger.info(f"Loaded environment variables from {parent_env_path}")
        
        # Use provided API key, or get from environment variable loaded from .env or .env.local file
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            error_msg = "DashScope API key is required. Please provide it or set DASHSCOPE_API_KEY in .env or .env.local file in the parent directory."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"LLM Extractor initialized with model: {model}, temperature: {temperature}")
        # Set model and temperature
        self.model = model
        self.temperature = temperature
        
        # Node tracking for frequency analysis
        self.node_candidates = node_candidates if node_candidates is not None else Counter()
        # Track stance node
        self.stance_node_created = False
        # Minimum frequency to promote a node candidate
        self.min_node_frequency = 2
    
    def get_node_candidates(self):
        """
        Get the current node candidates counter.
        
        Returns:
            Counter: The current node candidates counter
        """
        return self.node_candidates
        
    def set_node_candidates(self, node_candidates):
        """
        Set the node candidates counter.
        
        Args:
            node_candidates (Counter): The node candidates counter to set
        """
        self.node_candidates = node_candidates
    
    def extract_nodes(self, qa_pair, ensure_stance_node=True, session_id=None):
        """
        Extract potential nodes from a QA pair using LLM.
        Always ensures a stance node is created if none exists.
        
        Args:
            qa_pair (dict): A question-answer pair
            ensure_stance_node (bool): Whether to ensure a stance node is created
            session_id (str, optional): Session identifier for persistent tracking
            
        Returns:
            dict: Dictionary of extracted nodes with metadata
        """
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        qa_id = qa_pair.get('id')
        
        logger.info(f"Extracting nodes from QA pair {qa_id}")
        logger.info(f"Question: {question[:50]}...")
        logger.info(f"Answer: {answer[:50]}...")
        
        # Ensure qa_id has proper format
        if not qa_id or not isinstance(qa_id, str):
            qa_id = f"qa_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        elif not qa_id.startswith("qa_"):
            qa_id = f"qa_{qa_id}"
        
        # Use session manager if session_id is provided
        if session_id:
            # Get node candidates from session manager
            self.node_candidates = session_manager.get_node_candidates(session_id)
            logger.info(f"Retrieved node candidates from session {session_id}: {dict(self.node_candidates)}")
        
        try:
            # Extract nodes using LLM
            extracted_nodes = self._extract_nodes_with_llm(question, answer, qa_id, session_id)
            
            # If no nodes were extracted or we need to ensure a stance node
            if (not extracted_nodes or ensure_stance_node) and not self.stance_node_created:
                stance_node = self._create_stance_node(question, answer, qa_id, session_id)
                if stance_node:
                    stance_node_id = list(stance_node.keys())[0]
                    extracted_nodes.update(stance_node)
                    self.stance_node_created = True
                    logger.info(f"Created stance node: {extracted_nodes[stance_node_id]['label']}")
            
            logger.info(f"Extracted {len(extracted_nodes)} nodes")
            
            # Update session manager if session_id is provided
            if session_id:
                session_manager.update_node_candidates(session_id, self.node_candidates)
                logger.info(f"Updated node candidates in session {session_id}")
            
            return extracted_nodes
            
        except Exception as e:
            logger.error(f"Error extracting nodes with LLM: {e}")
            # Fallback to creating a stance node if all else fails
            if ensure_stance_node and not self.stance_node_created:
                stance_node = self._create_stance_node(question, answer, qa_id, session_id)
                if stance_node:
                    stance_node_id = list(stance_node.keys())[0]
                    logger.info(f"Created fallback stance node: {stance_node[stance_node_id]['label']}")
                    self.stance_node_created = True
                    return stance_node
            return {}
    
    def extract_edge(self, qa_pair, session_id=None):
        """
        Extract potential causal relationships (edges) from a QA pair using LLM.
        
        Args:
            qa_pair (dict): A question-answer pair
            session_id (str, optional): Session identifier for persistent tracking
            
        Returns:
            dict or None: Extracted edge information or None if no edge found
        """
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        qa_id = qa_pair.get('id')
        
        logger.info(f"Extracting edge from QA pair {qa_id}")
        
        # Use session manager if session_id is provided
        if session_id:
            # We don't actually need the node candidates for edge extraction,
            # but we might want to log the session activity
            session_manager._update_session_activity(session_id)
        
        # Prepare a prompt for edge extraction
        prompt = self._create_edge_extraction_prompt(question, answer)
        
        try:
            # Call the LLM to extract edges
            extracted_edge_json = self._call_llm_for_structured_output(prompt)
            
            if extracted_edge_json and 'edges' in extracted_edge_json and extracted_edge_json['edges']:
                edge_data = extracted_edge_json['edges'][0]  # Take the first edge
                
                # Get direction, confidence and strength
                direction = edge_data.get('direction', 'positive')
                confidence = edge_data.get('confidence', 0.7)
                strength = edge_data.get('strength', 0.7)
                
                # Calculate the modifier (-1.0 to 1.0) based on direction and strength
                if direction == 'negative':
                    modifier = -strength
                else:
                    modifier = strength
                
                # Create edge with metadata aligned with schema
                edge = {
                    "from_label": edge_data.get('from_node', ''),
                    "to_label": edge_data.get('to_node', ''),
                    "confidence": confidence,  # This will be used for aggregate_confidence in the CBN
                    "modifier": modifier
                }
                
                # Only return if both from and to nodes are present
                if edge["from_label"] and edge["to_label"]:
                    logger.info(f"Found edge: {edge['from_label']} → {edge['to_label']} (confidence: {edge['confidence']}, modifier: {edge['modifier']})")
                    return edge
            
            logger.info("No edge found in QA pair")
            return None
        
        except Exception as e:
            logger.error(f"Error extracting edge with LLM: {e}")
            # Fallback to rule-based extraction if LLM fails
            return self._extract_edge_rule_based(qa_pair)
    
    def _extract_nodes_with_llm(self, question, answer, qa_id, session_id=None):
        """
        Extract nodes from QA pair using LLM.
        
        Args:
            question (str): The question text
            answer (str): The answer text
            qa_id (str): The QA pair ID
            session_id (str, optional): Session identifier for persistent tracking
            
        Returns:
            dict: Dictionary of extracted nodes
        """
        # Prepare a prompt for node extraction
        prompt = self._create_node_extraction_prompt(question, answer)
        
        # Call the LLM to extract nodes
        extracted_nodes_json = self._call_llm_for_structured_output(prompt)
        extracted_nodes = {}
        
        if extracted_nodes_json:
            logger.info(f"LLM returned {len(extracted_nodes_json.get('nodes', []))} node candidates")
            
            # For each identified node
            for node_data in extracted_nodes_json.get('nodes', []):
                node_label = node_data.get('label', '')
                
                if not node_label:
                    continue
                
                # Update frequency counter - use session manager if session_id provided
                if session_id:
                    session_manager.increment_node_candidate(session_id, node_label)
                    self.node_candidates = session_manager.get_node_candidates(session_id)
                else:
                    self.node_candidates[node_label] += 1
                
                # Get node confidence and importance
                confidence = node_data.get('confidence', 0.9)
                importance = node_data.get('importance', 0.7)
                frequency = self.node_candidates[node_label]
                
                if frequency >= self.min_node_frequency or confidence > 0.7 or importance > 0.7:
                    # Generate a node ID
                    node_id = f"n_{self._normalize_text(node_label)}_{uuid.uuid4().hex[:6]}"
                    
                    # Determine if this is a stance node
                    is_stance = node_data.get('is_stance', False) or node_data.get('semantic_role', '') == 'behavioral_intention'
                    if is_stance:
                        self.stance_node_created = True
                    
                    # Create evidence entry
                    evidence = [{"qa_id": qa_id, "confidence": confidence}]
                    
                    # Create node with complete schema structure
                    new_node = {
                        "label": node_label,
                        "importance": importance,
                        "confidence": confidence,
                        "aggregate_confidence": confidence,  # Initial aggregate = single confidence
                        "evidence": evidence,
                        "source_qa": [qa_id],  # Kept for backward compatibility
                        "incoming_edges": [],
                        "outgoing_edges": [],
                        "is_stance": is_stance
                    }
                    
                    # Check if this node can be merged with existing nodes
                    merged = False
                    if len(extracted_nodes) > 0:
                        for existing_id, existing_node in list(extracted_nodes.items()):
                            if self._can_merge_nodes(existing_node, new_node):
                                logger.info(f"Merging node '{node_label}' with existing node '{existing_node['label']}'")
                                extracted_nodes[existing_id] = self._merge_nodes(existing_node, new_node)
                                merged = True
                                break
                    
                    if not merged:
                        extracted_nodes[node_id] = new_node
                        logger.info(f"Added node: {node_label} (confidence: {confidence}, importance: {importance}, stance: {is_stance})")
            
            # Log the current state of node candidate queue
            if session_id:
                node_candidates = session_manager.get_node_candidates(session_id)
                logger.info(f"Current node candidates queue for session {session_id}: {dict(node_candidates)}")
            else:
                logger.info(f"Current node candidates queue: {dict(self.node_candidates)}")
        
        return extracted_nodes
    
    def _create_stance_node(self, question, answer, qa_id, session_id=None):
        """
        Create a stance node based on the question context.
        
        Args:
            question (str): The question text
            answer (str): The answer text
            qa_id (str): The QA pair ID
            session_id (str, optional): Session identifier for persistent tracking
            
        Returns:
            dict: A dictionary containing a single stance node
        """
        logger.info("Creating stance node from question context")
        
        # Try to extract topic from question
        topic = self._extract_question_topic(question)
        
        # Create stance node label
        stance_label = f"Support for {topic}"
        node_id = f"n_stance_{self._normalize_text(topic)}_{uuid.uuid4().hex[:6]}"
        
        # Default confidence and importance for stance nodes
        confidence = 1.0
        importance = 1.0
        
        # Create evidence entry
        evidence = [{"qa_id": qa_id, "confidence": confidence}]
        
        # Create the node with complete schema structure
        stance_node = {
            node_id: {
                "label": stance_label,
                "importance": importance,
                "confidence": confidence,
                "aggregate_confidence": confidence,
                "evidence": evidence,
                "source_qa": [qa_id],
                "incoming_edges": [],
                "outgoing_edges": [],
                "is_stance": True
            }
        }
        
        # Update node candidates if session_id is provided
        if session_id:
            session_manager.increment_node_candidate(session_id, stance_label)
        else:
            self.node_candidates[stance_label] += 1
        
        return stance_node
    
    def _extract_question_topic(self, question):
        """
        Extract the main topic from a question.
        
        Args:
            question (str): The question text
            
        Returns:
            str: The main topic
        """
        # Try to use LLM to extract topic
        prompt = f"""
        Extract the main topic or subject from this question:
        
        Question: {question}
        
        Return only the topic name as a short phrase (2-5 words).
        """
        
        try:
            response = dashscope.Generation.call(
                api_key=self.api_key,
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'Extract the main topic from this question. Be brief and specific.'},
                    {'role': 'user', 'content': prompt}
                ],
                result_format='message',
                temperature=0.1
            )
            
            if response.status_code == 200:
                topic = response.output.choices[0].message.content.strip()
                if topic:
                    logger.info(f"Extracted topic: {topic}")
                    return topic
        except Exception as e:
            logger.error(f"Error extracting topic with LLM: {e}")
        
        # Fallback: Use a simple rule-based approach
        words = question.strip("?!.,;").split()
        if len(words) > 3:
            topic = " ".join(words[3:min(8, len(words))])
        else:
            topic = "this topic"
        
        logger.info(f"Generated fallback topic: {topic}")
        return topic
    
    def _call_llm_for_structured_output(self, prompt):
        """
        Call the LLM API with the given prompt and return structured output.
        
        Args:
            prompt (str): The prompt to send to the LLM
            
        Returns:
            dict: Parsed JSON response from the LLM, or empty dict if parsing fails
        """
        logger.info("Calling LLM for structured output")
        
        # Print shortened prompt for debugging
        shortened_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
        logger.debug(f"Prompt (shortened): {shortened_prompt}")
        
        # Print full prompt for detailed debugging
        DEBUG_LLM_IO = os.getenv('DEBUG_LLM_IO', 'false').lower() == 'true'
        if DEBUG_LLM_IO:
            logger.info(f"FULL PROMPT TO LLM: {prompt}")
        
        # Setup API configuration with authentication
        dashscope.api_key = self.api_key
        
        # Retry mechanism for API calls
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                # Call the LLM using DashScope API
                logger.info(f"Calling {self.model} (attempt {attempt+1}/{max_retries})")
                
                response = dashscope.Generation.call(
                    model=self.model,
                    prompt=prompt,
                    temperature=self.temperature,  # Use instance temperature parameter for consistent outputs
                    max_tokens=2000,
                    result_format='json'
                )
                
                # Log the API response for debugging
                if DEBUG_LLM_IO:
                    logger.info(f"LLM API RESPONSE: {json.dumps(response, indent=2)}")
                
                # Check if the call was successful
                if response.status_code == 200:
                    # Extract and parse the text response
                    output = response.output.text
                    
                    # Log the raw output for debugging
                    if DEBUG_LLM_IO:
                        logger.info(f"LLM RAW OUTPUT: {output}")
                    
                    # Clean and parse the JSON string
                    try:
                        json_data = json.loads(self._clean_json_string(output))
                        logger.info("Successfully parsed LLM response")
                        return json_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse LLM response as JSON: {e}")
                        logger.error(f"Raw response: {output}")
                        
                        # Try to extract JSON using regex as fallback
                        try:
                            json_match = re.search(r'(\{.*\})', output, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                                json_data = json.loads(json_str)
                                logger.info("Successfully parsed LLM response with regex fallback")
                                return json_data
                        except Exception:
                            pass
                        
                        # Return empty dict on failure
                        if attempt == max_retries - 1:
                            return {}
                else:
                    # Log API errors
                    error_message = f"LLM API error: {response.status_code}, {response.message}"
                    logger.error(error_message)
                    
                    # Return empty dict on final attempt
                    if attempt == max_retries - 1:
                        return {}
            
            except Exception as e:
                logger.error(f"Exception during LLM API call: {e}")
                
                # Return empty dict on final attempt
                if attempt == max_retries - 1:
                    return {}
            
            # Wait before retrying
            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        
        # If all retries failed
        return {}
    
    def _clean_json_string(self, json_str):
        """
        Clean a string to ensure it contains only valid JSON.
        """
        # Find the first { and the last }
        start = json_str.find('{')
        end = json_str.rfind('}') + 1
        
        if start >= 0 and end > start:
            return json_str[start:end]
        
        return json_str
    
    def _create_node_extraction_prompt(self, question, answer):
        """
        Create a prompt for extracting nodes from a QA pair.
        """
        return f"""
Extract key concepts or entities that could serve as nodes in a causal graph from the following question-answer pair:

Question: {question}

Answer: {answer}

Identify potential nodes with the following criteria:
1. Focus on meaningful concepts that could have causal relationships
2. Assign a confidence score (0.0-1.0) to each node, indicating certainty about its existence
3. Assign an importance score (0.0-1.0) to each node, indicating how central it is to the answer

Format your response as a JSON object with the following structure:
{{
  "nodes": [
    {{
      "label": "node_label",
      "confidence": 0.8,
      "importance": 0.7,
      "is_stance": true|false
    }}
  ]
}}
"""
    
    def _create_edge_extraction_prompt(self, question, answer):
        """
        Create a prompt for extracting edges from a QA pair.
        """
        return f"""
Extract causal relationships between concepts from the following question-answer pair:

Question: {question}

Answer: {answer}

Identify potential causal relationships with the following criteria:
1. Identify cause-effect relationships between concepts
2. Determine if the relationship is positive (increases/supports) or negative (decreases/prevents)
3. Assign a confidence score (0.0-1.0) to indicate certainty about this relationship's existence
4. Assign a strength score (0.0-1.0) to indicate how strong the causal effect is

Format your response as a JSON object with the following structure:
{{
  "edges": [
    {{
      "from_node": "cause_concept",
      "to_node": "effect_concept",
      "direction": "positive|negative",
      "confidence": 0.7,
      "strength": 0.8
    }}
  ]
}}
"""
    
    # Fallback rule-based methods
    
    def _extract_edge_rule_based(self, qa_pair):
        """
        Extract edges using rule-based approach (fallback method).
        
        Args:
            qa_pair (dict): A question-answer pair
            
        Returns:
            dict or None: Extracted edge or None if no edge found
        """
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        qa_id = qa_pair.get('id')
        
        logger.info("Using rule-based edge extraction fallback")
        
        causal_patterns = [
            r'([A-Za-z\s]+)\s+(?:causes|cause|caused|leads to|results in|affects|influences)\s+([A-Za-z\s]+)',
            r'([A-Za-z\s]+)\s+(?:depends on|is affected by|is influenced by)\s+([A-Za-z\s]+)',
            r'(?:If|When)\s+([A-Za-z\s]+),\s+(?:then)?\s+([A-Za-z\s]+)'
        ]
        
        for pattern in causal_patterns:
            matches = re.findall(pattern, answer)
            if matches:
                for match in matches:
                    from_node = match[0].strip()
                    to_node = match[1].strip()
                    
                    # Default values
                    confidence = 0.7
                    strength = 0.7
                    
                    # Determine direction/modifier
                    if "not" in answer or "n't" in answer:
                        modifier = -strength
                    else:
                        modifier = strength
                    
                    # Create edge with schema-aligned structure
                    edge = {
                        "from_label": from_node,
                        "to_label": to_node,
                        "confidence": confidence,
                        "modifier": modifier
                    }
                    
                    logger.info(f"Rule-based extraction found edge: {from_node} → {to_node} (confidence: {confidence}, modifier: {modifier})")
                    return edge
        
        logger.info("No edge found using rule-based extraction")
        return None
    
    def _normalize_text(self, text):
        """
        Normalize text for use in IDs.
        """
        normalized = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
        normalized = re.sub(r'_+', '_', normalized)
        if len(normalized) > 20:
            normalized = normalized[:20]
        return normalized
    
    def _can_merge_nodes(self, node1, node2):
        """
        Determine if two nodes can be merged based on semantic similarity.
        
        Args:
            node1 (dict): First node
            node2 (dict): Second node
            
        Returns:
            bool: True if nodes can be merged, False otherwise
        """
        # Get node labels
        label1 = node1.get('label', '')
        label2 = node2.get('label', '')
        
        # Skip if either label is empty or they're identical
        if not label1 or not label2:
            return False
        
        if label1 == label2:
            return True
        
        # Create a prompt for determining if nodes can be merged
        prompt = f"""
Determine if these two concepts represent the same underlying idea or entity:

Concept 1: {label1}
Concept 2: {label2}

Consider:
1. Do they refer to the same thing, just phrased differently?
2. Are they synonyms or closely related concepts that should be treated as the same?
3. Would merging them lead to information loss or distortion?

Return ONLY "yes" if they should be merged or "no" if they should remain separate.
"""
        
        try:
            # Call the LLM to determine if nodes can be merged
            response = dashscope.Generation.call(
                api_key=self.api_key,
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'Determine if two concepts are similar enough to be merged. Only answer with yes or no.'},
                    {'role': 'user', 'content': prompt}
                ],
                result_format='message',
                temperature=0.1
            )
            
            if response.status_code == 200:
                answer = response.output.choices[0].message.content.strip().lower()
                can_merge = answer.startswith('yes')
                logger.info(f"Merge check for '{label1}' and '{label2}': {can_merge}")
                return can_merge
            
        except Exception as e:
            logger.error(f"Error checking node similarity with LLM: {e}")
            # Fallback to basic string comparison
            return self._normalize_text(label1)[:10] == self._normalize_text(label2)[:10]
        
        return False
    
    def _merge_nodes(self, node1, node2):
        """
        Merge two nodes, combining their evidence and recalculating confidence and importance.
        
        Args:
            node1 (dict): First node
            node2 (dict): Second node
            
        Returns:
            dict: Merged node
        """
        # Select the label with higher confidence or the first one if equal
        if node2['confidence'] > node1['confidence']:
            merged_label = node2['label']
        else:
            merged_label = node1['label']
        
        # Combine evidence
        merged_evidence = node1.get('evidence', []) + node2.get('evidence', [])
        
        # Combine source QAs without duplicates
        merged_source_qa = list(set(node1.get('source_qa', []) + node2.get('source_qa', [])))
        
        # Calculate new aggregate confidence (weighted average)
        total_confidence = sum([ev.get('confidence', 0) for ev in merged_evidence])
        if len(merged_evidence) > 0:
            aggregate_confidence = total_confidence / len(merged_evidence)
        else:
            aggregate_confidence = max(node1.get('aggregate_confidence', 0), node2.get('aggregate_confidence', 0))
        
        # Take the maximum of the importance scores
        merged_importance = max(node1.get('importance', 0), node2.get('importance', 0))
        
        # Determine if merged node is a stance node (if either was a stance node)
        is_stance = node1.get('is_stance', False) or node2.get('is_stance', False)
        
        # Combine incoming and outgoing edges without duplicates
        merged_incoming = list(set(node1.get('incoming_edges', []) + node2.get('incoming_edges', [])))
        merged_outgoing = list(set(node1.get('outgoing_edges', []) + node2.get('outgoing_edges', [])))
        
        # Create the merged node
        merged_node = {
            "label": merged_label,
            "importance": merged_importance,
            "confidence": max(node1.get('confidence', 0), node2.get('confidence', 0)),
            "aggregate_confidence": aggregate_confidence,
            "evidence": merged_evidence,
            "source_qa": merged_source_qa,
            "incoming_edges": merged_incoming,
            "outgoing_edges": merged_outgoing,
            "is_stance": is_stance
        }
        
        return merged_node 