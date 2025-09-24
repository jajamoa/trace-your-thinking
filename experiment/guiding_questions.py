"""
Guiding Questions Manager
Extracts and manages initial research questions for different topics
"""

# Extracted from seed-guiding-questions-zoning.js
ZONING_QUESTIONS = [
    {
        "id": "gq1",
        "text": "To what extent do you support or oppose upzoning policies that allow for higher density housing in traditionally single-family neighborhoods? Please explain your reasoning.",
        "shortText": "Stance on upzoning",
        "category": "research"
    },
    {
        "id": "gq2",
        "text": "What do you think are the most significant impacts, positive or negative, of increasing housing density in residential neighborhoods?",
        "shortText": "Upzoning impacts",
        "category": "research"
    },
    {
        "id": "gq3",
        "text": "How do you think upzoning policies might affect housing affordability in urban areas?",
        "shortText": "Housing affordability",
        "category": "research"
    },
    {
        "id": "gq4",
        "text": "What impact do you believe increased housing density might have on neighborhood character and quality of life?",
        "shortText": "Neighborhood character",
        "category": "research"
    },
    {
        "id": "gq5",
        "text": "How do you think upzoning might affect transportation systems and traffic congestion in cities?",
        "shortText": "Transportation impacts",
        "category": "research"
    },
    {
        "id": "gq6",
        "text": "What role do you believe local government should play in regulating housing development and density?",
        "shortText": "Government role",
        "category": "research"
    },
    {
        "id": "gq7",
        "text": "How might environmental concerns factor into decisions about urban density and zoning?",
        "shortText": "Environmental factors",
        "category": "research"
    },
    {
        "id": "gq8",
        "text": "What economic effects, both positive and negative, might result from changing zoning laws to allow more multi-family housing?",
        "shortText": "Economic effects",
        "category": "research"
    },
    {
        "id": "gq9",
        "text": "How do you think the interests of current residents versus future residents should be balanced when making zoning decisions?",
        "shortText": "Current vs future residents",
        "category": "research"
    },
    {
        "id": "gq10",
        "text": "What role do you think social equity and access to opportunity play in discussions about zoning and housing policy?",
        "shortText": "Social equity",
        "category": "research"
    }
]

# Extracted from seed-guiding-questions-healthcare.js
HEALTHCARE_QUESTIONS = [
    {
        "id": "gq1",
        "text": "To what extent do you support or oppose universal healthcare policies that provide government-funded healthcare coverage for all citizens? Please explain your reasoning.",
        "shortText": "Stance on universal healthcare",
        "category": "research"
    },
    {
        "id": "gq2",
        "text": "What do you think are the most significant impacts, positive or negative, of implementing a universal healthcare system?",
        "shortText": "Healthcare system impacts",
        "category": "research"
    },
    {
        "id": "gq3",
        "text": "How do you think universal healthcare policies might affect healthcare quality and accessibility?",
        "shortText": "Quality and accessibility",
        "category": "research"
    },
    {
        "id": "gq4",
        "text": "What impact do you believe a universal healthcare system might have on medical innovation and research?",
        "shortText": "Medical innovation",
        "category": "research"
    },
    {
        "id": "gq5",
        "text": "How do you think universal healthcare might affect the economic burden on individuals and families?",
        "shortText": "Economic burden",
        "category": "research"
    },
    {
        "id": "gq6",
        "text": "What role do you believe government should play in healthcare delivery and financing?",
        "shortText": "Government role",
        "category": "research"
    },
    {
        "id": "gq7",
        "text": "How might healthcare provider concerns factor into decisions about universal healthcare implementation?",
        "shortText": "Provider concerns",
        "category": "research"
    },
    {
        "id": "gq8",
        "text": "What economic effects, both positive and negative, might result from transitioning to a universal healthcare system?",
        "shortText": "Economic effects",
        "category": "research"
    },
    {
        "id": "gq9",
        "text": "How do you think the interests of taxpayers versus healthcare consumers should be balanced when making healthcare policy?",
        "shortText": "Taxpayers vs consumers",
        "category": "research"
    },
    {
        "id": "gq10",
        "text": "What role do you think social equity and access to care play in discussions about healthcare policy?",
        "shortText": "Social equity",
        "category": "research"
    }
]

