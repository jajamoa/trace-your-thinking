# **Causal Belief Network (CBN) Data Schema**

This schema defines the format for capturing causal belief networks extracted from question-answer (QA) interactions. It includes:

- **Nodes**: Concepts with evidence-based confidence and importance scores
- **Edges**: Causal links between nodes, with direction, confidence and evidence
- **QA History**: Source QA pairs that support node and edge generation

Each element is keyed by a unique ID.

---

## Format

### 1. Nodes

```json
"n1": {
  "label": "string",                // Concept name (e.g. "Climate Change")
  "aggregate_confidence": float,    // 0.0–1.0, weighted confidence across all evidence
  "evidence": [                     // List of supporting evidence
    { 
      "qa_id": "qa1",              // ID of supporting QA pair
      "confidence": float,         // 0.0–1.0, confidence from this specific QA
      "importance": float          // 0.0–1.0, importance from this specific QA
    }
  ],
  "incoming_edges": ["e1"],         // List of incoming edge IDs
  "outgoing_edges": ["e2"],         // List of outgoing edge IDs
  "importance": float              // 0.0–1.0, overall node importance
}
```

### 2. Edges

```json
"e1": {
  "source": "n1",                  // From-node
  "target": "n2",                  // To-node
  "aggregate_confidence": float,   // 0.0–1.0, aggregate confidence across all evidence
  "evidence": [                    // List of supporting evidence
    { 
      "qa_id": "qa1",             // ID of supporting QA pair
      "confidence": float,        // 0.0–1.0, confidence from this specific QA
      "original_modifier": float  // -1.0 or 1.0, indicates negative or positive relationship
    }
  ],
  "modifier": float,              // Causal direction and strength: 
                                  // range [-1.0, 1.0]
                                  // positive: supports/causes
                                  // negative: opposes/prevents
  "source_label": "string",       // Cached label of source node
  "target_label": "string"        // Cached label of target node
}
```

### 3. QA History

```json
"qa1": {
  "question": "string",
  "answer": "string",
  "extracted_pairs": [            // Causal relationships extracted from this QA
    {
      "edge_id": "e1",            // ID of the created/updated edge
      "source": "n1",             // Source node ID
      "target": "n2",             // Target node ID
      "source_label": "string",   // Label of source node
      "target_label": "string",   // Label of target node
      "confidence": float,        // 0.0–1.0, confidence in this causal relation
      "modifier": float          // Direction and strength (-1.0 to 1.0)
    }
  ],
  "extracted_nodes": [            // Nodes extracted from this QA
    {
      "node_id": "n1",            // ID of the node
      "label": "string",          // Label of the node
      "confidence": float,        // 0.0–1.0, confidence in this node
      "importance": float         // 0.0–1.0, importance of this node
    }
  ]
}
```

### 4. Full CBN Structure

```json
{
  "agent_id": "string",           // ID of the agent/user
  "nodes": {                      // Dictionary of nodes
    "n1": { /* node object */ },
    "n2": { /* node object */ },
    // ... more nodes
  },
  "edges": {                      // Dictionary of edges
    "e1": { /* edge object */ },
    "e2": { /* edge object */ },
    // ... more edges
  },
  "qa_history": {                 // Dictionary of QA pairs
    "qa1": { /* qa object */ },
    "qa2": { /* qa object */ },
    // ... more QA pairs
  }
}
```

---

## Notes

- **Evidence Structure**: Both nodes and edges use a unified evidence structure that tracks which QA pairs contributed to their creation/update.
- **Aggregate Confidence**: A weighted average of confidence scores across all evidence.
- **Importance**: A score (0–1) indicating the node's relevance to the user's belief system.
- **Modifier**: 
  - For edges, represents the causal *valence* and *strength*.
  - `+1.0`: Strong positive cause (e.g., "X leads to Y")
  - `-1.0`: Strong negative effect (e.g., "X prevents Y")
  - Values between are scaled by confidence

---

## Example: Climate Change Beliefs

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
  }
} 