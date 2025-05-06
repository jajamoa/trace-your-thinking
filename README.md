# Trace Your Thinking

![TYT Banner](assets/tyt_banner.png)

A sophisticated interview collection and analysis tool designed for research studies, focusing on capturing and analyzing thought processes.

## Overview

Trace Your Thinking is a modern web application that enables researchers to conduct, record, and analyze interviews with enhanced features for tracking thought processes. The application provides a seamless experience for both researchers and participants.

## Key Features

- Modern, minimalist interface optimized for focus
- Real-time interview transcription
- Interactive transcript review and editing
- High-quality voice recording capabilities
- Smooth, intuitive animations
- Responsive design for all devices
- Comprehensive accessibility support

## Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Icons**: Lucide React
- **State Management**: Zustand
- **Animations**: Framer Motion

## Getting Started

### Prerequisites

- Node.js 18 or higher
- pnpm package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/trace-your-thinking.git
cd trace-your-thinking
```

2. Install dependencies:
```bash
pnpm install
```

3. Start the development server:
```bash
pnpm dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Architecture

```
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout with theme
│   ├── page.tsx          # Landing page
│   ├── interview/        # Interview workspace
│   ├── review/          # Review & editing
│   ├── thank-you/       # Completion page
│   └── api/             # API endpoints
├── components/           # React components
│   ├── ui/              # shadcn/ui components
│   ├── ChatPanel.tsx    # Interview interface
│   ├── Sidebar.tsx      # Navigation sidebar
│   ├── Transcript.tsx   # Transcript viewer
│   └── ...             # Other components
├── lib/                 # Utilities
│   ├── store.ts        # State management
│   └── ws.ts           # WebSocket handling
└── public/             # Static assets
```

## Core Functionality

1. **Interview Flow**
   - Start from the welcome screen
   - Conduct interview with real-time transcription
   - Review and edit responses
   - Export or submit final transcript

2. **Key Controls**
   - Press 'R' to revise previous answer
   - Use space bar for voice recording
   - Navigate with keyboard shortcuts

3. **Data Management**
   - Automatic saving
   - Export options (PDF, TXT, JSON)
   - Secure data handling

## Accessibility

The application is built with accessibility as a priority:
- ARIA labels throughout
- Keyboard navigation support
- Motion reduction options
- Screen reader compatibility
- High contrast mode

## Deployment

### Vercel Deployment

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Configure build settings (automatically detected)
4. Deploy with one click

## Contributing

We welcome contributions. Please see our contributing guidelines for more details.

## License

MIT License - See LICENSE file for details

## Support

For support or questions, please open an issue on GitHub or contact the development team.

## Adding Questions Programmatically

The application supports adding questions programmatically via an API endpoint.

### API Endpoint

```
POST /api/questions
```

### Request Body

```json
{
  "sessionId": "session_123456789",
  "question": {
    "text": "What are the ethical implications of your research?",
    "shortText": "Ethical implications"
  }
}
```

### Required Fields

- `sessionId`: The ID of the session to add the question to
- `question.text`: The full text of the question to ask the participant
- `question.shortText`: A short description/label for the question

### Response

```json
{
  "success": true,
  "question": {
    "id": "q1631234567890",
    "text": "What are the ethical implications of your research?",
    "shortText": "Ethical implications"
  },
  "session": {
    // Session data
  }
}
```

### Example using curl

```bash
curl -X POST http://localhost:3000/api/questions \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "session_123456789",
    "question": {
      "text": "What are the ethical implications of your research?",
      "shortText": "Ethical implications"
    }
  }'
```

## Getting Questions

You can retrieve all questions for a session using the GET endpoint:

```
GET /api/questions?sessionId=session_123456789
```

### Response

```json
{
  "questions": [
    {
      "id": "q1",
      "text": "Could you describe your current research focus?",
      "shortText": "Research focus"
    },
    // More questions...
  ],
  "pendingQuestions": [
    // Questions that haven't been answered yet
  ]
}
```

## Session Store API

The application uses a client-side store with the following question-related methods:

### `addNewQuestion(question)`

Adds a new question to the current session.

```javascript
import { useStore } from '@/lib/store'

// In your component
const { addNewQuestion } = useStore()

// Add a new question
const newQuestionId = addNewQuestion({
  text: "What are the ethical implications of your research?",
  shortText: "Ethical implications"
})
```

### `getNextQuestion()`

Returns the next pending question, or null if all questions have been answered.

### `markQuestionAsAnswered(questionId)`

Marks a question as answered, removing it from the pending questions queue.
