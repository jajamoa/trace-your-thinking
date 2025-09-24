"""
Thread-safe LLM-Powered Synthetic Agent with concurrent request handling
"""
import json
import os
import requests
import threading
from pathlib import Path
from datetime import datetime
from agent_interface import BaseAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import queue


class ThreadSafeLLMAgent(BaseAgent):
    """Thread-safe agent that uses LLM with concurrent request handling"""
    
    # Class-level thread pool for LLM requests
    _llm_executor = None
    _executor_lock = threading.Lock()
    
    @classmethod
    def get_llm_executor(cls, max_workers=8):
        """Get or create the shared LLM thread pool"""
        if cls._llm_executor is None:
            with cls._executor_lock:
                if cls._llm_executor is None:
                    cls._llm_executor = ThreadPoolExecutor(
                        max_workers=max_workers, 
                        thread_name_prefix="LLM-Request"
                    )
        return cls._llm_executor
    
    @classmethod
    def shutdown_llm_executor(cls):
        """Shutdown the shared LLM thread pool"""
        if cls._llm_executor is not None:
            with cls._executor_lock:
                if cls._llm_executor is not None:
                    cls._llm_executor.shutdown(wait=True)
                    cls._llm_executor = None
    
    def __init__(self, agent_id, agent_data_path, use_llm=True):
        """
        Initialize thread-safe LLM synthetic agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_data_path: Path to the agent's data directory
            use_llm: Whether to use LLM (if False, falls back to templates)
        """
        super().__init__(agent_id)
        self.agent_data_path = Path(agent_data_path)
        self.use_llm = use_llm and bool(os.getenv('DASHSCOPE_API_KEY'))
        
        # Load demographic data
        self.demographic = self._load_demographic()
        
        # Current topic and CBN
        self.current_topic = None
        self.current_cbn_prompt = None
        
        # LLM settings
        self.api_key = os.getenv('DASHSCOPE_API_KEY')
        self.model = "qwen-turbo"
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # Thread-local storage for request session
        self._local = threading.local()
    
    def _get_session(self):
        """Get thread-local requests session"""
        if not hasattr(self._local, 'session'):
            self._local.session = requests.Session()
            # Set common headers
            self._local.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            })
        return self._local.session
        
    def _load_demographic(self):
        """Load agent demographic data"""
        demographic_file = self.agent_data_path / "demographic" / "demographic.json"
        if demographic_file.exists():
            with open(demographic_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def set_topic(self, topic):
        """Set current topic and load corresponding CBN"""
        self.current_topic = topic
        
        # Map surveillance to camera for file naming
        file_topic = "camera" if topic == "surveillance" else topic
        
        # Load CBN prompt for this topic (only prompt CBN is needed for reasoning)
        prompt_file = self.agent_data_path / f"prompt_cbn_{file_topic}.json"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                self.current_cbn_prompt = json.load(f)
        else:
            self.current_cbn_prompt = None
    
    def process_question(self, question):
        """Process a question using LLM with CBN context"""
        if not self.current_cbn_prompt:
            return "I need to think about this topic more before I can provide a meaningful answer."
        
        question_text = question.get("question", "") if isinstance(question, dict) else str(question)
        
        if self.use_llm and self.api_key:
            return self._generate_llm_answer(question_text)
        else:
            # Fallback to template-based response
            return self._generate_template_answer(question_text)
    
    def process_survey_question(self, question_data):
        """Process a survey question with specific format requirements"""
        if not self.current_cbn_prompt:
            return {"error": "No CBN data available"}
        
        question_text = question_data.get("text", "")
        question_type = question_data.get("type", "opinion")
        options = question_data.get("options", [])
        scale = question_data.get("scale", None)
        reasons = question_data.get("reasons", [])
        
        # Store reasons for reason_evaluation questions
        if question_type == "reason_evaluation":
            self._current_question_reasons = reasons
        
        if self.use_llm and self.api_key:
            return self._generate_survey_response(question_text, question_type, options, scale)
        else:
            return self._generate_template_survey_response(question_data)
    
    def _llm_request(self, messages, max_tokens=200, temperature=0.8, retry_count=3):
        """Make thread-safe LLM request with retry and rate limiting"""
        import time
        import random
        
        session = self._get_session()
        
        data = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.9
            }
        }
        
        last_error = None
        
        for attempt in range(retry_count):
            try:
                # Add small random delay to avoid thundering herd
                if attempt > 0:
                    delay = random.uniform(0.5, 2.0) * (attempt + 1)
                    time.sleep(delay)
                
                response = session.post(self.api_url, json=data, timeout=30)
                
                # Handle rate limiting specifically
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', '60')
                    wait_time = min(int(retry_after), 60)  # Cap at 60 seconds
                    
                    if attempt < retry_count - 1:  # Don't wait on last attempt
                        print(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{retry_count}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {retry_count} attempts")
                
                response.raise_for_status()
                
                result = response.json()
                if 'output' in result:
                    output = result['output']
                    # Handle both API response formats
                    if 'text' in output:
                        return output['text'].strip()
                    elif 'choices' in output and output['choices']:
                        return output['choices'][0]['message']['content'].strip()
                
                raise Exception(f"Unexpected API response format: {result}")
                
            except Exception as e:
                last_error = e
                if attempt < retry_count - 1:
                    # Exponential backoff for other errors
                    delay = min(2 ** attempt + random.uniform(0, 1), 10)
                    time.sleep(delay)
                    continue
                else:
                    # Last attempt failed
                    break
        
        # All retries failed
        raise last_error
    
    def _generate_llm_answer(self, question_text):
        """Generate answer using LLM with CBN context"""
        try:
            # Build personality prompt from CBN and demographics
            personality_prompt = self._build_personality_prompt()
            
            # Create the full prompt
            system_prompt = f"""You are a research participant responding to questions about {self.current_topic}. 

{personality_prompt}

Respond naturally and conversationally, as if you're talking to a researcher. Keep your response under 150 words. Be authentic and show your personality through your answer."""

            user_prompt = f"Question: {question_text}\n\nPlease answer based on your beliefs and experiences:"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            return self._llm_request(messages, max_tokens=200, temperature=0.8)
                
        except Exception as e:
            # Check for specific API issues
            error_str = str(e).lower()
            if "access denied" in error_str or "account" in error_str:
                print(f"LLM API access issue: {e}")
                # Disable LLM for this agent
                self.use_llm = False
            elif "inappropriate content" in error_str:
                print(f"Content filtered by API: {e}")
                # Don't disable LLM, just use template for this question
            else:
                print(f"LLM generation failed: {e}, falling back to template")
            return self._generate_template_answer(question_text)
    
    def _build_personality_prompt(self):
        """Build personality description from prompt CBN only"""
        if not self.current_cbn_prompt:
            return "You are a thoughtful research participant."
        
        # Convert CBN to natural language
        cbn_text = self._cbn_to_text()
        
        # Build personality prompt
        prompt = f"""You are a research participant with the following belief network about {self.current_topic}:

{cbn_text}

Based on these interconnected beliefs, respond naturally and authentically to questions. Your answers should reflect these beliefs and their relationships."""
        
        # Add demographic context if available
        if self.demographic:
            age = self.demographic.get('age', 'unknown')
            education = self.demographic.get('education', 'unknown')
            
            prompt += f"\n\nYour background: Age {age}, education: {education}."
        
        return prompt
    
    def _cbn_to_text(self):
        """Convert prompt CBN to readable text"""
        if not self.current_cbn_prompt:
            return ""
        
        nodes = self.current_cbn_prompt.get("nodes", {})
        edges = self.current_cbn_prompt.get("edges", [])
        stance_node_id = self.current_cbn_prompt.get("stance_node")
        
        # Start with stance
        text_parts = []
        if stance_node_id and stance_node_id in nodes:
            stance_label = nodes[stance_node_id]["label"]
            text_parts.append(f"Main stance: {stance_label}")
        
        # Add key beliefs
        belief_nodes = [node["label"] for nid, node in nodes.items() 
                       if nid != stance_node_id]
        if belief_nodes:
            text_parts.append(f"Key beliefs: {', '.join(belief_nodes[:5])}")
        
        # Add relationships from edges
        if edges:
            relationships = []
            for edge in edges[:3]:  # Show only first 3 relationships
                source = nodes.get(edge["source"], {}).get("label", "")
                target = nodes.get(edge["target"], {}).get("label", "")
                direction = edge.get("direction", "related")
                
                if source and target:
                    if direction == "positive":
                        relationships.append(f"{source} supports {target}")
                    elif direction == "negative":
                        relationships.append(f"{source} conflicts with {target}")
                    else:
                        relationships.append(f"{source} relates to {target}")
            
            if relationships:
                text_parts.append(f"Key relationships: {'; '.join(relationships)}")
        
        return "\n".join(text_parts)
    
    def _get_scale_values(self, scale):
        """Extract min/max values from scale (list or dict)"""
        if isinstance(scale, list) and len(scale) >= 2:
            return scale[0], scale[1]
        elif isinstance(scale, dict):
            return scale.get('min', 1), scale.get('max', 10)
        else:
            return 1, 10
    
    def _get_scale_label(self, scale, key, default):
        """Get scale label safely"""
        if isinstance(scale, dict):
            return scale.get(key, default)
        else:
            return default
    
    def _extract_score_from_text(self, text, scale):
        """Extract score from text response using keyword analysis"""
        text_lower = text.lower()
        min_val, max_val = self._get_scale_values(scale)
        
        # Strong positive indicators
        if any(word in text_lower for word in ['strongly support', 'very supportive', 'much more supportive', 'significantly more']):
            return max_val
        
        # Moderate positive indicators  
        if any(word in text_lower for word in ['more supportive', 'support', 'positive', 'strengthens my support', 'makes me more']):
            return int(max_val * 0.7)
        
        # Neutral/mixed indicators
        if any(word in text_lower for word in ['neutral', 'same', 'not change', 'stays mostly', 'balance']):
            return int((max_val + min_val) / 2)
        
        # Moderate negative indicators
        if any(word in text_lower for word in ['less supportive', 'concerned', 'worried', 'still prefer']):
            return int(max_val * 0.3)
        
        # Strong negative indicators
        if any(word in text_lower for word in ['strongly oppose', 'very opposed', 'much less supportive']):
            return min_val
            
        # Default to neutral if no clear indicators
        return int((max_val + min_val) / 2)
    
    def _generate_reason_evaluation_response(self, question_data):
        """Generate response for reason_evaluation type questions"""
        reasons = question_data.get("reasons", [])
        scale = question_data.get("scale", [1, 5])
        min_val, max_val = self._get_scale_values(scale)
        
        # Return a dictionary with scores for each reason
        reason_scores = {}
        for reason_code in reasons:
            # For now, generate random scores within range
            # In a more sophisticated implementation, this could be based on CBN data
            import random
            reason_scores[reason_code] = random.randint(min_val, max_val)
        
        return reason_scores

    def _generate_survey_response(self, question_text, question_type, options, scale):
        """Generate survey response using LLM with specific format"""
        try:
            # Build personality prompt
            personality_prompt = self._build_personality_prompt()
            
            # Handle reason_evaluation separately
            if question_type == "reason_evaluation":
                # For reason_evaluation, we need to get reasons from the original question data
                # This is typically handled by the survey processing script, but we can provide a fallback
                reasons = getattr(self, '_current_question_reasons', options) if hasattr(self, '_current_question_reasons') else []
                return self._generate_reason_evaluation_response({"reasons": reasons, "scale": scale, "text": question_text})
            
            # Create survey-specific prompt
            if question_type in ["stance", "opinion", "scenario"] and scale:
                system_prompt = f"""You are a research participant responding to a survey question. 

{personality_prompt}

For this question, you must respond with ONLY a number from {self._get_scale_values(scale)[0]} to {self._get_scale_values(scale)[1]} based on your beliefs.
{self._get_scale_values(scale)[0]} = {self._get_scale_label(scale, 'min_label', 'Strongly disagree')}
{self._get_scale_values(scale)[1]} = {self._get_scale_label(scale, 'max_label', 'Strongly agree')}

CRITICAL: Your response MUST be ONLY a single number ({self._get_scale_values(scale)[0]}-{self._get_scale_values(scale)[1]}). Do NOT provide any explanation, reasoning, or additional text. Just the number."""
                
                user_prompt = f"Question: {question_text}\n\nYour rating (number only):"
                max_tokens = 10
                
            elif question_type == "multiple_choice" and options:
                system_prompt = f"""You are a research participant responding to a survey question.

{personality_prompt}

Choose ONE option from the list below that best matches your beliefs. Respond with ONLY the option letter (A, B, C, etc.), no explanation.

Options:
{chr(10).join([f'{chr(65+i)}. {opt}' for i, opt in enumerate(options)])}"""
                
                user_prompt = f"Question: {question_text}\n\nYour choice (letter only):"
                max_tokens = 5
                
            else:
                # Open-ended response
                system_prompt = f"""You are a research participant responding to a survey question.

{personality_prompt}

Provide a brief, authentic response (under 100 words) based on your beliefs."""
                
                user_prompt = f"Question: {question_text}\n\nYour response:"
                max_tokens = 150
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response_text = self._llm_request(messages, max_tokens=max_tokens, temperature=0.3)
            
            # Parse response based on type
            if question_type in ["stance", "opinion", "scenario", "reason_evaluation"] and scale:
                # Extract number from response
                import re
                numbers = re.findall(r'\b(\d+)\b', response_text)
                if numbers:
                    score = int(numbers[0])
                    # Handle scale as list [min, max] or dict {"min": val, "max": val}
                    min_val, max_val = self._get_scale_values(scale)
                    if min_val <= score <= max_val:
                        return {"score": score, "raw_response": response_text}
                
                # Try keyword-based fallback parsing if no valid number found
                score = self._extract_score_from_text(response_text, scale)
                if score is not None:
                    return {"score": score, "raw_response": response_text}
                
                # Fallback to template
                return self._generate_template_survey_response({"text": question_text, "type": question_type, "scale": scale})
            
            elif question_type == "multiple_choice" and options:
                # Extract letter choice
                import re
                letters = re.findall(r'\b([A-Z])\b', response_text.upper())
                if letters:
                    choice_index = ord(letters[0]) - ord('A')
                    if 0 <= choice_index < len(options):
                        return {"choice": letters[0], "option": options[choice_index], "raw_response": response_text}
                
                # Fallback to template
                return self._generate_template_survey_response({"text": question_text, "type": question_type, "options": options})
            
            else:
                return {"response": response_text}
                
        except Exception as e:
            # Check for specific API issues
            error_str = str(e).lower()
            if "access denied" in error_str or "account" in error_str:
                print(f"Survey LLM API access issue: {e}")
                # Disable LLM for this agent
                self.use_llm = False
            elif "inappropriate content" in error_str:
                print(f"Survey content filtered by API: {e}")
                # Don't disable LLM, just use template for this question
            else:
                print(f"Survey LLM generation failed: {e}, falling back to template")
            return self._generate_template_survey_response({"text": question_text, "type": question_type, "options": options, "scale": scale})
    
    def _generate_template_survey_response(self, question_data):
        """Generate template-based survey response"""
        question_type = question_data.get("type", "opinion")
        scale = question_data.get("scale")
        options = question_data.get("options", [])
        
        if question_type == "reason_evaluation":
            return self._generate_reason_evaluation_response(question_data)
        
        elif question_type in ["stance", "opinion", "scenario"] and scale:
            # Use stance from CBN to determine score
            stance_node_id = self.current_cbn_prompt.get("stance_node") if self.current_cbn_prompt else None
            if stance_node_id and self.current_cbn_prompt:
                nodes = self.current_cbn_prompt.get("nodes", {})
                if stance_node_id in nodes:
                    label = nodes[stance_node_id].get("label", "").lower()
                    min_val, max_val = self._get_scale_values(scale)
                    if "strongly support" in label:
                        return {"score": max_val}
                    elif "support" in label:
                        return {"score": int((max_val + min_val) * 0.75)}
                    elif "strongly oppose" in label:
                        return {"score": min_val}
                    elif "oppose" in label:
                        return {"score": int((max_val + min_val) * 0.25)}
            
            # Default to middle
            min_val, max_val = self._get_scale_values(scale)
            return {"score": int((max_val + min_val) / 2)}
        
        elif question_type == "multiple_choice" and options:
            # Simple template choice
            return {"choice": "A", "option": options[0] if options else "No option available"}
        
        else:
            return {"response": "I need to think more about this question."}
    
    def _generate_template_answer(self, question_text):
        """Fallback template-based answer generation"""
        # Simplified template response
        if not self.current_cbn_prompt:
            return "I need more time to think about this issue."
        
        stance_node_id = self.current_cbn_prompt.get("stance_node")
        nodes = self.current_cbn_prompt.get("nodes", {})
        
        if stance_node_id and stance_node_id in nodes:
            stance_label = nodes[stance_node_id].get("label", "").lower()
            
            if "support" in stance_label:
                return f"I generally support this. Based on my understanding, this issue is important for our community."
            elif "oppose" in stance_label:
                return f"I have concerns about this. I think this approach could have negative impacts."
            else:
                return f"I have mixed feelings about this. There are multiple factors to consider before making a decision."
        
        return "This is a complex issue that requires careful consideration of various factors."


# Factory function for backward compatibility
def create_synthetic_agent(agent_id, agent_data_path, use_llm=True):
    """Factory function to create the appropriate agent type"""
    if use_llm and os.getenv('DASHSCOPE_API_KEY'):
        return ThreadSafeLLMAgent(agent_id, agent_data_path, use_llm=True)
    else:
        # Import and use original template-based agent
        from synthetic_agent import SyntheticAgent
        return SyntheticAgent(agent_id, agent_data_path)
