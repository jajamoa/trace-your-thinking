# Synthetic Agent Experiments

This document explains how to run experiments with synthetic agents.

## Overview

The synthetic agent experiments allow agents to:
- Play the roles of synthetic agents from `agent_data/synthetic_agents/`
- Answer questions based on their CBN (Causal Belief Network) logic
- Have conversations with the chatbot on three topics: zoning, healthcare, and camera
- Save transcripts and captured CBNs for analysis

## Quick Start

To run all synthetic agent experiments:

```bash
cd experiment
python run_all_synthetic.py
```

This will:
1. Process all synthetic agents in `agent_data/synthetic_agents/`
2. Run conversations for each agent on all three topics
3. Save transcripts in each agent's `transcript/raw/` folder
4. Save captured CBNs in each agent's `cbn_capture/` folder

## Running Individual Experiments

To run a single agent on a specific topic:

```bash
python run_experiment.py --agent-id 0194ba6e2b4741d496ece110 --topic zoning
```

Options:
- `--agent-id`: The synthetic agent ID (required)
- `--topic`: One of 'zoning', 'healthcare', 'camera' (required)
- `--max-qa`: Maximum QA pairs (default: 15)
- `--quiet`: Reduce output verbosity

## Running Batch Experiments

For more control over batch experiments:

```bash
python run_synthetic_experiments.py --topics zoning healthcare --max-qa 20
```

Options:
- `--topics`: Specific topics to run (default: all)
- `--max-qa`: Maximum QA pairs per conversation (default: 15)
- `--agent-dir`: Directory containing synthetic agents
- `--quiet`: Reduce output verbosity

## Output Structure

For each agent and topic, the following files are created:

```
agent_data/synthetic_agents/
└── <agent_id>/
    ├── transcript/
    │   └── raw/
    │       ├── zoning.csv
    │       ├── healthcare.csv
    │       └── camera.csv
    └── cbn_capture/
        ├── captured_cbn_zoning.json
        ├── captured_cbn_healthcare.json
        └── captured_cbn_camera.json
```

### Transcript Format

Transcripts are saved as CSV files with columns:
- `timestamp`: ISO format timestamp
- `speaker`: Either "interviewer" or "participant"
- `content`: The question or answer text

### Captured CBN Format

The captured CBNs contain the causal belief network that the chatbot builds during the conversation, including:
- Nodes with labels, confidence, and importance
- Edges showing relationships between concepts
- QA history
- Anchor queue and other metadata

## Implementation Details

### SyntheticAgent Class

The `SyntheticAgent` class (in `synthetic_agent.py`):
- Loads agent demographic data and CBN prompts
- Generates answers based on CBN structure and relationships
- Incorporates demographic context into responses

### Answer Generation Logic

The agent generates answers by:
1. Analyzing the question type (stance, factors, relationships, etc.)
2. Using the CBN structure to identify relevant concepts
3. Incorporating demographic context when appropriate
4. Generating coherent responses that reflect the agent's beliefs

## Troubleshooting

1. **API Key Error**: Make sure `DASHSCOPE_API_KEY` is set in your environment or `.env` file

2. **Agent Not Found**: Verify the agent ID exists in `agent_data/synthetic_agents/`

3. **Missing CBN Prompts**: Ensure each agent has `prompt_cbn_*.json` files for all topics

4. **Path Issues**: Make sure to run scripts from the `experiment/` directory

## Verification

To test the setup, run:

```bash
python test_synthetic_agent.py
```

This will verify that:
- Synthetic agents load correctly
- CBN prompts are accessible
- Answer generation works

## Summary Output

After batch experiments, a summary file is created:
- `agent_data/synthetic_agents/experiment_summary.json`

This contains statistics about all experiments including QA counts and file locations.
