# How to Use the Agent Generator

## Quick Start

### Using the Shell Script

The simplest way to generate agents is using the provided shell script:

```bash
# Generate 100 agents (default)
./generate_agents.sh

# Generate specific number of agents
./generate_agents.sh 50

# Generate with custom output directory
./generate_agents.sh 50 my_custom_agents
```

### Using Python Directly

```bash
# Generate with default settings
python unified_agent_generator.py

# Custom settings
python unified_agent_generator.py --num_agents 200 --output_dir production_agents
```

## Generated Files Structure

Each agent will have:

1. **Full GT CBNs** (in `cbn/` folder):
   - Complete ground truth CBNs for analysis
   - Contains all nodes, edges, and metadata
   - Used for similarity analysis and validation

2. **Prompt CBNs** (in agent root):
   - Simplified CBNs for prompting
   - Only connected nodes with stance
   - Minimal information for reasoning

3. **Demographic Data** (in `demographic/` folder):
   - Randomly sampled from survey schema
   - Maintains logical consistency

## Example Prompt CBN

The prompt CBNs are designed for efficient reasoning:

```json
{
  "stance_node": "n1",
  "nodes": {
    "n1": {"label": "Support for upzoning", "is_stance": true},
    "n2": {"label": "Housing affordability", "is_stance": false},
    "n3": {"label": "Traffic concerns", "is_stance": false}
  },
  "edges": [
    {"source": "n2", "target": "n1", "direction": "positive"},
    {"source": "n3", "target": "n1", "direction": "negative"}
  ]
}
```

This shows:
- Node n1 is the stance (main position)
- Housing affordability (n2) positively influences support
- Traffic concerns (n3) negatively influence support

## Analysis Tools

After generating agents, you can:

1. **Run similarity analysis**:
   ```bash
   python enhanced_cbn_similarity_analyzer.py synthetic_agents zoning analysis_output
   ```

2. **Check individual agent data**:
   ```bash
   # View prompt CBN
   cat synthetic_agents/[agent_id]/prompt_cbn_zoning.json
   
   # View full GT CBN
   cat synthetic_agents/[agent_id]/cbn/gt_cbn_zoning.json
   ```

## Tips

- Generate agents in batches for better organization
- Use meaningful output directory names
- The prompt CBNs are much smaller than GT CBNs (typically 2-10 nodes vs 20-100+ nodes)
- All GT CBNs are validated to have exactly one stance node
