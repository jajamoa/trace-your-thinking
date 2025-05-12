import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Base configuration class for the application."""
    
    def __init__(self):
        # Load environment variables from parent directory .env file or .env.local file
        parent_env_path = Path(__file__).parent.parent / '.env'
        parent_env_local_path = Path(__file__).parent.parent / '.env.local'

        if parent_env_local_path.exists():
            load_dotenv(dotenv_path=parent_env_local_path)
        elif parent_env_path.exists():
            load_dotenv(dotenv_path=parent_env_path)
            
        # API configuration
        self.API_VERSION = "1.0.0"
        self.PORT = int(os.environ.get("PORT", 5001))
        self.FLASK_ENV = os.environ.get("FLASK_ENV", "development")
        
        # LLM configuration
        self.DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY')
        self.LLM_MODEL = os.environ.get('LLM_MODEL', 'qwen-turbo')
        self.LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', '0.01'))
        self.DEBUG_LLM_IO = os.environ.get('DEBUG_LLM_IO', 'false').lower() == 'true'
        
        # Research configuration
        self.RESEARCH_TOPIC = os.environ.get('NEXT_PUBLIC_RESEARCH_TOPIC', 'general')

config = Config() 