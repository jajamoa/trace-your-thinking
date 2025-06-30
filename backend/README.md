# Backend System for Trace Your Thinking

This backend system powers the "Trace Your Thinking" application, which builds structural causal models (SCMs) from user conversations.

## Components

- `app.py` - Flask application with API endpoints
- `llm_extractor.py` - LLM-based node and edge extractor
- `cbn_manager.py` - Causal Belief Network manager
- `question_generator.py` - Follow-up question generator
- `llm_logger.py` - Minimalist LLM call logging system

## LLM Call Logging System

The backend includes a lightweight, modular logging system for LLM calls that allows you to control which types of calls have detailed logs.

### How It Works

The logging system is completely separated from the LLM extraction logic:

1. `llm_logger.py` provides a simple, reusable logging interface
2. LLM calls in `llm_extractor.py` use the logger to record prompts and responses
3. Configuration is done through environment variables

### Available Call Types

The following LLM call types can be separately controlled:

- `node_extraction` - Extraction of nodes from QA pairs
- `edge_extraction` - Extraction of edges (causal relationships)
- `function_params` - Extraction of causal function parameters
- `belief_extraction` - Extraction of user beliefs about relationships
- `topic_extraction` - Extraction of topics from questions

### Configuration

Logging is controlled through environment variables in your `.env` or `.env.local` file:

```
# Global control for all LLM calls
DEBUG_LLM_IO=true|false

# Type-specific control (overrides global setting)
DEBUG_LLM_IO_NODE_EXTRACTION=true|false
DEBUG_LLM_IO_EDGE_EXTRACTION=true|false
DEBUG_LLM_IO_FUNCTION_PARAMS=true|false
DEBUG_LLM_IO_BELIEF_EXTRACTION=true|false
DEBUG_LLM_IO_TOPIC_EXTRACTION=true|false
```

### Usage Example

To enable only node extraction and function parameter logging:

```
# .env or .env.local file
DEBUG_LLM_IO=false
DEBUG_LLM_IO_NODE_EXTRACTION=true
DEBUG_LLM_IO_FUNCTION_PARAMS=true
```

### Developer Integration

To use the logger in your own code:

```python
from llm_logger import llm_logger, LLM_CALL_TYPES

# Log a prompt if enabled for this call type
llm_logger.log_prompt(LLM_CALL_TYPES["NODE_EXTRACTION"], prompt)

# Make your API call...
response = some_llm_api.call(prompt)

# Log the response if enabled for this call type
llm_logger.log_response(LLM_CALL_TYPES["NODE_EXTRACTION"], response)
```

## Enhanced Node Similarity Matching

The system now uses enhanced semantic similarity matching for node merging, utilizing:

1. **WordNet-based similarity**: Compares nodes using linguistic relationships from WordNet
2. **Word vector similarity**: (Optional) Computes similarity using pre-trained word embeddings
3. **Jaccard similarity**: Uses word overlap as a fallback method

### Configuration

The semantic similarity threshold is currently set to `0.9` (in `cbn_manager.py`). This is a strict threshold that 
requires nodes to be very similar before merging.

To adjust this threshold:
- Lower values (e.g., 0.7) will result in more aggressive merging
- Higher values (e.g., 0.95) will result in very conservative merging
- The recommended range is 0.8-0.9 for a good balance

### Word Vectors (Optional)

To use word vectors for even better similarity matching:

1. Download a pre-trained word embeddings model (e.g., GloVe or Word2Vec)
2. Modify the `SemanticSimilarityEngine` initialization in `cbn_manager.py`:
   ```python
   self.similarity_engine = SemanticSimilarityEngine(
       similarity_threshold=0.9,
       use_wordnet=True,
       use_word_vectors=True,
       word_vectors_path="/path/to/your/vectors.bin"
   )
   ```

## Dependencies

The enhanced similarity engine requires these additional dependencies (already in requirements.txt):
- nltk
- numpy
- scikit-learn
- gensim (for word vectors)

## Initial Setup

When first setting up the project:

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Download required NLTK data (this will happen automatically on first run, or you can run):
   ```
   python download_nltk_data.py
   ```

3. Start the server:
   ```
   python app.py
   ```

The API will be available at http://localhost:5001/ 

## CBN Data Structure Example

