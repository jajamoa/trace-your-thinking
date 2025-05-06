// Run this script to initialize the guiding questions database
// node scripts/seed-guiding-questions.js

const { MongoClient } = require('mongodb');
require('dotenv').config({ path: '.env.local' });

// Default guiding questions
const initialGuidingQuestions = [
  {
    id: "gq0a",
    text: "Welcome to the Trace Your Thinking interview system. This platform is designed to capture your research insights in a comfortable and intuitive way. Would you like me to guide you through using this system?",
    shortText: "Welcome",
    category: "tutorial",
    isActive: true,
    order: 0
  },
  {
    id: "gq0b",
    text: "You have two options for answering questions: voice recording or typing. For voice recording, simply click the microphone button (🎤) and speak clearly. When finished, click the microphone again or press ESC. The system will automatically transcribe and submit your response. Would you like to try voice recording now?",
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
    text: "You can switch between voice and text modes at any time. The microphone button will show while recording and turn red when active. During transcription, you'll see 'Transcribing your speech...' and your answer will be automatically submitted once ready. Feel comfortable with the system now?",
    shortText: "Mode switching guide",
    category: "tutorial",
    isActive: true,
    order: 3
  },
  {
    id: "gq0e",
    text: "Excellent! We're now ready to begin the research interview. Remember you can switch input methods anytime. Take your time with each response and provide as much detail as you'd like. Let's start with our first research question.",
    shortText: "Start interview",
    category: "tutorial",
    isActive: true,
    order: 4
  },
  {
    id: "gq1",
    text: "Could you describe your current research focus and how it relates to the broader field?",
    shortText: "Research focus",
    category: "research",
    isActive: true,
    order: 5
  },
  {
    id: "gq2",
    text: "Could you elaborate on the methodologies you're using in your current project?",
    shortText: "Methodologies",
    category: "research",
    isActive: true,
    order: 6
  },
  {
    id: "gq3",
    text: "What challenges have you encountered in your research, and how have you addressed them?",
    shortText: "Challenges",
    category: "research",
    isActive: true,
    order: 7
  },
  {
    id: "gq4",
    text: "How do you situate your work within existing literature in your field?",
    shortText: "Literature context",
    category: "research",
    isActive: true,
    order: 8
  },
  {
    id: "gq5",
    text: "What implications might your findings have for theory or practice in your domain?",
    shortText: "Implications",
    category: "research",
    isActive: true,
    order: 9
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