# Extracted from seed-guiding-questions-surveillance.js
SURVEILLANCE_QUESTIONS = [
    {
        "id": "gq1",
        "text": "To what extent do you support or oppose the widespread deployment of surveillance cameras in public spaces? Please explain your reasoning.",
        "shortText": "Stance on surveillance",
        "category": "research"
    },
    {
        "id": "gq2",
        "text": "What do you think are the most significant impacts, positive or negative, of increasing surveillance camera coverage in urban areas?",
        "shortText": "Surveillance impacts",
        "category": "research"
    },
    {
        "id": "gq3",
        "text": "How do you think surveillance technologies might affect public safety and crime rates?",
        "shortText": "Public safety",
        "category": "research"
    },
    {
        "id": "gq4",
        "text": "What impact do you believe increased surveillance might have on personal privacy and individual liberties?",
        "shortText": "Privacy concerns",
        "category": "research"
    },
    {
        "id": "gq5",
        "text": "How do you think surveillance camera systems might affect community trust and police-community relations?",
        "shortText": "Community relations",
        "category": "research"
    },
    {
        "id": "gq6",
        "text": "What role do you believe government should play in regulating surveillance technologies and data collection?",
        "shortText": "Government regulation",
        "category": "research"
    },
    {
        "id": "gq7",
        "text": "How might technological concerns about accuracy and reliability factor into decisions about surveillance systems?",
        "shortText": "Technical factors",
        "category": "research"
    },
    {
        "id": "gq8",
        "text": "What economic effects, both positive and negative, might result from investing in widespread surveillance infrastructure?",
        "shortText": "Economic effects",
        "category": "research"
    },
    {
        "id": "gq9",
        "text": "How do you think the interests of law enforcement versus privacy advocates should be balanced when making surveillance policy?",
        "shortText": "Law enforcement vs privacy",
        "category": "research"
    },
    {
        "id": "gq10",
        "text": "What role do you think social equity and potential bias play in discussions about surveillance technologies?",
        "shortText": "Social equity and bias",
        "category": "research"
    }
]


class GuidingQuestionsManager:
    """Manages guiding questions for different topics"""
    
    def __init__(self):
        self.questions = {
            "zoning": ZONING_QUESTIONS,
            "healthcare": HEALTHCARE_QUESTIONS,
            "surveillance": SURVEILLANCE_QUESTIONS
        }
        
    def get_initial_question(self, topic):
        """Get the first question for a topic"""
        questions = self.questions.get(topic, [])
        if questions:
            return {
                "id": f"initial_{topic}",
                "question": questions[0]["text"],
                "shortText": questions[0]["shortText"],
                "type": "initial"
            }
        else:
            # Fallback to generic question
            return {
                "id": "initial_generic",
                "question": f"What are your thoughts on {topic}?",
                "shortText": f"Initial thoughts on {topic}",
                "type": "initial"
            }
    
    def get_follow_up_questions(self, topic, used_questions=None):
        """Get remaining questions for a topic"""
        if used_questions is None:
            used_questions = set()
            
        questions = self.questions.get(topic, [])
        remaining_questions = []
        
        for i, q in enumerate(questions[1:], 1):  # Skip first question
            q_id = f"{topic}_gq{i+1}"
            if q_id not in used_questions:
                remaining_questions.append({
                    "id": q_id,
                    "question": q["text"],
                    "shortText": q["shortText"],
                    "type": "guiding"
                })
        
        return remaining_questions
    
    def get_all_questions(self, topic):
        """Get all questions for a topic"""
        return self.questions.get(topic, [])
