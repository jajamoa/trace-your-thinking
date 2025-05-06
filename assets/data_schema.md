# Cognitive SCM – Minimal Node-ID-Based Data Schema

This document defines a minimal and interpretable JSON schema for representing individual-level Structural Causal Models (SCMs), derived from human interviews. These SCMs formalize a person's reasoning trace by representing belief variables and their causal relationships. The schema is designed to support simulation, motif extraction, and structured analysis.


## Top-Level Structure

Each record corresponds to one individual.

```json
{
  "agent_id": "string",
  "demographics": { ... },
  "nodes": { ... },
  "edges": { ... },
  "qas": [ ... ]
}
```


## 1. `agent_id`

| Field     | Type   | Description                        |
|-----------|--------|------------------------------------|
| agent_id  | string | Unique identifier for the individual |


## 2. `demographics`

Basic demographic information about the individual.

| Field       | Type   | Description                            |
|-------------|--------|----------------------------------------|
| age         | number | Age of the individual                  |
| income      | string | Income bracket                         |
| education   | string | Highest level of education completed   |
| occupation  | string | Current or past occupation             |

Example:
```json
{
  "age": 34,
  "income": "$50,000–$99,999",
  "education": "college graduate",
  "occupation": "urban planner"
}
```


## 3. `nodes`

Nodes represent belief variables in the person's reasoning process. Each node has a unique `node_id` (e.g., `"n1"`, `"n2"`).

### Required Fields

| Field           | Type             | Description |
|----------------|------------------|-------------|
| label           | string           | Human-readable concept name |
| type            | string           | One of: `"binary"` or `"continuous"` |
| range           | array            | Required if type is `"continuous"` (e.g., `[0.0, 1.0]`) |
| values          | array            | Required if type is `"binary"`; always `[true, false]` |
| semantic_role   | string           | One of: `"external_state"`, `"internal_affect"`, `"behavioral_intention"` |
| appearance      | object           | Includes `qa_ids` and `frequency` |
| incoming_edges  | array of strings | List of edge IDs targeting this node |
| outgoing_edges  | array of strings | List of edge IDs emitted from this node |

### Node Type Guidelines

- `"binary"` nodes represent boolean propositions and must include:
  ```json
  "values": [true, false]
  ```
- `"continuous"` nodes represent real-valued quantities and must include:
  ```json
  "range": [min, max]
  ```

### Cognitive Role (semantic_role)

| semantic_role         | Description                                  | Cognitive Mapping      |
|------------------------|----------------------------------------------|-------------------------|
| external_state         | Observable or inferred world conditions      | Input / Belief          |
| internal_affect        | Internal emotional or evaluative states      | Affect / Preference     |
| behavioral_intention   | Actions, intentions, or behavioral choices   | Output / Decision       |

Example:
```json
"n2": {
  "label": "Mood",
  "type": "binary",
  "values": [true, false],
  "semantic_role": "internal_affect",
  "appearance": {
    "qa_ids": ["qa_01"],
    "frequency": 1
  },
  "incoming_edges": ["e1"],
  "outgoing_edges": ["e2"]
}
```


## 4. `edges`

Edges define directed causal relationships between nodes. Each edge must include a functional form and is keyed by a unique `edge_id`.

### Required Fields

| Field        | Type   | Description |
|--------------|--------|-------------|
| from         | string | Source `node_id` |
| to           | string | Target `node_id` |
| function     | object | Parameterized causal function |
| support_qas  | array  | List of supporting QA IDs |

### `function` Object

| Field         | Type             | Description |
|---------------|------------------|-------------|
| target        | string           | Target `node_id` |
| inputs        | array of strings | Parent `node_id`s |
| function_type | string           | One of: `"sigmoid"` or `"threshold"` |
| parameters    | object           | Function-specific parameters (see below) |
| noise_std     | float            | Gaussian noise standard deviation [0.0-1.0] |
| support_qas   | array of strings | Supporting QA IDs |
| confidence    | float (optional) | Confidence score [0.0-1.0] |

### Parameters by Function Type

- `"sigmoid"`:
```json
"parameters": {
  "weights": Array[-1.0 to 1.0], // Array of float values for each input
  "bias": Float[-1.0 to 1.0]     // Bias term of sigmoid function
}
```
Output: Float[0.0-1.0], calculated as 1/(1+exp(-(sum(weights*inputs)+bias)))

- `"threshold"`:
```json
"parameters": {
  "threshold": Float[0.0 to 1.0],     // Threshold value
  "direction": Enum["less", "greater", "equal"] // Comparison operator
}
```
Output: Binary [0.0, 1.0]
- "less": Returns 1.0 if input < threshold, else 0.0
- "greater": Returns 1.0 if input > threshold, else 0.0
- "equal": Returns 1.0 if input == threshold, else 0.0


