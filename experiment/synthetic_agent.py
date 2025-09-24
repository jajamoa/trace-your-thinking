"""
Synthetic Agent Implementation
Implements agents based on synthetic agent data with CBN logic
"""
import json
import os
import random
from pathlib import Path
from datetime import datetime
from agent_interface import BaseAgent


class SyntheticAgent(BaseAgent):
    """Agent that uses synthetic agent data and CBN logic"""
    
    def __init__(self, agent_id, agent_data_path):
        """
        Initialize synthetic agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_data_path: Path to the agent's data directory
        """
        super().__init__(agent_id)
        self.agent_data_path = Path(agent_data_path)
        
        # Load demographic data
        self.demographic = self._load_demographic()
        
        # Current topic and CBN
        self.current_topic = None
        self.current_cbn_prompt = None
        
    def _load_demographic(self):
        """Load agent demographic data"""
        demographic_file = self.agent_data_path / "demographic" / "demographic.json"
        if demographic_file.exists():
            with open(demographic_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def set_topic(self, topic):
        """
        Set current topic and load corresponding CBN prompt
        
        Args:
            topic: One of 'zoning', 'healthcare', 'camera' (or 'surveillance')
        """
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
        """
        Process a question and generate an answer based on CBN logic
        
        Args:
            question: Question dict with 'question' and other fields
            
        Returns:
            Answer string
        """
        if not self.current_cbn_prompt:
            return "I need to think about this topic more before I can provide a meaningful answer."
        
        question_text = question.get("question", "")
        
        # Parse question to identify relevant concepts
        relevant_nodes = self._identify_relevant_nodes(question_text)
        
        # Generate answer based on CBN reasoning
        answer = self._generate_cbn_based_answer(question_text, relevant_nodes)
        
        return answer
    
    def _identify_relevant_nodes(self, question_text):
        """Identify CBN nodes relevant to the question"""
        relevant_nodes = []
        
        if not self.current_cbn_prompt:
            return relevant_nodes
        
        nodes_data = self.current_cbn_prompt.get("nodes", {})
        question_lower = question_text.lower()
        
        # Convert nodes dict to list format
        nodes = []
        if isinstance(nodes_data, dict):
            for node_id, node_info in nodes_data.items():
                node = {"id": node_id}
                node.update(node_info)
                nodes.append(node)
        else:
            nodes = nodes_data
        
        for node in nodes:
            node_label = node.get("label", "").lower()
            
            # Check if node label or related concepts appear in question
            if any(word in question_lower for word in node_label.split()):
                relevant_nodes.append(node)
                continue
                
            # Check for related concepts based on node type and topic
            if self._is_conceptually_related(node, question_lower):
                relevant_nodes.append(node)
        
        # If no specific nodes found, include stance and high-importance nodes
        if not relevant_nodes:
            stance_node_id = self.current_cbn_prompt.get("stance_node")
            for node in nodes:
                if node.get("is_stance") or node.get("id") == stance_node_id:
                    relevant_nodes.append(node)
                elif node.get("properties", {}).get("importance", 0) > 0.7:
                    relevant_nodes.append(node)
        
        return relevant_nodes
    
    def _is_conceptually_related(self, node, question_text):
        """Check if a node is conceptually related to the question"""
        # Topic-specific concept mappings
        concept_mappings = {
            "zoning": {
                "housing": ["density", "upzoning", "development", "neighborhood", "residential"],
                "affordability": ["cost", "price", "affordable", "housing crisis"],
                "transportation": ["traffic", "congestion", "transit", "commute"],
                "environment": ["environmental", "green", "sustainable", "climate"],
                "economy": ["economic", "business", "jobs", "growth"],
                "equity": ["equity", "fair", "access", "opportunity"],
                "character": ["character", "quality of life", "community", "culture"]
            },
            "healthcare": {
                "coverage": ["universal", "insurance", "access", "coverage"],
                "cost": ["cost", "price", "afford", "expense", "payment"],
                "quality": ["quality", "care", "treatment", "outcome"],
                "efficiency": ["efficient", "wait", "delay", "bureaucracy"],
                "equity": ["equity", "fair", "equal", "disparities"],
                "choice": ["choice", "freedom", "option", "provider"],
                "system": ["system", "implementation", "administration"]
            },
            "surveillance": {
                "privacy": ["privacy", "surveillance", "monitor", "watch"],
                "safety": ["safety", "security", "crime", "protection"],
                "effectiveness": ["effective", "work", "prevent", "deter"],
                "misuse": ["misuse", "abuse", "corrupt", "power"],
                "technology": ["technology", "camera", "data", "system"],
                "rights": ["rights", "freedom", "civil", "liberty"],
                "trust": ["trust", "government", "authority", "accountability"]
            }
        }
        
        # Map camera to surveillance
        topic = "surveillance" if self.current_topic == "camera" else self.current_topic
        mappings = concept_mappings.get(topic, {})
        
        node_label = node.get("label", "").lower()
        
        for concept, keywords in mappings.items():
            if concept in node_label:
                return any(keyword in question_text for keyword in keywords)
                
        return False
    
    def _generate_cbn_based_answer(self, question_text, relevant_nodes):
        """Generate answer based on CBN reasoning"""
        if not relevant_nodes:
            return self._generate_generic_answer()
        
        # Get stance value
        stance = self._get_stance_from_nodes(relevant_nodes)
        
        # Identify question type
        question_type = self._identify_question_type(question_text)
        
        # Generate answer based on question type and stance
        if question_type == "stance":
            return self._generate_stance_answer(stance, relevant_nodes)
        elif question_type == "impact":
            return self._generate_impact_answer(stance, relevant_nodes, question_text)
        elif question_type == "causality":
            return self._generate_causal_answer(stance, relevant_nodes, question_text)
        elif question_type == "tradeoff":
            return self._generate_tradeoff_answer(stance, relevant_nodes)
        else:
            return self._generate_reasoning_answer(stance, relevant_nodes, question_text)
    
    def _get_stance_from_nodes(self, nodes):
        """Extract stance value from nodes"""
        # First check the passed nodes
        for node in nodes:
            # Skip if node is not a dict
            if not isinstance(node, dict):
                continue
            if node.get("is_stance"):
                # For prompt_cbn format, use simple stance determination
                label = node.get("label", "").lower()
                if "support" in label or "favor" in label or "pro" in label:
                    return "support"
                elif "against" in label or "oppose" in label or "anti" in label:
                    return "oppose"
        
        # If no stance found in nodes, check the stance node directly
        if self.current_cbn_prompt:
            stance_node_id = self.current_cbn_prompt.get("stance_node")
            nodes_data = self.current_cbn_prompt.get("nodes", {})
            if stance_node_id and stance_node_id in nodes_data:
                stance_node = nodes_data[stance_node_id]
                label = stance_node.get("label", "").lower()
                if "support" in label or "favor" in label or "pro" in label:
                    return "support"
                elif "against" in label or "oppose" in label or "anti" in label:
                    return "oppose"
                    
        # Fallback: determine stance from demographic or topic context
        # This is basic fallback when prompt CBN doesn't have clear stance
        
        return "neutral"
    
    def _identify_question_type(self, question_text):
        """Identify the type of question being asked"""
        question_lower = question_text.lower()
        
        if any(phrase in question_lower for phrase in 
               ["to what extent", "support or oppose", "your stance", "your position"]):
            return "stance"
        elif any(phrase in question_lower for phrase in 
                ["impact", "effect", "consequence", "result", "lead to"]):
            return "impact"
        elif any(phrase in question_lower for phrase in 
                ["cause", "why", "reason", "because", "due to"]):
            return "causality"
        elif any(phrase in question_lower for phrase in 
                ["balance", "tradeoff", "weigh", "versus", "compared"]):
            return "tradeoff"
        else:
            return "reasoning"
    
    def _generate_stance_answer(self, stance, relevant_nodes):
        """Generate answer for stance questions"""
        # Extract key factors from nodes
        factors = self._extract_key_factors(relevant_nodes)
        
        if stance == "strongly_support":
            templates = [
                f"I strongly support this policy. {self._get_supporting_reasons(factors)}",
                f"I'm very much in favor of this. {self._get_benefits_statement(factors)}",
                f"This is definitely something we need. {self._get_positive_impact_statement(factors)}"
            ]
        elif stance == "support":
            templates = [
                f"I generally support this policy. {self._get_moderate_support_reasons(factors)}",
                f"I lean towards supporting this. {self._get_qualified_benefits(factors)}",
                f"Overall, I think this would be beneficial. {self._get_cautious_support(factors)}"
            ]
        elif stance == "oppose":
            templates = [
                f"I have concerns about this policy. {self._get_opposition_reasons(factors)}",
                f"I'm skeptical about this approach. {self._get_negative_impacts(factors)}",
                f"I don't think this is the right solution. {self._get_alternative_suggestion(factors)}"
            ]
        elif stance == "strongly_oppose":
            templates = [
                f"I strongly oppose this policy. {self._get_strong_opposition_reasons(factors)}",
                f"This would be harmful to our community. {self._get_severe_impacts(factors)}",
                f"I'm firmly against this. {self._get_fundamental_disagreement(factors)}"
            ]
        else:
            templates = [
                f"I have mixed feelings about this. {self._get_balanced_view(factors)}",
                f"There are both pros and cons to consider. {self._get_neutral_analysis(factors)}",
                f"I'm undecided on this issue. {self._get_uncertainty_reasons(factors)}"
            ]
        
        return random.choice(templates)
    
    def _generate_impact_answer(self, stance, relevant_nodes, question_text):
        """Generate answer for impact questions"""
        factors = self._extract_key_factors(relevant_nodes)
        
        # Identify specific impact area from question
        impact_area = self._identify_impact_area(question_text)
        
        if stance in ["strongly_support", "support"]:
            return self._generate_positive_impact_answer(factors, impact_area)
        elif stance in ["strongly_oppose", "oppose"]:
            return self._generate_negative_impact_answer(factors, impact_area)
        else:
            return self._generate_mixed_impact_answer(factors, impact_area)
    
    def _generate_causal_answer(self, stance, relevant_nodes, question_text):
        """Generate answer for causal questions"""
        # Use edges from prompt CBN to explain causal relationships
        if self.current_cbn_prompt:
            edges = self.current_cbn_prompt.get("edges", [])
            relevant_edges = self._find_relevant_edges(edges, relevant_nodes)
            
            if relevant_edges:
                return self._explain_causal_chain(relevant_edges, stance)
        
        # Fallback to factor-based explanation
        factors = self._extract_key_factors(relevant_nodes)
        return self._generate_causal_explanation(factors, stance)
    
    def _generate_tradeoff_answer(self, stance, relevant_nodes):
        """Generate answer for tradeoff questions"""
        factors = self._extract_key_factors(relevant_nodes)
        
        positive_factors = [f for f in factors if f.get("valence", "neutral") == "positive"]
        negative_factors = [f for f in factors if f.get("valence", "neutral") == "negative"]
        
        if stance in ["strongly_support", "support"]:
            return f"While I acknowledge {self._list_concerns(negative_factors)}, " \
                   f"I believe {self._list_benefits(positive_factors)} outweigh these concerns."
        elif stance in ["strongly_oppose", "oppose"]:
            return f"Although there might be {self._list_minor_benefits(positive_factors)}, " \
                   f"the {self._list_major_concerns(negative_factors)} are too significant to ignore."
        else:
            return f"This involves balancing {self._list_benefits(positive_factors)} " \
                   f"against {self._list_concerns(negative_factors)}. It's not a simple decision."
    
    def _generate_reasoning_answer(self, stance, relevant_nodes, question_text):
        """Generate general reasoning answer"""
        factors = self._extract_key_factors(relevant_nodes)
        
        # Build reasoning based on factors and stance
        if factors:
            factor_names = [f["label"] for f in factors[:3]]  # Top 3 factors
            return f"The key factors I consider are {', '.join(factor_names)}. " \
                   f"Each of these plays an important role in shaping my perspective."
        else:
            # Fallback to mentioning general node labels
            node_labels = [n.get("label", "") for n in relevant_nodes if n.get("label")]
            if node_labels:
                return f"This relates to {' and '.join(node_labels[:2])}, " \
                       f"which are central to my understanding of this issue."
            else:
                return self._generate_generic_answer()
    
    def _extract_key_factors(self, nodes):
        """Extract key factors from nodes with their properties"""
        factors = []
        
        for node in nodes:
            # Skip stance nodes
            if node.get("is_stance"):
                continue
                
            # All non-stance nodes can be factors
            factor = {
                "label": node.get("label", ""),
                "importance": node.get("properties", {}).get("importance", 0.5),
                "type": node.get("type", "factor"),
                "valence": self._determine_valence(node)
            }
            factors.append(factor)
        
        # Sort by importance if available, otherwise keep order
        if any(f["importance"] != 0.5 for f in factors):
            factors.sort(key=lambda x: x["importance"], reverse=True)
        
        return factors
    
    def _determine_valence(self, node):
        """Determine if a node represents positive or negative factor"""
        label = node.get("label", "").lower()
        
        positive_keywords = ["benefit", "opportunity", "improve", "help", "afford", 
                           "access", "safety", "growth", "equity", "quality"]
        negative_keywords = ["concern", "risk", "harm", "cost", "traffic", "crime",
                           "privacy", "congestion", "displacement", "burden"]
        
        if any(keyword in label for keyword in positive_keywords):
            return "positive"
        elif any(keyword in label for keyword in negative_keywords):
            return "negative"
        else:
            return "neutral"
    
    def _identify_impact_area(self, question_text):
        """Identify specific impact area from question"""
        question_lower = question_text.lower()
        
        impact_areas = {
            "affordability": ["afford", "cost", "price", "expensive"],
            "traffic": ["traffic", "congestion", "transport", "commute"],
            "environment": ["environment", "green", "sustain", "climate"],
            "community": ["neighborhood", "community", "character", "quality of life"],
            "economy": ["economic", "business", "job", "growth"],
            "equity": ["equity", "fair", "access", "opportunity"],
            "safety": ["safe", "security", "crime", "protect"],
            "privacy": ["privacy", "surveillance", "monitor", "data"]
        }
        
        for area, keywords in impact_areas.items():
            if any(keyword in question_lower for keyword in keywords):
                return area
                
        return "general"
    
    # Helper methods for generating specific types of responses
    def _get_supporting_reasons(self, factors):
        if not factors:
            return "It addresses critical issues in our community."
        top_factor = factors[0]["label"]
        return f"The potential for {top_factor} is substantial and would benefit many people."
    
    def _get_benefits_statement(self, factors):
        if len(factors) >= 2:
            return f"The benefits in terms of {factors[0]['label']} and {factors[1]['label']} are clear."
        elif factors:
            return f"The {factors[0]['label']} benefits alone make this worthwhile."
        return "The overall benefits to society are significant."
    
    def _get_positive_impact_statement(self, factors):
        return "Studies have shown similar policies have positive outcomes in other areas."
    
    def _get_moderate_support_reasons(self, factors):
        return "While there are some valid concerns, the potential benefits seem to outweigh them."
    
    def _get_qualified_benefits(self, factors):
        return "If implemented carefully, this could address some important issues."
    
    def _get_cautious_support(self, factors):
        return "However, we need to ensure proper safeguards are in place."
    
    def _get_opposition_reasons(self, factors):
        if factors:
            concerns = [f for f in factors if f.get("valence") == "negative"]
            if concerns:
                return f"The {concerns[0]['label']} issues are particularly troubling."
        return "There are several problematic aspects that haven't been addressed."
    
    def _get_negative_impacts(self, factors):
        return "The unintended consequences could outweigh any potential benefits."
    
    def _get_alternative_suggestion(self, factors):
        return "We should explore other approaches that don't have these drawbacks."
    
    def _get_strong_opposition_reasons(self, factors):
        return "This goes against fundamental principles of how our community should function."
    
    def _get_severe_impacts(self, factors):
        if factors:
            return f"The {factors[0]['label']} consequences would be devastating."
        return "The negative impacts would be far-reaching and long-lasting."
    
    def _get_fundamental_disagreement(self, factors):
        return "This represents a misguided approach to solving our problems."
    
    def _get_balanced_view(self, factors):
        return "There are valid arguments on both sides that need careful consideration."
    
    def _get_neutral_analysis(self, factors):
        if len(factors) >= 2:
            return f"The {factors[0]['label']} benefits must be weighed against {factors[1]['label']} concerns."
        return "Each situation would need to be evaluated on its own merits."
    
    def _get_uncertainty_reasons(self, factors):
        return "More research and community input would help clarify the best path forward."
    
    def _generate_positive_impact_answer(self, factors, impact_area):
        """Generate positive impact answer"""
        templates = {
            "affordability": "This would significantly improve affordability by creating more housing options and reducing competition for limited units.",
            "traffic": "With proper planning, higher density can actually reduce traffic by enabling more walkable neighborhoods and better transit.",
            "community": "This would create more vibrant, diverse communities with better local amenities and services.",
            "economy": "The economic benefits include job creation, increased tax revenue, and support for local businesses.",
            "general": f"The positive impacts would be substantial, particularly in terms of {factors[0]['label'] if factors else 'community development'}."
        }
        return templates.get(impact_area, templates["general"])
    
    def _generate_negative_impact_answer(self, factors, impact_area):
        """Generate negative impact answer"""
        templates = {
            "affordability": "This could actually worsen affordability by attracting more high-income residents and driving up prices.",
            "traffic": "The increased density would overwhelm our already strained transportation infrastructure.",
            "community": "This would fundamentally alter neighborhood character and reduce quality of life for existing residents.",
            "economy": "The economic disruption to existing businesses and property values would be significant.",
            "general": f"The negative impacts, especially regarding {factors[0]['label'] if factors else 'community stability'}, are concerning."
        }
        return templates.get(impact_area, templates["general"])
    
    def _generate_mixed_impact_answer(self, factors, impact_area):
        """Generate mixed impact answer"""
        return f"There would be both positive and negative impacts on {impact_area}. " \
               f"The outcome would largely depend on implementation details and local conditions."
    
    def _find_relevant_edges(self, edges, nodes):
        """Find edges relevant to the given nodes"""
        node_ids = [n.get("id") for n in nodes if n.get("id")]
        relevant_edges = []
        
        for edge in edges:
            if edge.get("source") in node_ids or edge.get("target") in node_ids:
                relevant_edges.append(edge)
                
        return relevant_edges
    
    def _explain_causal_chain(self, edges, stance):
        """Explain causal relationships based on edges"""
        if not edges:
            return self._generate_generic_answer()
            
        # Build a simple causal explanation
        edge = edges[0]  # Use first relevant edge
        source = edge.get("source_label", "this factor")
        target = edge.get("target_label", "the outcome")
        strength = edge.get("properties", {}).get("strength", "moderate")
        
        if stance in ["strongly_support", "support"]:
            return f"I believe {source} would positively influence {target}, creating beneficial outcomes for our community."
        elif stance in ["strongly_oppose", "oppose"]:
            return f"My concern is that {source} would negatively affect {target}, leading to undesirable consequences."
        else:
            return f"The relationship between {source} and {target} is complex and could go either direction."
    
    def _generate_causal_explanation(self, factors, stance):
        """Generate causal explanation based on factors"""
        if not factors:
            return "There are multiple causal factors at play that shape my view on this issue."
            
        if stance in ["strongly_support", "support"]:
            return f"I believe this would work because it addresses {factors[0]['label']}, " \
                   f"which is a key driver of positive change in this area."
        elif stance in ["strongly_oppose", "oppose"]:
            return f"My concern stems from how this would exacerbate {factors[0]['label']}, " \
                   f"which is already a significant problem."
        else:
            return f"The causal relationships are complex, with {factors[0]['label']} " \
                   f"potentially leading to both positive and negative outcomes."
    
    def _list_concerns(self, factors):
        """List concerns from factors"""
        if not factors:
            return "some potential drawbacks"
        concerns = [f["label"] for f in factors[:2]]
        return " and ".join(concerns) if len(concerns) > 1 else concerns[0]
    
    def _list_benefits(self, factors):
        """List benefits from factors"""
        if not factors:
            return "the potential benefits"
        benefits = [f["label"] for f in factors[:2]]
        return " and ".join(benefits) if len(benefits) > 1 else benefits[0]
    
    def _list_minor_benefits(self, factors):
        """List minor benefits"""
        if not factors:
            return "some minor benefits"
        return f"some benefits in terms of {factors[0]['label']}"
    
    def _list_major_concerns(self, factors):
        """List major concerns"""
        if not factors:
            return "serious concerns"
        concerns = [f["label"] for f in factors[:2]]
        return "risks related to " + " and ".join(concerns)
    
    def _generate_generic_answer(self):
        """Generate generic answer when no specific reasoning available"""
        generic_answers = [
            "This is a complex issue that requires careful consideration of multiple factors.",
            "I would need more specific information to provide a detailed response.",
            "My perspective on this depends on various contextual factors.",
            "There are many aspects to consider when evaluating this question.",
            "This touches on several important considerations that shape my view."
        ]
        return random.choice(generic_answers)
    
    def add_to_history(self, question, answer):
        """Add QA pair to conversation history"""
        self.conversation_history.append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })