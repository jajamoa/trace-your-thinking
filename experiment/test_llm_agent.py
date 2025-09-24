#!/usr/bin/env python3
"""
Test LLM Agent with both conversation and survey modes
"""
import os
from llm_agent import LLMSyntheticAgent

def test_agent():
    """Test agent with a sample agent"""
    agent_id = '91a9b3c2b67840d48e632bb2'
    agent_path = f'agent_data/synthetic_agents/{agent_id}'
    
    # Create agent (will use LLM if API key is available)
    agent = LLMSyntheticAgent(agent_id, agent_path, use_llm=True)
    agent.set_topic('zoning')
    
    print(f"Agent type: {type(agent).__name__}")
    print(f"Using LLM: {agent.use_llm}")
    print(f"API Key available: {bool(os.getenv('DASHSCOPE_API_KEY'))}")
    print("=" * 50)
    
    # Test conversation mode
    print("\n🗣️  CONVERSATION MODE")
    question = {'question': 'What are your thoughts on increasing housing density?'}
    try:
        answer = agent.process_question(question)
        print(f"Q: {question['question']}")
        print(f"A: {answer}")
        print("✅ Conversation mode working")
    except Exception as e:
        print(f"❌ Conversation mode failed: {e}")
    
    # Test survey mode - stance question
    print("\n📊 SURVEY MODE - Stance Question")
    survey_question = {
        'text': 'To what extent do you support or oppose upzoning policies?',
        'type': 'stance', 
        'scale': {
            'min': 1, 
            'max': 10, 
            'min_label': 'Strongly oppose', 
            'max_label': 'Strongly support'
        }
    }
    try:
        response = agent.process_survey_question(survey_question)
        print(f"Q: {survey_question['text']}")
        print(f"Response: {response}")
        print("✅ Survey stance mode working")
    except Exception as e:
        print(f"❌ Survey stance mode failed: {e}")
    
    # Test survey mode - multiple choice
    print("\n📊 SURVEY MODE - Multiple Choice")
    mc_question = {
        'text': 'What is your primary concern about upzoning?',
        'type': 'multiple_choice',
        'options': [
            'Traffic congestion',
            'Loss of neighborhood character', 
            'Property values',
            'Infrastructure strain',
            'No concerns'
        ]
    }
    try:
        response = agent.process_survey_question(mc_question)
        print(f"Q: {mc_question['text']}")
        print(f"Options: {mc_question['options']}")
        print(f"Response: {response}")
        print("✅ Survey multiple choice mode working")
    except Exception as e:
        print(f"❌ Survey multiple choice mode failed: {e}")

if __name__ == "__main__":
    test_agent()