## 5. `qas`

Each QA record contains a question-answer pair and the extracted causal belief structure.

### Required Fields

| Field         | Type   | Description |
|---------------|--------|-------------|
| qa_id         | string | Unique identifier |
| question      | string | Interview question |
| answer        | string | Verbatim response |
| parsed_belief | object | Extracted causal belief |

### `parsed_belief` Fields

| Field            | Type   | Description |
|------------------|--------|-------------|
| belief_structure | object | Causal link between two node IDs |
| belief_strength  | object | Estimated strength and confidence |
| counterfactual   | string | Optional contrastive explanation |

**belief_structure**:
```json
{
  "from": "node_id",                    // Source node ID
  "to": "node_id",                      // Target node ID
  "direction": Enum["positive", "negative"] // Causal effect direction
}
```
- "positive": Increase in source leads to increase in target
- "negative": Increase in source leads to decrease in target

**belief_strength**:

```json
{
  "estimated_probability": Float[0.0-1.0], // Strength of belief
  "confidence_rating": Float[0.0-1.0]      // Confidence in belief
}
```


## Function Type Justification

| Function Type | Kept | Rationale |
|---------------|------|-----------|
| sigmoid       | Yes  | Models graded causal effects |
| threshold     | Yes  | Captures sharp rule-like transitions |
| linear        | No   | Redundant with sigmoid; less interpretable |
| rule_based    | No   | Fragile, not data-driven |
| textual       | No   | Not executable |



## Full Example Record

```json
{
  "agent_id": "user_001",
  "demographics": {
    "age": 34,
    "income": "$50,000–$99,999",
    "education": "college graduate",
    "occupation": "urban planner"
  },
  "nodes": {
    "n1": {
      "label": "Sunlight",
      "type": "continuous",
      "range": [0.0, 1.0],
      "semantic_role": "external_state",
      "appearance": {
        "qa_ids": ["qa_01"],
        "frequency": 1
      },
      "incoming_edges": [],
      "outgoing_edges": ["e1"]
    },
    "n2": {
      "label": "Mood",
      "type": "binary",
      "values": [true, false],
      "semantic_role": "internal_affect",
      "appearance": {
        "qa_ids": ["qa_01"],
        "frequency": 1
      },
      "incoming_edges": ["e1"],
      "outgoing_edges": ["e2"]
    },
    "n3": {
      "label": "SupportsPolicy",
      "type": "binary",
      "values": [true, false],
      "semantic_role": "behavioral_intention",
      "appearance": {
        "qa_ids": ["qa_06"],
        "frequency": 1
      },
      "incoming_edges": ["e2"],
      "outgoing_edges": []
    }
  },
  "edges": {
    "e1": {
      "from": "n1",
      "to": "n2",
      "function": {
        "target": "n2",
        "inputs": ["n1"],
        "function_type": "sigmoid",
        "parameters": {
          "weights": [-2.5],
          "bias": 1.2
        },
        "noise_std": 0.3,
        "support_qas": ["qa_01"],
        "confidence": 0.8
      },
      "support_qas": ["qa_01"]
    },
    "e2": {
      "from": "n2",
      "to": "n3",
      "function": {
        "target": "n3",
        "inputs": ["n2"],
        "function_type": "threshold",
        "parameters": {
          "threshold": 0.6,
          "direction": "less"
        },
        "noise_std": 0.2,
        "support_qas": ["qa_06"]
      },
      "support_qas": ["qa_06"]
    }
  },
  "qas": [
    {
      "qa_id": "qa_01",
      "question": "Why do you oppose tall buildings?",
      "answer": "They block sunlight and it affects my mood.",
      "parsed_belief": {
        "belief_structure": {
          "from": "n1",
          "to": "n2",
          "direction": "negative"
        },
        "belief_strength": {
          "estimated_probability": 0.75,
          "confidence_rating": 0.8
        },
        "counterfactual": "If there were no tall buildings, I'd feel better."
      }
    },
    {
      "qa_id": "qa_06",
      "question": "Do you support the upzoning plan?",
      "answer": "No, because being in a bad mood makes me less supportive of new developments.",
      "parsed_belief": {
        "belief_structure": {
          "from": "n2",
          "to": "n3",
          "direction": "positive"
        },
        "belief_strength": {
          "estimated_probability": 0.6,
          "confidence_rating": 0.7
        },
        "counterfactual": "If I felt better, I might support it."
      }
    }
  ]
}
```