Below is an example of the Causal Belief Network (CBN) data structure used in the application:

```json
{
  "agent_id": "user123",
  "nodes": {
    "n1": {
      "label": "Climate Change",
      "aggregate_confidence": 0.85,
      "evidence": [
        {
          "qa_id": "qa1",
          "confidence": 0.8,
          "importance": 0.9
        },
        {
          "qa_id": "qa2",
          "confidence": 0.9,
          "importance": 0.85
        }
      ],
      "incoming_edges": ["e2"],
      "outgoing_edges": ["e1"],
      "importance": 0.9
    },
    "n2": {
      "label": "Carbon Emissions",
      "aggregate_confidence": 0.8,
      "evidence": [
        {
          "qa_id": "qa1",
          "confidence": 0.8,
          "importance": 0.7
        }
      ],
      "incoming_edges": [],
      "outgoing_edges": ["e2"],
      "importance": 0.7
    },
    "n3": {
      "label": "Sea Level Rise",
      "aggregate_confidence": 0.75,
      "evidence": [
        {
          "qa_id": "qa2",
          "confidence": 0.75,
          "importance": 0.6
        }
      ],
      "incoming_edges": ["e1"],
      "outgoing_edges": [],
      "importance": 0.6
    }
  },
  "edges": {
    "e1": {
      "source": "n1",
      "target": "n3",
      "aggregate_confidence": 0.8,
      "evidence": [
        {
          "qa_id": "qa2",
          "confidence": 0.8,
          "original_modifier": 1.0
        }
      ],
      "modifier": 0.8,
      "source_label": "Climate Change",
      "target_label": "Sea Level Rise"
    },
    "e2": {
      "source": "n2",
      "target": "n1",
      "aggregate_confidence": 0.75,
      "evidence": [
        {
          "qa_id": "qa1",
          "confidence": 0.75,
          "original_modifier": 1.0
        }
      ],
      "modifier": 0.75,
      "source_label": "Carbon Emissions",
      "target_label": "Climate Change"
    }
  },
  "qa_history": {
    "qa1": {
      "question": "How do you think carbon emissions affect climate change?",
      "answer": "I believe carbon emissions are a major factor causing climate change because greenhouse gases lead to global warming.",
      "extracted_pairs": [
        {
          "edge_id": "e2",
          "source": "n2",
          "target": "n1",
          "source_label": "Carbon Emissions",
          "target_label": "Climate Change",
          "confidence": 0.75,
          "modifier": 0.75
        }
      ],
      "extracted_nodes": [
        {
          "node_id": "n2",
          "label": "Carbon Emissions",
          "confidence": 0.8,
          "importance": 0.7
        },
        {
          "node_id": "n1",
          "label": "Climate Change",
          "confidence": 0.8,
          "importance": 0.9
        }
      ]
    },
    "qa2": {
      "question": "What impact does climate change have on sea levels?",
      "answer": "Climate change causes polar ice caps to melt, leading to sea level rise which threatens coastal areas.",
      "extracted_pairs": [
        {
          "edge_id": "e1",
          "source": "n1",
          "target": "n3",
          "source_label": "Climate Change",
          "target_label": "Sea Level Rise",
          "confidence": 0.8,
          "modifier": 0.8
        }
      ],
      "extracted_nodes": [
        {
          "node_id": "n1",
          "label": "Climate Change",
          "confidence": 0.9,
          "importance": 0.85
        },
        {
          "node_id": "n3",
          "label": "Sea Level Rise",
          "confidence": 0.75,
          "importance": 0.6
        }
      ]
    }
  },
  "phase": "edge_construction",
  "anchor_queue": ["n1"]
}
```

### Process Variables

The CBN system includes process variables that manage the interview flow but are not part of the core data schema:

1. **phase** - Tracks the current interview phase:
   - `node_discovery`: Initial phase focused on identifying key concepts
   - `edge_construction`: Second phase building connections between nodes
   - `edge_refinement`: Final phase refining and validating relationships

2. **anchor_queue** - List of important nodes identified for follow-up questions. Nodes become anchors when:
   - They appear in multiple QA pairs (high frequency)
   - They have high importance (>= 0.8)
   - They have high confidence (>= 0.8)

These process variables guide the question generation and help the system transition between different interview stages. 