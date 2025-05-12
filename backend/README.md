# Backend for Trace Your Thinking

This is the Flask backend for the Trace Your Thinking application, providing API endpoints for interview data collection and analysis.

## Project Structure

The backend follows a modular structure:
- `app.py`: Application factory
- `wsgi.py`: WSGI entry point for production
- `run.py`: Development server runner
- `config.py`: Configuration management
- `models/`: Data models
- `services/`: Business logic services
- `api/`: API endpoints
- `utils/`: Utility modules

## Local Development Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
python run.py
```

The server will be available at http://localhost:5001 (or the port specified in your environment).

## Running with Gunicorn

For a more production-like environment, you can use Gunicorn:

```bash
cd backend
gunicorn wsgi:application
```

## Deploying to Render.com

1. Create a new Web Service on Render.com

2. Connect your GitHub repository

3. Configure these settings:
   - **Name**: trace-your-thinking-backend
   - **Environment**: Python
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && gunicorn wsgi:application`

4. Add environment variables:
   - `DASHSCOPE_API_KEY`: Your DashScope API key
   - `FLASK_ENV`: Set to "production"
   - Any other required environment variables

5. Click "Create Web Service"

## API Endpoints

- `GET /healthz`: Health check endpoint
- `GET /api/status`: API status information
- `POST /api/process_answer`: Process interview answers and generate follow-up questions

## Troubleshooting

- **ModuleNotFoundError**: Ensure you are running commands from the correct directory and Python path is set correctly
- **Import Errors**: The application uses absolute imports when running from the backend directory
- **Port already in use**: You can change the port in your environment variables
- **KeyError in SCM Model**: If you encounter a KeyError related to missing fields in the SCM model, ensure you're using the latest version. A bug related to missing keys when loading existing models has been fixed in the current version.
- **LLM-related errors**: Check that you have set the correct API key for DashScope in your environment variables

## Recent Fixes

- **2023-05-08**: Fixed an issue where loading an existing SCM model was failing with KeyError for missing required fields
- **2023-05-08**: Resolved import issues by updating relative imports to absolute imports throughout the codebase
- **2023-05-08**: Added run.py for easier development and testing

# Structural Causal Model (SCM) Interview Framework

This project implements a semi-structured interview framework for building Structural Causal Models (SCMs) from qualitative interviews. It focuses on cognitively-informed elicitation strategies for domains like urban upzoning.

## Architecture Overview

The system uses a three-phase strategy for constructing SCMs:

1. **Node Discovery & Establishment**: Identifying important concepts and establishing them as nodes
2. **Anchor Expansion**: Exploring causal relationships between established nodes
3. **Function Fitting**: Determining the nature and parameters of causal relationships

### System Components

The backend consists of four main components:

- `app.py`: Main Flask application implementing the API endpoints
- `scm_extractor.py`: Extracts nodes, edges, and function parameters from QA pairs
- `scm_manager.py`: Manages the SCM graph, including node merging and edge updates
- `question_generator.py`: Generates follow-up questions based on the current state of the SCM

## Data Flow

1. A question-answer pair is sent to the `/api/process_answer` endpoint
2. The SCM extractor identifies potential nodes and relationships
3. The SCM manager updates the graph structure
4. The question generator creates follow-up questions based on the current phase
5. The updated SCM and follow-up questions are returned to the client

## SCM Structure

The SCM follows a structured JSON format:

```json
{
  "agent_id": "user123",
  "nodes": {
    "n_123": {
      "id": "n_123",
      "label": "Housing Affordability",
      "type": "binary",
      "values": [true, false],
      "semantic_role": "external_state",
      "appearance": {
        "qa_ids": ["qa_1", "qa_2"],
        "frequency": 2
      },
      "incoming_edges": ["e_1"],
      "outgoing_edges": ["e_2"]
    }
  },
  "edges": {
    "e_1": {
      "from": "n_123",
      "to": "n_456",
      "function": {
        "target": "n_456",
        "inputs": ["n_123"],
        "function_type": "sigmoid",
        "parameters": {
          "weights": [0.8],
          "bias": 0.2
        },
        "noise_std": 0.1,
        "support_qas": ["qa_1"],
        "confidence": 0.7
      },
      "support_qas": ["qa_1"]
    }
  },
  "qas": [
    {
      "qa_id": "qa_1",
      "question": "What do you think about housing policies?",
      "answer": "I think zoning policies affect housing affordability significantly.",
      "parsed_belief": {
        "belief_structure": {
          "from": "n_789",
          "to": "n_123",
          "direction": "positive"
        },
        "belief_strength": {
          "estimated_probability": 0.7,
          "confidence_rating": 0.6
        },
        "counterfactual": "If zoning policies were different, housing affordability would change."
      }
    }
  ]
}
```

## Cognitive Foundations

The system is grounded in several cognitive theories:

- Mental Models (Johnson-Laird, 1983)
- Basic-Level Categories (Rosch, 1978)
- Discourse Entity Grounding (Grosz & Sidner, 1986)

## Node Classification

Nodes are classified into three semantic roles:

1. **External State**: World states observed or believed (e.g., noise level, housing prices)
2. **Internal Affect**: Emotions, preferences, perceived costs (e.g., stress, satisfaction)
3. **Behavioral Intention**: Action tendencies or decision intents (e.g., support for policy)

## API Usage

### Process Answer Endpoint

```
POST /api/process_answer
```

Request body:
```json
{
  "sessionId": "session123",
  "prolificId": "user123",
  "qaPair": {
    "id": "qa_1",
    "question": "What do you think about housing policies?",
    "answer": "I think zoning policies affect housing affordability significantly."
  },
  "qaPairs": [...],
  "currentQuestionIndex": 0,
  "existingCausalGraph": {...}
}
```

Response:
```json
{
  "success": true,
  "sessionId": "session123",
  "prolificId": "user123",
  "qaPair": {...},
  "followUpQuestions": [...],
  "causalGraph": {...},
  "timestamp": 1620000000
}
```

## Deployment

The application runs on port 5001 by default. You can customize this by setting the `PORT` environment variable.

```
PORT=5001 python app.py
``` 