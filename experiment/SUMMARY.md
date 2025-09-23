# Experiment Environment Summary

## What We Built

A clean, minimal experiment environment that enables direct conversation between a chatbot and custom Python agents, with automatic causal graph generation.

## Key Features

1. **Standalone Operation**: Runs independently from the main app
2. **Code Reuse**: Leverages existing backend components (LLM extractor, CBN manager, question generator)
3. **Custom Agents**: Easy-to-implement agent interface for custom behavior
4. **Auto Export**: Automatically saves conversation history and causal graphs

## Architecture

```
experiment/
├── conversation_manager.py    # Orchestrates chatbot-agent dialogue
├── agent_interface.py        # Base classes for custom agents
├── run_experiment.py         # Main experiment runner
├── custom_agent_example.py   # Example agent implementations
├── batch_experiments.py      # Run multiple experiments
├── visualize_graph.py        # View exported causal graphs
├── test_experiment.py        # Test suite
├── quick_start.py           # Interactive launcher
└── exports/                 # Auto-generated results
```

## Quick Usage

### 1. Simple Test
```bash
python experiment/run_experiment.py --agent simple --max-qa 10
```

### 2. Interactive Mode
```bash
python experiment/run_experiment.py --agent interactive
```

### 3. Custom Agent
```python
from experiment.agent_interface import BaseAgent

class MyAgent(BaseAgent):
    def process_question(self, question):
        # Custom logic here
        return "My response"

# Use in experiment
from experiment.run_experiment import ExperimentRunner
runner = ExperimentRunner(MyAgent(), max_qa_count=20)
runner.run()
```

## How It Works

1. **Initialization**: Creates a causal graph with stance node
2. **Question Generation**: Chatbot generates questions based on graph state
3. **Agent Response**: Agent processes question and returns answer
4. **Graph Update**: Answer is analyzed to extract nodes and relationships
5. **Iteration**: Process repeats until max QA count reached
6. **Export**: Conversation and final graph are saved automatically

## Customization Points

- **Agent Logic**: Implement `process_question()` method
- **Topics**: Set via `topic` parameter
- **Conversation Length**: Control with `max_qa_count`
- **Agent Stance**: See `custom_agent_example.py` for stance-based responses

## Output Format

### Conversation File
```json
{
  "session_id": "exp_12345678",
  "topic": "climate change",
  "qa_pairs": [...],
  "total_qa_count": 20
}
```

### Causal Graph File
```json
{
  "nodes": {
    "n1": {"label": "Support for climate change", ...},
    "n2": {"label": "Economic factors", ...}
  },
  "edges": {
    "e1": {"source": "n2", "target": "n1", ...}
  }
}
```

## Setup

### Environment Configuration

1. **Copy environment template:**
   ```bash
   cp experiment/env.example .env.local
   ```

2. **Edit with your API key:**
   ```bash
   # In .env.local:
   DASHSCOPE_API_KEY=your_actual_dashscope_api_key
   ```

3. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

### Requirements

- Python 3.7+
- Backend dependencies (from parent project)
- DASHSCOPE_API_KEY in .env.local or environment

## Next Steps

To implement custom agent behavior:

1. Extend `BaseAgent` class
2. Override `process_question()` method
3. Add custom logic for message processing
4. Return string responses

The framework handles all conversation flow, graph building, and export functionality automatically.
