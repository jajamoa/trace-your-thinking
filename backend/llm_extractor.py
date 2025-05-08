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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QwenLLMExtractor:
    """
    Simplified extractor that focuses on nodes with a stance node as starting point.
    Also provides edge and function parameter extraction capabilities.
    """
    
    def __init__(self, api_key=None, model="qwen-plus", temperature=0.1):
        """
        Initialize the LLM extractor with DashScope API configuration.
        
        Args:
            api_key (str, optional): DashScope API key. Defaults to environment variable.
            model (str, optional): Model name to use. Defaults to "qwen-plus".
            temperature (float, optional): Temperature parameter for LLM output. Lower values (0.01-0.1) produce more deterministic responses. Defaults to 0.1.
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
        self.node_candidates = Counter()
        # Track stance node
        self.stance_node_created = False
        # Minimum frequency to promote a node candidate
        self.min_node_frequency = 2
    
    def extract_nodes(self, qa_pair, ensure_stance_node=True):
        """
        Extract potential nodes from a QA pair using LLM.
        Always ensures a stance node is created if none exists.
        
        Args:
            qa_pair (dict): A question-answer pair
            ensure_stance_node (bool): Whether to ensure a stance node is created
            
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
        
        try:
            # Extract nodes using LLM
            extracted_nodes = self._extract_nodes_with_llm(question, answer, qa_id)
            
            # If no nodes were extracted or we need to ensure a stance node
            if (not extracted_nodes or ensure_stance_node) and not self.stance_node_created:
                stance_node = self._create_stance_node(question, answer, qa_id)
                if stance_node:
                    stance_node_id = list(stance_node.keys())[0]
                    extracted_nodes.update(stance_node)
                    self.stance_node_created = True
                    logger.info(f"Created stance node: {extracted_nodes[stance_node_id]['label']}")
            
            logger.info(f"Extracted {len(extracted_nodes)} nodes")
            return extracted_nodes
            
        except Exception as e:
            logger.error(f"Error extracting nodes with LLM: {e}")
            # Fallback to creating a stance node if all else fails
            if ensure_stance_node and not self.stance_node_created:
                stance_node = self._create_stance_node(question, answer, qa_id)
                if stance_node:
                    stance_node_id = list(stance_node.keys())[0]
                    logger.info(f"Created fallback stance node: {stance_node[stance_node_id]['label']}")
                    self.stance_node_created = True
                    return stance_node
            return {}
    
    def extract_edge(self, qa_pair):
        """
        Extract potential causal relationships (edges) from a QA pair using LLM.
        
        Args:
            qa_pair (dict): A question-answer pair
            
        Returns:
            dict or None: Extracted edge information or None if no edge found
        """
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        qa_id = qa_pair.get('id')
        
        logger.info(f"Extracting edge from QA pair {qa_id}")
        
        # Prepare a prompt for edge extraction
        prompt = self._create_edge_extraction_prompt(question, answer)
        
        try:
            # Call the LLM to extract edges
            extracted_edge_json = self._call_llm_for_structured_output(prompt)
            
            if extracted_edge_json and 'edges' in extracted_edge_json and extracted_edge_json['edges']:
                edge_data = extracted_edge_json['edges'][0]  # Take the first edge
                
                # Create edge with metadata
                edge = {
                    "from_label": edge_data.get('from_node', ''),
                    "to_label": edge_data.get('to_node', ''),
                    "direction": edge_data.get('direction', 'positive'),
                    "confidence": edge_data.get('confidence', 0.7),
                    "support_qas": [qa_id],
                    "function_type": edge_data.get('function_type', 'sigmoid'),
                    "status": "proposed"
                }
                
                # Only return if both from and to nodes are present
                if edge["from_label"] and edge["to_label"]:
                    logger.info(f"Found edge: {edge['from_label']} → {edge['to_label']} (direction: {edge['direction']})")
                    return edge
            
            logger.info("No edge found in QA pair")
            return None
        
        except Exception as e:
            logger.error(f"Error extracting edge with LLM: {e}")
            # Fallback to rule-based extraction if LLM fails
            return self._extract_edge_rule_based(qa_pair)
    
    def extract_function_params(self, qa_pair):
        """
        Extract parameters for the causal function from a QA pair using LLM.
        
        Args:
            qa_pair (dict): A question-answer pair
            
        Returns:
            dict or None: Function parameters or None if not extractable
        """
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        
        logger.info("Extracting function parameters")
        
        # Prepare a prompt for function parameter extraction
        prompt = self._create_function_params_prompt(question, answer)
        
        try:
            # Call the LLM to extract function parameters
            function_params_json = self._call_llm_for_structured_output(prompt)
            
            if function_params_json and 'function_params' in function_params_json:
                params = function_params_json['function_params']
                
                function_params = {
                    "function_type": params.get('function_type', 'sigmoid'),
                    "parameters": {
                        "weights": params.get('weights', [0.5]),
                        "bias": params.get('bias', 0.0)
                    },
                    "noise_std": params.get('noise_std', 0.1)
                }
                
                if 'confidence' in params:
                    function_params["confidence"] = params.get('confidence')
                
                logger.info(f"Extracted function parameters: type={function_params['function_type']}")
                return function_params
            
            logger.info("No function parameters found")
            return None
        
        except Exception as e:
            logger.error(f"Error extracting function parameters with LLM: {e}")
            # Fallback to rule-based extraction if LLM fails
            return self._extract_function_params_rule_based(qa_pair)
    
    def extract_parsed_belief(self, qa_pair, from_node_id, to_node_id):
        """
        Extract a structured parsed belief from a QA pair using LLM.
        
        Args:
            qa_pair (dict): A question-answer pair
            from_node_id (str): Source node ID
            to_node_id (str): Target node ID
            
        Returns:
            dict: Structured parsed belief, empty dict if extraction fails
        """
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        
        logger.info("Extracting parsed belief")
        
        # Prepare a prompt for belief extraction
        prompt = self._create_belief_extraction_prompt(question, answer, from_node_id, to_node_id)
        
        try:
            # Call the LLM to extract beliefs
            belief_json = self._call_llm_for_structured_output(prompt)
            
            if belief_json and 'parsed_belief' in belief_json:
                belief_data = belief_json['parsed_belief']
                
                parsed_belief = {
                    "belief_structure": {
                        "from": from_node_id,
                        "to": to_node_id,
                        "direction": belief_data.get('direction', 'positive')
                    },
                    "belief_strength": {
                        "estimated_probability": belief_data.get('strength', 0.7),
                        "confidence_rating": belief_data.get('confidence', 0.6)
                    },
                    "counterfactual": belief_data.get('counterfactual', f"If [from_node] were different, [to_node] would change.")
                }
                
                logger.info(f"Extracted belief: direction={parsed_belief['belief_structure']['direction']}, strength={parsed_belief['belief_strength']['estimated_probability']}")
                return parsed_belief
            
            logger.info("No parsed belief found, returning minimal valid structure")
            # Return minimal valid structure to comply with schema
            return {
                "belief_structure": {
                    "from": from_node_id,
                    "to": to_node_id,
                    "direction": "positive"
                },
                "belief_strength": {
                    "estimated_probability": 0.5,
                    "confidence_rating": 0.5
                },
                "counterfactual": ""
            }
        
        except Exception as e:
            logger.error(f"Error extracting beliefs with LLM: {e}")
            # Return minimal valid structure to comply with schema
            return {
                "belief_structure": {
                    "from": from_node_id,
                    "to": to_node_id,
                    "direction": "positive"
                },
                "belief_strength": {
                    "estimated_probability": 0.5,
                    "confidence_rating": 0.5
                },
                "counterfactual": ""
            }
    
    def _extract_nodes_with_llm(self, question, answer, qa_id):
        """
        Extract nodes from QA pair using LLM.
        
        Args:
            question (str): The question text
            answer (str): The answer text
            qa_id (str): The QA pair ID
            
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
                
                # Update frequency counter
                self.node_candidates[node_label] += 1
                
                # Only add nodes that have appeared multiple times or are important
                frequency = self.node_candidates[node_label]
                importance = node_data.get('importance', 0)
                
                if frequency >= self.min_node_frequency or importance > 0.7:
                    # Generate a node ID
                    node_id = f"n_{self._normalize_text(node_label)}_{uuid.uuid4().hex[:6]}"
                    
                    # Get semantic role
                    semantic_role = node_data.get('semantic_role', 'external_state')
                    
                    # Handle stance nodes
                    is_stance = node_data.get('is_stance', False) or semantic_role == 'behavioral_intention'
                    if is_stance:
                        self.stance_node_created = True
                    
                    # Create node with metadata
                    extracted_nodes[node_id] = {
                        "id": node_id,
                        "label": node_label,
                        "type": "binary",  # Default to binary
                        "values": [True, False],
                        "semantic_role": semantic_role,
                        "is_stance": is_stance,
                        "appearance": {
                            "qa_ids": [qa_id],
                            "frequency": frequency
                        },
                        "incoming_edges": [],
                        "outgoing_edges": [],
                        "status": "anchor" if is_stance else "proposed"  # Stance nodes start as anchors
                    }
                    
                    logger.info(f"Added node: {node_label} (role: {semantic_role}, stance: {is_stance})")
        
        return extracted_nodes
    
    def _create_stance_node(self, question, answer, qa_id):
        """
        Create a stance node based on the question context.
        
        Args:
            question (str): The question text
            answer (str): The answer text
            qa_id (str): The QA pair ID
            
        Returns:
            dict: A dictionary containing a single stance node
        """
        logger.info("Creating stance node from question context")
        
        # Try to extract topic from question
        topic = self._extract_question_topic(question)
        
        # Create stance node label
        stance_label = f"Stance on {topic}"
        node_id = f"n_stance_{self._normalize_text(topic)}_{uuid.uuid4().hex[:6]}"
        
        # Create the node
        stance_node = {
            node_id: {
                "id": node_id,
                "label": stance_label,
                "type": "binary",
                "values": [True, False],
                "semantic_role": "behavioral_intention",
                "is_stance": True,
                "appearance": {
                    "qa_ids": [qa_id],
                    "frequency": 2  # Give it enough frequency to be considered important
                },
                "incoming_edges": [],
                "outgoing_edges": [],
                "status": "anchor"  # Stance nodes are always anchors
            }
        }
        
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
Extract key concepts or entities that could serve as nodes in a Structural Causal Model (SCM) from the following question-answer pair:

Question: {question}

Answer: {answer}

Identify potential nodes with the following criteria:
1. Focus on meaningful concepts that could have causal relationships
2. Classify each node into one of these semantic roles:
   - external_state: World states observed or believed (e.g., noise level, housing prices)
   - internal_affect: Emotions, preferences, perceived costs (e.g., stress, satisfaction)
   - behavioral_intention: Action tendencies or decision intents (e.g., support for policy)
3. Assign an importance score (0.0-1.0) to each node
4. Mark any nodes that represent the person's stance or overall opinion as is_stance=true

Format your response as a JSON object with the following structure:
{{
  "nodes": [
    {{
      "label": "node_label",
      "semantic_role": "external_state|internal_affect|behavioral_intention",
      "importance": 0.8,
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
2. Determine the direction (positive/negative) of the relationship
3. Assign a confidence score (0.0-1.0) to each relationship
4. Suggest a function type (sigmoid, threshold, linear) that best describes the relationship

Format your response as a JSON object with the following structure:
{{
  "edges": [
    {{
      "from_node": "cause_concept",
      "to_node": "effect_concept",
      "direction": "positive|negative",
      "confidence": 0.7,
      "function_type": "sigmoid|threshold|linear"
    }}
  ]
}}
"""
    
    def _create_function_params_prompt(self, question, answer):
        """
        Create a prompt for extracting function parameters from a QA pair.
        """
        return f"""
Extract parameters for a causal function from the following question-answer pair:

Question: {question}

Answer: {answer}

Analyze the text to determine:
1. The most appropriate function type (sigmoid, threshold, linear)
2. The strength of the relationship (numeric weight value)
3. Any bias or threshold in the relationship
4. The confidence level in this function

Format your response as a JSON object with the following structure:
{{
  "function_params": {{
    "function_type": "sigmoid|threshold|linear",
    "weights": [0.7],
    "bias": 0.2,
    "noise_std": 0.1,
    "confidence": 0.8
  }}
}}
"""
    
    def _create_belief_extraction_prompt(self, question, answer, from_node_id, to_node_id):
        """
        Create a prompt for extracting beliefs from a QA pair.
        """
        return f"""
Extract the belief about a causal relationship from the following question-answer pair:

Question: {question}

Answer: {answer}

For a relationship between two nodes, extract:
1. The direction of the relationship (positive/negative)
2. The strength of the belief (0.0-1.0)
3. The confidence in this belief (0.0-1.0)
4. A counterfactual statement about this relationship

Format your response as a JSON object with the following structure:
{{
  "parsed_belief": {{
    "direction": "positive|negative",
    "strength": 0.7,
    "confidence": 0.6,
    "counterfactual": "If [cause] were different, [effect] would change."
  }}
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
                    
                    direction = "positive"
                    if "not" in answer or "n't" in answer:
                        direction = "negative"
                    
                    edge = {
                        "from_label": from_node,
                        "to_label": to_node,
                        "direction": direction,
                        "confidence": 0.7,
                        "support_qas": [qa_id],
                        "function_type": "sigmoid",
                        "status": "proposed"
                    }
                    
                    logger.info(f"Rule-based extraction found edge: {from_node} → {to_node}")
                    return edge
        
        logger.info("No edge found using rule-based extraction")
        return None
    
    def _extract_function_params_rule_based(self, qa_pair):
        """
        Extract function parameters using rule-based approach (fallback method).
        
        Args:
            qa_pair (dict): A question-answer pair
            
        Returns:
            dict: Function parameters
        """
        answer = qa_pair.get('answer', '')
        
        logger.info("Using rule-based function parameter extraction fallback")
        
        strength_indicators = {
            "very strong": 0.9,
            "strong": 0.8,
            "moderate": 0.5,
            "weak": 0.3,
            "very weak": 0.2
        }
        
        function_params = {
            "function_type": "sigmoid",
            "parameters": {
                "weights": [0.5],
                "bias": 0.0
            },
            "noise_std": 0.1
        }
        
        if "threshold" in answer.lower() or "only when" in answer.lower():
            function_params["function_type"] = "threshold"
        elif "linear" in answer.lower() or "proportional" in answer.lower():
            function_params["function_type"] = "linear"
        
        for indicator, value in strength_indicators.items():
            if indicator in answer.lower():
                function_params["parameters"]["weights"] = [value]
                break
        
        confidence_match = re.search(r'(?:confidence|certain|sure).*?(\d+)%', answer.lower())
        if confidence_match:
            confidence = float(confidence_match.group(1)) / 100.0
            function_params["confidence"] = confidence
        
        logger.info(f"Rule-based extraction determined function type: {function_params['function_type']}")
        return function_params
    
    def _extract_parsed_belief_rule_based(self, qa_pair, from_node_id, to_node_id):
        """
        Extract parsed belief using rule-based approach (fallback method).
        
        Args:
            qa_pair (dict): A question-answer pair
            from_node_id (str): Source node ID
            to_node_id (str): Target node ID
            
        Returns:
            dict: Parsed belief
        """
        answer = qa_pair.get('answer', '')
        
        logger.info("Using rule-based belief extraction fallback")
        
        belief_strength = 0.7
        confidence = 0.6
        
        if "very strong" in answer.lower():
            belief_strength = 0.9
            confidence = 0.8
        elif "strong" in answer.lower():
            belief_strength = 0.8
            confidence = 0.7
        elif "moderate" in answer.lower():
            belief_strength = 0.5
            confidence = 0.6
        elif "weak" in answer.lower():
            belief_strength = 0.3
            confidence = 0.5
        elif "very weak" in answer.lower():
            belief_strength = 0.2
            confidence = 0.4
        
        direction = "positive"
        if "not" in answer.lower() or "n't" in answer.lower() or "negatively" in answer.lower():
            direction = "negative"
        
        parsed_belief = {
            "belief_structure": {
                "from": from_node_id,
                "to": to_node_id,
                "direction": direction
            },
            "belief_strength": {
                "estimated_probability": belief_strength,
                "confidence_rating": confidence
            },
            "counterfactual": f"If [from_node] were different, [to_node] would change."
        }
        
        logger.info(f"Rule-based extraction determined belief direction: {direction}, strength: {belief_strength}")
        return parsed_belief
    
    def _normalize_text(self, text):
        """
        Normalize text for use in IDs.
        """
        normalized = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
        normalized = re.sub(r'_+', '_', normalized)
        if len(normalized) > 20:
            normalized = normalized[:20]
        return normalized 