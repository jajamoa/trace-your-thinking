"""
LLM-based Node Extractor
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

# Import the LLMLogger
from llm_logger import llm_logger, LLM_CALL_TYPES

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QwenLLMExtractor:
    """
    Extractor that uses LLM to identify nodes and causal relationships from text.
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
        # Minimum frequency to promote a node candidate
        self.min_node_frequency = 2
    
    def extract_nodes(self, qa_pair, ensure_stance_node=True):
        """
        Extract potential nodes from a QA pair using LLM.
        
        Args:
            qa_pair (dict): A question-answer pair
            ensure_stance_node (bool): Parameter kept for backward compatibility, but ignored
            
        Returns:
            dict: Dictionary of extracted nodes with metadata (without specific IDs)
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
        
        # Skip if either question or answer is empty
        if not question or not answer:
            return {}
        
        prompt = self.get_node_extraction_prompt(question, answer)
        llm_logger.log_separator("NODE EXTRACTION")
        llm_logger.log_prompt(LLM_CALL_TYPES["NODE_EXTRACTION"], prompt)
        
        extracted_output = self._call_llm_for_structured_output(
            prompt, 
            LLM_CALL_TYPES["NODE_EXTRACTION"]
        )
        
        # No valid extraction
        if not extracted_output:
            return {}
            
        # Process and normalize output
        nodes = {}
        
        # Extract nodes from the response
        try:
            # If the extracted_output is already a list or dict, no need to parse it
            if isinstance(extracted_output, (list, dict)):
                extracted_data = extracted_output
            else:
                # Otherwise, clean and parse it as a string
                clean_json = self._clean_json_string(extracted_output)
                extracted_data = json.loads(clean_json)
            
            # Check if we got a valid structure
            if isinstance(extracted_data, dict) and 'nodes' in extracted_data:
                # Handle old format: {"nodes": [...]}
                node_list = extracted_data['nodes']
            elif isinstance(extracted_data, list):
                # Handle new format: direct array of nodes
                node_list = extracted_data
            else:
                logger.warning(f"Unexpected response format: {type(extracted_data)}")
                return {}
                
            # Process each node
            for i, node_data in enumerate(node_list):
                if not isinstance(node_data, dict):
                    continue
                    
                # Extract basic node properties
                node_label = node_data.get('label', '').strip()
                if not node_label:
                    continue
                    
                # Skip if label is too short
                if len(node_label) < 2:
                    continue
                    
                # Normalize confidence to 0.0-1.0 range
                confidence = float(node_data.get('aggregate_confidence', node_data.get('confidence', 0.5)))
                confidence = max(0.0, min(1.0, confidence))
                
                # Normalize importance to 0.0-1.0 range
                importance = float(node_data.get('importance', 0.5))
                importance = max(0.0, min(1.0, importance))
                
                # Create temporary key for this batch
                temp_key = f"temp_{i}"
                
                # Track node frequency
                self.node_candidates[node_label.lower()] += 1
                
                # Create evidence entry for this QA
                evidence = [{
                    "qa_id": qa_id,
                    "confidence": confidence,
                    "importance": importance
                }]
                
                # Create node with metadata but without permanent ID
                nodes[temp_key] = {
                    'label': node_label,
                    'aggregate_confidence': confidence,
                    'importance': importance,
                    'evidence': evidence,
                    'frequency': 1
                }
            
            if nodes:
                logger.info(f"Extracted {len(nodes)} nodes from QA pair")
                for key, node in nodes.items():
                    logger.info(f"- {node['label']} (aggregate_confidence: {node['aggregate_confidence']:.2f}, importance: {node['importance']:.2f})")
            
            return nodes
                
        except Exception as e:
            logger.error(f"Error processing node extraction: {str(e)}")
            logger.error(f"Raw output: {extracted_output}")
            return {}
    
    def extract_edge(self, qa_pair, extracted_nodes=None):
        """
        Extract potential causal relationships (edges) from a QA pair using LLM.
        This is a comprehensive extraction that collects all necessary information in one call,
        including direction, strength, aggregate_confidence, and explanation.
        
        Args:
            qa_pair (dict): A question-answer pair
            extracted_nodes (dict, optional): Previously extracted nodes to restrict edge creation
            
        Returns:
            dict or None: Extracted edge information or None if no edge found
        """
        question = qa_pair.get('question', '')
        answer = qa_pair.get('answer', '')
        qa_id = qa_pair.get('id')
        
        logger.info(f"Extracting comprehensive edge information from QA pair {qa_id}")
        
        # Add separators before LLM calls in the important extraction methods
        llm_logger.log_separator("Edge Extraction Request")
        
        # Prepare a prompt for combined edge and modifier extraction
        prompt = self._create_combined_edge_extraction_prompt(question, answer, extracted_nodes)
        
        try:
            # Call the LLM to extract edges with modifiers
            extracted_edge_json = self._call_llm_for_structured_output(prompt, LLM_CALL_TYPES["EDGE_EXTRACTION"])
            
            if extracted_edge_json and 'edges' in extracted_edge_json and extracted_edge_json['edges']:
                edge_data = extracted_edge_json['edges'][0]  # Take the first edge
                
                # Create edge with comprehensive metadata
                edge = {
                    "from_label": edge_data.get('from_node', ''),
                    "to_label": edge_data.get('to_node', ''),
                    "direction": edge_data.get('direction', 'positive'),
                    "aggregate_confidence": edge_data.get('aggregate_confidence', edge_data.get('confidence', 0.7)),
                    "support_qas": [qa_id],
                    "function_type": edge_data.get('function_type', 'sigmoid'),
                    "strength": edge_data.get('strength', 0.7),
                    "explanation": edge_data.get('explanation', '')
                }
                
                # Only return if both from and to nodes are present
                if edge["from_label"] and edge["to_label"]:
                    logger.info(f"Found edge: {edge['from_label']} → {edge['to_label']} (direction: {edge['direction']}, strength: {edge['strength']})")
                    if edge['explanation']:
                        logger.info(f"Explanation: {edge['explanation']}")
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
        This is kept for backward compatibility but can be bypassed since parameters
        are now extracted in the edge extraction step.
        
        Args:
            qa_pair (dict): A question-answer pair
            
        Returns:
            dict or None: Function parameters or None if not extractable
        """
        logger.info("Function parameters already extracted in edge extraction step")
        return {"aggregate_confidence": 0.7}  # Return default values
    
    def get_node_extraction_prompt(self, question, answer):
        """
        Create a prompt for extracting nodes from a question-answer pair.
        
        Args:
            question (str): The question text
            answer (str): The answer text
            
        Returns:
            str: A prompt for node extraction
        """
        return f"""
You are analyzing a conversation about beliefs. Extract important concepts/nodes from this Q&A pair.

INSTRUCTION:
Identify key concepts or beliefs from the user's answer. These could be:
1. Factors the user believes are important
2. Concepts that the user has strong opinions about
3. Entities or ideas that influence the user's thinking

For each concept, rate:
- Aggregate Confidence (0.0-1.0): How confident the user seems about this concept
- Importance (0.0-1.0): How important this concept appears to be in their belief system

FORMAT:
Return ONLY a raw JSON array of objects with 'label', 'aggregate_confidence', and 'importance' fields.
Do NOT use markdown formatting or code blocks - return ONLY the JSON array directly.

Example of correct response format:
[
  {{
    "label": "Concept name",
    "aggregate_confidence": 0.8,
    "importance": 0.9
  }}
]

QUESTION:
{question}

ANSWER:
{answer}

EXTRACTED CONCEPTS (JSON ONLY):
"""
    
    def _create_combined_edge_extraction_prompt(self, question, answer, extracted_nodes=None):
        """
        Create a prompt for extracting both edges and their modifiers from a QA pair.
        This is a comprehensive extraction that collects all necessary information about
        causal relationships, including direction, strength, aggregate_confidence, and explanation.
        
        Args:
            question (str): The question text
            answer (str): The answer text
            extracted_nodes (dict, optional): Previously extracted nodes to restrict edge creation
        """
        # Add node list to prompt if available
        node_list_section = ""
        if extracted_nodes and len(extracted_nodes) > 0:
            nodes_list = [node.get('label', '') for key, node in extracted_nodes.items()]
            nodes_text = ", ".join([f'"{node}"' for node in nodes_list if node])
            node_list_section = f"""
IMPORTANT: You MUST ONLY create edges between the following concepts that were identified in this answer:
[{nodes_text}]

DO NOT introduce new concepts that are not in this list. If you cannot find a valid causal relationship between these concepts, return an empty edges array.
"""
        
        return f"""
Extract comprehensive causal relationship information from the following question-answer pair:

Question: {question}

Answer: {answer}
{node_list_section}
Identify potential causal relationships with the following criteria:
1. Identify cause-effect relationships between concepts
2. Determine if the relationship is positive (cause increases effect) or negative (cause decreases effect)
3. Assess the strength of the relationship on a scale from 0.0 to 1.0
   - 0.0 = no effect
   - 0.5 = moderate effect
   - 1.0 = very strong effect
4. Assign an aggregate_confidence score (0.0-1.0) to how certain you are about this relationship
5. Provide a brief explanation of why this causal relationship exists

Format your response as a JSON object with the following structure.
Return ONLY raw JSON - do NOT use markdown formatting or code blocks:

{{
  "edges": [
    {{
      "from_node": "cause_concept",
      "to_node": "effect_concept",
      "direction": "positive|negative",
      "strength": 0.8,
      "aggregate_confidence": 0.7,
      "explanation": "Brief explanation of why this causal relationship exists"
    }}
  ]
}}

A positive direction means the cause increases the effect.
A negative direction means the cause decreases the effect.
Strength indicates how powerful the influence is (0.0=weak, 1.0=strong).
Aggregate_confidence indicates how certain you are about the existence of this relationship.
Explanation should briefly explain the reasoning behind this causal relationship.

RESPONSE (JSON ONLY):
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
                        "aggregate_confidence": 0.7,
                        "support_qas": [qa_id]
                    }
                    
                    logger.info(f"Rule-based extraction found edge: {from_node} → {to_node}")
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
    
    def _call_llm_for_structured_output(self, prompt, call_type):
        """
        Call the LLM API with the given prompt and return structured output.
        
        Args:
            prompt (str): The prompt to send to the LLM
            call_type (str): The type of LLM call for logging
            
        Returns:
            dict: Parsed JSON response from the LLM, or empty dict if parsing fails
        """
        logger.info(f"Calling LLM for structured output - type: {call_type}")
        
        # Log the prompt if enabled for this call type
        llm_logger.log_prompt(call_type, prompt)
        
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
                
                # Log the API response if enabled for this call type
                llm_logger.log_response(call_type, response)
                
                # Check if the call was successful
                if response.status_code == 200:
                    # Extract and parse the text response
                    output = response.output.text
                    
                    # Clean and parse the JSON string
                    try:
                        json_data = json.loads(self._clean_json_string(output))
                        logger.info("Successfully parsed LLM response")
                        
                        # Log the parsed JSON if enabled for this call type
                        llm_logger.log_response(call_type, json_data)
                        
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
                                
                                # Log the parsed JSON if enabled for this call type
                                llm_logger.log_response(call_type, json_data)
                                
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
        Handles both object ({...}) and array ([...]) formats,
        and removes Markdown code block syntax if present.
        """
        # If input is already a dict or list, return it as is
        if isinstance(json_str, (dict, list)):
            return json_str
            
        # Ensure we have a string to work with
        if not isinstance(json_str, str):
            return json_str
            
        # Remove markdown code block syntax if present
        if "```json" in json_str or "```" in json_str:
            # Find content between code block markers
            import re
            code_block_match = re.search(r'```(?:json)?\n([\s\S]*?)\n```', json_str)
            if code_block_match:
                json_str = code_block_match.group(1)
        
        # Try to find JSON array
        if '[' in json_str and ']' in json_str:
            array_start = json_str.find('[')
            array_end = json_str.rfind(']') + 1
            if array_start >= 0 and array_end > array_start:
                return json_str[array_start:array_end]
        
        # Try to find JSON object
        if '{' in json_str and '}' in json_str:
            obj_start = json_str.find('{')
            obj_end = json_str.rfind('}') + 1
            if obj_start >= 0 and obj_end > obj_start:
                return json_str[obj_start:obj_end]
        
        # If we couldn't extract a clean JSON structure, return the original
        return json_str.strip()
    
    def find_similar_nodes_in_graph(self, nodes):
        """
        Find semantically similar nodes in the entire graph at once using LLM.
        
        Args:
            nodes (dict): Dictionary of node_id -> node mapping from the graph
            
        Returns:
            list: List of tuples (node_id1, node_id2, confidence) for similar nodes
        """
        if not nodes or len(nodes) < 2:
            return []
        
        logger.info(f"Finding similar nodes in graph with {len(nodes)} nodes")
        
        # Extract relevant node information for the LLM
        node_data = []
        for node_id, node in nodes.items():
            node_data.append({
                "id": node_id,
                "label": node.get("label", ""),
                "frequency": node.get("frequency", 1),
                "importance": node.get("importance", 0.5),
                "confidence": node.get("aggregate_confidence", 0.5),
                "status": node.get("status", "candidate"),  # Include node status
                "is_stance": node.get("is_stance", False)   # Include stance flag
            })
        
        # Create a prompt to find similar nodes in the graph
        prompt = f"""
You are analyzing a graph of concepts extracted from a user's beliefs.
Find pairs of nodes that are semantically similar.

INSTRUCTIONS:
Analyze the following list of concept nodes and identify pairs that represent the same or very similar ideas.
These could be:
1. Synonyms or alternative phrasings
2. Specific vs. general versions of the same concept
3. Different aspects of the same underlying idea

NODE LIST:
{json.dumps(node_data, indent=2)}

When determining similarity, consider:
- Exact matching words indicate strong similarity
- Synonyms or related terms indicate potential similarity
- Semantic meaning is more important than exact wording

IMPORTANT: Your task is ONLY to identify similar nodes, NOT to decide which node should be kept or merged.
The merging direction will be determined by the system based on node properties.

RESPONSE FORMAT:
Return ONLY a JSON array of objects, where each object has:
- "node_id1": ID of first similar node
- "node_id2": ID of second similar node
- "explanation": Brief explanation of why these nodes are similar
- "confidence": How confident you are about the similarity (0.0-1.0)

Example response:
[
  {{
    "node_id1": "n3",
    "node_id2": "n7",
    "explanation": "Both refer to climate policy with slightly different wording",
    "confidence": 0.85
  }}
]

IMPORTANT: Only include pairs with high confidence (>= 0.7).
Do NOT include pairs where the similarity is questionable.
The response should be raw JSON without code block formatting.

RESPONSE (JSON ONLY):
"""
        
        try:
            # Call the LLM to find similar nodes
            llm_logger.log_separator("GRAPH-WIDE NODE SIMILARITY CHECK")
            llm_logger.log_prompt("NODE_SIMILARITY", prompt)
            
            response = self._call_llm_for_structured_output(prompt, "NODE_SIMILARITY")
            
            similar_pairs = []
            if isinstance(response, list):
                for pair in response:
                    if (isinstance(pair, dict) and 
                        "node_id1" in pair and 
                        "node_id2" in pair and 
                        "confidence" in pair):
                        
                        node_id1 = pair["node_id1"]
                        node_id2 = pair["node_id2"]
                        confidence = pair.get("confidence", 0)
                        explanation = pair.get("explanation", "")
                        
                        # Only include high-confidence matches
                        if confidence >= 0.7:
                            logger.info(f"Similar nodes found: {node_id1} <-> {node_id2} ({explanation}, confidence: {confidence})")
                            similar_pairs.append((node_id1, node_id2, confidence))
            
            logger.info(f"Found {len(similar_pairs)} pairs of similar nodes")
            return similar_pairs
            
        except Exception as e:
            logger.error(f"Error finding similar nodes in graph: {e}")
            return [] 