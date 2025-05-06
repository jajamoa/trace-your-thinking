# Thinking Trace Application

This is a Python backend for processing user answers and generating causal graphs for the Thinking Trace application. It works in conjunction with a Next.js frontend that handles data storage.

## Architecture Overview

This application uses a hybrid architecture with clear separation of responsibilities:

1. **Python Backend**: 
   - Responsible for computational logic and data processing
   - Generates causal graphs from user answers
   - Provides follow-up questions
   - Does NOT handle database storage

2. **Next.js Frontend**:
   - Handles user interface and interactions
   - Manages question flow
   - Responsible for ALL database operations
   - Stores data processed by the Python backend

### Data Flow

1. User answers a question in the Next.js frontend
2. Frontend sends the answer to the Python backend for processing
3. Python backend generates a causal graph and returns it along with follow-up questions
4. Next.js frontend stores the processed data in MongoDB
5. Next.js provides API routes for retrieving stored data

## Python Backend

### Features

- Process user answers to extract patterns
- Generate causal graphs showing relationships
- Provide fixed follow-up questions
- Return processed data to frontend

### Installation and Setup

#### Prerequisites

- Python 3.8+

#### Installation Steps

1. Clone the repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python app.py
```

The server will start at http://localhost:5000.

### API Endpoints

#### Process Answer

```
POST /api/process_answer
```

Request body example:
```json
{
  "sessionId": "session_123456",
  "prolificId": "user_123",
  "qaPair": {
    "id": "q1",
    "question": "Please describe your thinking process...",
    "shortText": "Thinking process",
    "answer": "I first considered..."
  }
}
```

Response example:
```json
{
  "success": true,
  "sessionId": "session_123456",
  "prolificId": "user_123",
  "qaPair": {
    "id": "q1",
    "question": "Please describe your thinking process...",
    "shortText": "Thinking process",
    "answer": "I first considered..."
  },
  "followUpQuestions": [
    {
      "id": "followup1",
      "question": "Could you further explain the main factors you mentioned in your previous answer?",
      "shortText": "Explain main factors",
      "answer": ""
    },
    ...
  ],
  "causalGraph": {
    "id": "graph_12345",
    "nodes": [...],
    "edges": [...]
  },
  "timestamp": 1631234567
}
```

## Next.js Frontend Integration

The Next.js frontend provides API routes for database operations:

### Save Data API Route

```
POST /api/save-data
```
This endpoint saves data received from the Python backend to MongoDB.

### Get Causal Graphs API Route

```
GET /api/causal-graphs?prolificId=user123
```
This endpoint retrieves all causal graphs for a specific user.

### Integration Example

```javascript
// Frontend code example
async function submitAnswer(qaPair) {
  // Get session data from store
  const sessionId = useStore.getState().sessionId;
  const prolificId = useStore.getState().prolificId;
  
  // 1. Send to Python backend for processing
  const response = await fetch('http://localhost:5000/api/process_answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, prolificId, qaPair }),
  });
  
  const data = await response.json();
  
  if (data.success) {
    // 2. Save processed data to MongoDB via Next.js API
    await fetch('/api/save-data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    
    // 3. Add follow-up questions to question list
    data.followUpQuestions.forEach(question => {
      useStore.getState().addNewQuestion(question);
    });
    
    // 4. Update UI with causal graph
    displayCausalGraph(data.causalGraph);
  }
}
```

## Why This Architecture?

This architecture leverages the strengths of both platforms:

1. **Python for Complex Processing**: 
   - Better suited for computational tasks and data analysis
   - Easier integration with NLP and ML libraries
   - More flexible for implementing complex algorithms

2. **Next.js for Data Management**:
   - Unified data storage approach
   - Consistent data access patterns
   - Better type safety with TypeScript
   - Simplified state management

By separating computation from data storage, we get a more maintainable and scalable system that can evolve independently. 