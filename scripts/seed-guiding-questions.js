// Run this script to initialize the guiding questions database
// node scripts/seed-guiding-questions.js

const { MongoClient } = require('mongodb');
require('dotenv').config({ path: '.env.local' });

// Default guiding questions
const initialGuidingQuestions = [
  {
    id: "gq0a",
    text: "Welcome to the Trace Your Thinking interview system. This platform is designed to capture your thought process about research practices. Would you like me to guide you through using this system?",
    shortText: "Welcome",
    category: "tutorial",
    isActive: true,
    order: 0
  },
  {
    id: "gq0b",
    text: "You have two options for answering questions: voice recording or typing. For voice recording, press the microphone button (🎤) or the Space key to start recording. When finished, press the microphone button or Space key again to stop. You can also press ESC to cancel. The system will automatically transcribe and submit your response after recording. Would you like to try voice recording now?",
    shortText: "Voice recording guide",
    category: "tutorial",
    isActive: true,
    order: 1
  },
  {
    id: "gq0c",
    text: "For text input, click the message icon (💬) to switch modes. Type your response in the text box. Press Ctrl+Enter or click the send button (➤) to submit. You can press ESC to clear your text. Would you like to try text input now?",
    shortText: "Text input guide",
    category: "tutorial",
    isActive: true,
    order: 2
  },
  {
    id: "gq0d",
    text: "You can switch between voice and text modes at any time. In voice mode, the microphone button will show as red when recording is active. During transcription, you'll see 'Transcribing your speech...' and your answer will be automatically submitted once ready. Feel comfortable with the system now?",
    shortText: "Mode switching guide",
    category: "tutorial",
    isActive: true,
    order: 3
  },
  {
    id: "gq0f",
    text: "Excellent! We're now ready to begin the research interview. We're interested in understanding your thoughts about open science practices in research. Take your time with each response and provide as much detail as you'd like.",
    shortText: "Start interview",
    category: "tutorial",
    isActive: true,
    order: 4
  },
  // Phase 1: Node Discovery Questions - Primary stance exploration
  {
    id: "gq1",
    text: "To what extent do you believe that open science practices improve research quality? Please explain your reasoning.",
    shortText: "Stance on open science",
    category: "research",
    isActive: true,
    order: 5
  },
  // Phase 1: Node Discovery Questions - Discovering key concepts/nodes
  {
    id: "gq2",
    text: "What specific aspects of open science (such as data sharing, pre-registration, open access publishing, etc.) do you think are most important for research quality?",
    shortText: "Important aspects",
    category: "research",
    isActive: true,
    order: 6
  },
  {
    id: "gq3",
    text: "How do you think transparency in research methods affects the reliability of scientific findings?",
    shortText: "Transparency effects",
    category: "research",
    isActive: true,
    order: 7
  },
  {
    id: "gq4",
    text: "What role do you believe peer review plays in maintaining research quality in an open science framework?",
    shortText: "Peer review role",
    category: "research",
    isActive: true,
    order: 8
  },
  {
    id: "gq5",
    text: "How might institutional incentives influence researchers' adoption of open science practices?",
    shortText: "Institutional incentives",
    category: "research",
    isActive: true,
    order: 9
  },
  {
    id: "gq6",
    text: "What challenges or barriers do you see in implementing open science practices across different research fields?",
    shortText: "Implementation challenges",
    category: "research",
    isActive: true,
    order: 10
  },
  {
    id: "gq7",
    text: "How do you think open data practices specifically contribute to research reproducibility?",
    shortText: "Open data impact",
    category: "research",
    isActive: true,
    order: 11
  },
  {
    id: "gq8",
    text: "In what ways might open science practices affect researchers at different career stages differently?",
    shortText: "Career stage effects",
    category: "research",
    isActive: true,
    order: 12
  },
  // Phase 2 questions will be generated dynamically based on the nodes discovered
  {
    id: "gq9",
    text: "Thank you for sharing your perspectives. As we conclude, is there anything else about open science and research quality that you'd like to add?",
    shortText: "Final thoughts",
    category: "conclusion",
    isActive: true,
    order: 13
  }
];

async function seedGuidingQuestions() {
  // Check environment variables
  if (!process.env.MONGODB_URI) {
    console.error('MONGODB_URI environment variable is not defined.');
    process.exit(1);
  }

  const client = new MongoClient(process.env.MONGODB_URI);

  try {
    await client.connect();
    console.log('Connected to MongoDB');

    const db = client.db();
    const collection = db.collection('guidingquestions');

    // Check if collection is empty
    const count = await collection.countDocuments();
    
    if (count > 0) {
      console.log(`Found ${count} existing guiding questions.`);
      const deletePrompt = process.argv.includes('--force') ? 'y' : 
        await promptUser('Do you want to delete existing guiding questions? (y/n): ');
      
      if (deletePrompt.toLowerCase() === 'y') {
        await collection.deleteMany({});
        console.log('Deleted existing guiding questions.');
      } else {
        console.log('Operation cancelled. No changes made.');
        return;
      }
    }

    // Insert new guiding questions
    const result = await collection.insertMany(initialGuidingQuestions);
    console.log(`${result.insertedCount} guiding questions have been added to the database.`);

    // Add timestamps
    const timestamp = new Date();
    for (const id of Object.values(result.insertedIds)) {
      await collection.updateOne(
        { _id: id },
        { $set: { createdAt: timestamp, updatedAt: timestamp } }
      );
    }
    
    console.log('Added timestamps to all guiding questions.');
    console.log('Database seeding completed successfully!');
    
  } catch (error) {
    console.error('An error occurred while seeding the database:', error);
  } finally {
    await client.close();
    console.log('MongoDB connection closed.');
  }
}

async function promptUser(question) {
  const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    readline.question(question, (answer) => {
      readline.close();
      resolve(answer);
    });
  });
}

// Execute script
seedGuidingQuestions(); 