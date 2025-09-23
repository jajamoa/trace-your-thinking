# Chatbot-Agent Conversation Experiment

This experiment environment allows a chatbot to have direct conversations with custom Python agents, automatically building causal graphs from the dialogue.

## Quick Start

### 1. Basic Usage

```bash
# Run with simple agent
python experiment/run_experiment.py --agent simple

# Run with interactive agent (manual responses)
python experiment/run_experiment.py --agent interactive

# Custom topic and QA count
python experiment/run_experiment.py --topic "artificial intelligence" --max-qa 15
```

### 2. Creating Custom Agents

Create your own agent by extending `BaseAgent`:

```python
from experiment.agent_interface import BaseAgent

class MyAgent(BaseAgent):
    def process_question(self, question):
        # Your custom logic here
        q_text = question.get("question", "")
        
        # Return agent's answer
        return "My custom response to: " + q_text
```

### 3. Running with Custom Agent

```python
from experiment.run_experiment import ExperimentRunner
from my_custom_agent import MyAgent

# Create agent and runner
agent = MyAgent()
runner = ExperimentRunner(agent, topic="climate change", max_qa_count=20)

# Run experiment
conversation_file, graph_file = runner.run()
```

## Architecture

### Components

1. **ConversationManager**: Orchestrates the conversation flow
   - Manages QA pairs
   - Updates causal graph
   - Generates follow-up questions

2. **Agent Interface**: Base class for custom agents
   - `BaseAgent`: Abstract base class
   - `SimpleAgent`: Keyword-based responses
   - `InteractiveAgent`: Manual input
   - `CustomAgent`: Example with stance-based responses

3. **ExperimentRunner**: Coordinates the experiment
   - Runs conversation loops
   - Exports results
   - Provides summaries

### Output Files

Results are saved in `experiment/exports/`:

- `conversation_[session_id]_[timestamp].json`: Full conversation history
- `causal_graph_[session_id]_[timestamp].json`: Generated causal graph

## Customization Options

### Agent Behavior

Agents receive questions with this structure:

```python
{
    "id": "q_1",
    "question": "What factors influence climate change?",
    "shortText": "Factors affecting climate",
    "type": "node_discovery"  # or "relationship", "initial", etc.
}
```

Agents should return a string answer that:

- Addresses the question directly
- Mentions relevant factors/concepts for node discovery
- Describes relationships when asked

### Conversation Parameters

- `topic`: Main topic of discussion
- `max_qa_count`: Maximum QA pairs before ending
- `verbose`: Show detailed output during conversation

## Example: Stance-Based Agent

See `custom_agent_example.py` for an agent that responds based on a configured stance:

```python
# Create agents with different perspectives
supportive = CustomAgent(stance="supportive")
opposed = CustomAgent(stance="opposed")
neutral = CustomAgent(stance="neutral")
```

## Requirements

- Python 3.7+
- Backend dependencies (from parent project)
- DASHSCOPE_API_KEY environment variable

### Environment Setup

1. **Create environment file:**
   ```bash
   # Copy the example file
   cp experiment/env.example .env.local
   
   # Edit with your API key
   nano .env.local
   ```

2. **Set DASHSCOPE_API_KEY:**
   ```bash
   # In .env.local file:
   DASHSCOPE_API_KEY=your_actual_api_key_here
   ```

3. **Alternative: Direct export**
   ```bash
   export DASHSCOPE_API_KEY=your_actual_api_key_here
   ```

The experiment environment will automatically load variables from:
- `.env.local` (highest priority, gitignored)  
- `.env` (fallback)

## Notes

- The chatbot uses the same backend as the main application
- Causal graphs are built incrementally during conversation
- Agents can be simple rule-based systems or complex ML models
- Export functionality runs automatically after conversation ends
